# Versión: 2026.11.10
"""Ejecutor: aplica los eventos planificados sobre los actuadores."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .. import settings as ajustes
from ..models import Actuator, Pause, Plan, Room, Slot, pausa_activa
from .evaluator import Evaluator
from .notifier import Notifier
from .planner import Planner
from .ports import ActuatorPort, ClockPort, EventPort, StatePort
from .records import Decision, PlannedEvent, Record

_LOGGER = logging.getLogger(__name__)


class Runner:
    """Ejecuta inicios, fines y reintentos con verificación y avisos."""

    def __init__(self, plan: Plan, state: StatePort, actuator: ActuatorPort,
                 notifier: Notifier, clock: ClockPort, events: EventPort) -> None:
        self._state = state
        self._actuator = actuator
        self._notifier = notifier
        self._clock = clock
        self._events = events
        self._evaluator = Evaluator(state)
        # Tramos activos cuyo inicio se omitió por condiciones: (id de habitación, id de tramo)
        self._pendientes: set[tuple[str, str]] = set()
        # De ellos, los omitidos por falta de datos de sensores (se reintentan tras un arranque)
        self._sin_datos: set[tuple[str, str]] = set()
        # Último inicio gestionado de cada tramo («habitación/tramo» → inicio y resultado)
        self._manejados: dict[str, dict[str, str]] = {}
        self.plan = plan
        self.planner = Planner(plan)
        self.set_plan(plan)

    def set_plan(self, plan: Plan) -> None:
        """Sustituye el plan (tras importar o recargar la configuración)."""
        self.plan = plan
        self.planner = Planner(plan)
        self._notifier.plan = plan

    # --- Entrada ---------------------------------------------------------------
    async def handle(self, evento: PlannedEvent, forzar: bool = False) -> Record | None:
        """Procesa un evento planificado. `forzar` ignora condiciones y ausencia."""
        sala = self.plan.room(evento.room_id)
        tramo = sala.slot(evento.slot_id) if sala else None
        if sala is None or tramo is None:
            _LOGGER.warning(ajustes.MOTIVO_TRAMO_INEXISTENTE)
            return None
        if evento.kind == ajustes.EVENTO_INICIO:
            return await self._inicio(sala, tramo, forzar)
        return await self._fin(sala, tramo, evento.kind)

    async def catch_up(self) -> list[Record]:
        """Al arrancar dentro de un tramo, aplica el inicio si `catch_up` lo pide."""
        if self.plan.config.catch_up != ajustes.CATCH_UP_EVALUAR:
            return []
        ahora = self._clock.now()
        registros = []
        for sala in self.plan.rooms:
            for tramo in self.planner.active_slots(sala, ahora):
                inicio = self.planner.inicio_ocurrencia(tramo, ahora)
                if inicio is not None and self.ya_gestionado(sala.id, tramo.id, inicio):
                    continue  # ya se gestionó antes del reinicio: se respeta el estado del dispositivo
                # Conservador: con datos ausentes (típico tras arrancar) no se enciende
                registro = await self._inicio(sala, tramo, False, conservador=True)
                if registro is not None:
                    registros.append(registro)
        return registros

    # --- Estado que sobrevive a un reinicio ----------------------------------------------------
    @staticmethod
    def _clave(sala_id: str, tramo_id: str) -> str:
        """Clave de un tramo en el estado guardado."""
        return f"{sala_id}/{tramo_id}"

    def _quitar_pendiente(self, clave: tuple[str, str]) -> None:
        """Deja de reevaluar un tramo."""
        self._pendientes.discard(clave)
        self._sin_datos.discard(clave)

    def ya_gestionado(self, room_id: str, slot_id: str, inicio: datetime) -> bool:
        """Indica si el inicio de ese tramo (esa ocurrencia) ya se gestionó, p. ej. antes de un reinicio."""
        previo = self._manejados.get(self._clave(room_id, slot_id))
        return previo is not None and datetime.fromisoformat(previo["start"]) >= inicio

    def _registrar_manejo(self, sala: Room, tramo: Slot, accion: str, codigo: str) -> None:
        """Anota el resultado del inicio de la ocurrencia en curso (se guarda para sobrevivir a un reinicio)."""
        inicio = self.planner.inicio_ocurrencia(tramo, self._clock.now())
        if inicio is None:
            return  # p. ej. ejecución manual fuera del horario
        if accion == ajustes.ACCION_ENCENDER:
            resultado = ajustes.RESULTADO_ENCENDIDO
        elif codigo in ajustes.CODIGOS_SIN_DATOS:
            resultado = ajustes.RESULTADO_PENDIENTE_DATOS
        elif codigo in ajustes.CODIGOS_REEVALUABLES:
            resultado = ajustes.RESULTADO_PENDIENTE
        elif accion == ajustes.ACCION_ERROR:
            resultado = ajustes.RESULTADO_ERROR
        else:
            resultado = ajustes.RESULTADO_OMITIDO
        self._manejados[self._clave(sala.id, tramo.id)] = {"start": inicio.isoformat(), "outcome": resultado}

    def estado_arranque(self) -> dict[str, dict[str, str]]:
        """Copia del estado que debe persistirse."""
        return {k: dict(v) for k, v in self._manejados.items()}

    def cargar_estado(self, datos: dict[str, Any] | None) -> None:
        """Restaura lo gestionado antes de un reinicio.

        Con `datos=None` (primer arranque con esta función) se considera gestionado todo lo que
        está activo ahora, para no tocar ningún dispositivo.
        """
        ahora = self._clock.now()
        if datos is None:
            self._manejados = {}
            for sala in self.plan.rooms:
                for tramo in self.planner.active_slots(sala, ahora):
                    inicio = self.planner.inicio_ocurrencia(tramo, ahora)
                    self._manejados[self._clave(sala.id, tramo.id)] = {
                        "start": inicio.isoformat(), "outcome": ajustes.RESULTADO_OMITIDO}
            return
        self._manejados = {k: dict(v) for k, v in datos.items()
                           if isinstance(v, dict) and "start" in v and "outcome" in v}
        for clave, valor in self._manejados.items():
            sala_id, _, tramo_id = clave.partition("/")
            if valor["outcome"] in (ajustes.RESULTADO_PENDIENTE, ajustes.RESULTADO_PENDIENTE_DATOS):
                self._pendientes.add((sala_id, tramo_id))
                if valor["outcome"] == ajustes.RESULTADO_PENDIENTE_DATOS:
                    self._sin_datos.add((sala_id, tramo_id))

    # --- Pausas ----------------------------------------------------------------------------
    def pausa_vigente(self, sala: Room) -> tuple[Pause, bool] | None:
        """Pausa vigente hoy: (pausa, es_global). La de la habitación tiene prioridad."""
        hoy = self._clock.now().date()
        propia = pausa_activa(sala.pauses, hoy)
        if propia is not None:
            return propia, False
        global_ = pausa_activa(self.plan.config.pauses, hoy)
        return (global_, True) if global_ is not None else None

    @staticmethod
    def _motivo_pausa(pausa: Pause, es_global: bool) -> str:
        """Texto del motivo de omisión por pausa."""
        return ajustes.MOTIVO_PAUSA.format(
            motivo=pausa.reason or ajustes.MOTIVO_PAUSA_SIN_NOMBRE,
            ambito=ajustes.PAUSA_AMBITO_CASA if es_global else "habitación",
            desde=pausa.start.strftime(ajustes.FORMATO_FECHA),
            hasta=pausa.end.strftime(ajustes.FORMATO_FECHA) if pausa.end else ajustes.PAUSA_SIN_FIN)

    # --- Reevaluación durante el tramo ------------------------------------------------------
    def salas_pendientes(self, solo_sin_datos: bool = False) -> set[str]:
        """Habitaciones con algún tramo cuyo inicio se omitió por condiciones (o por falta de datos)."""
        origen = self._sin_datos if solo_sin_datos else self._pendientes
        return {sala_id for sala_id, _ in origen}

    def _ya_encendido(self, act: Actuator) -> bool:
        """Indica si el dispositivo ya está calentando (p. ej. encendido a mano)."""
        return self._state.get_state(act.entity_id) == act.estado_encendido

    async def reevaluate(self, room_id: str | None = None, solo_sin_datos: bool = False) -> list[Record]:
        """Reevalúa los tramos activos cuyo inicio se omitió por condiciones.

        Enciende si ahora se cumplen. No hace nada si el dispositivo ya está encendido (a mano),
        y las omisiones repetidas no se registran ni avisan: solo el encendido.
        """
        ahora = self._clock.now()
        registros: list[Record] = []
        politica = ajustes.POLITICA_NO_ENCENDER if solo_sin_datos else None
        for clave in sorted(self._sin_datos if solo_sin_datos else self._pendientes):
            if room_id is not None and clave[0] != room_id:
                continue
            sala = self.plan.room(clave[0])
            tramo = sala.slot(clave[1]) if sala else None
            if sala is None or tramo is None or tramo.id not in {
                    t.id for t in self.planner.active_slots(sala, ahora)}:
                self._quitar_pendiente(clave)  # el tramo ya terminó o no existe
                continue
            if (not sala.enabled or not tramo.enabled or self.plan.config.away_mode
                    or self.pausa_vigente(sala) is not None):
                continue  # sigue pendiente: se reanudará cuando se levante el bloqueo
            if self._ya_encendido(sala.actuator):
                self._quitar_pendiente(clave)  # alguien lo encendió: no se interviene
                continue
            if not self._evaluator.evaluate(sala, tramo, self.plan.config, politica).start:
                continue
            registros.append(await self._inicio(sala, tramo, False, reevaluacion=True,
                                                conservador=solo_sin_datos))
        return registros

    # --- Inicio ------------------------------------------------------------------
    async def _inicio(self, sala: Room, tramo: Slot, forzar: bool, reevaluacion: bool = False,
                      conservador: bool = False) -> Record:
        """Inicio de tramo: comprueba, evalúa y enciende."""
        tipo = ajustes.EVENTO_INICIO
        if not forzar:
            if not sala.enabled:
                return await self._emitir(sala, tramo, tipo, ajustes.ACCION_OMITIR,
                                          ajustes.COD_HABITACION_DESHABILITADA,
                                          ajustes.MOTIVO_HABITACION_DESHABILITADA)
            if not tramo.enabled:
                return await self._emitir(sala, tramo, tipo, ajustes.ACCION_OMITIR,
                                          ajustes.COD_TRAMO_DESHABILITADO,
                                          ajustes.MOTIVO_TRAMO_DESHABILITADO)
            if self.plan.config.away_mode:
                return await self._emitir(sala, tramo, tipo, ajustes.ACCION_OMITIR,
                                          ajustes.COD_AUSENCIA, ajustes.MOTIVO_AUSENCIA)
            pausa = self.pausa_vigente(sala)
            if pausa is not None:
                return await self._emitir(sala, tramo, tipo, ajustes.ACCION_OMITIR,
                                          ajustes.COD_PAUSA, self._motivo_pausa(*pausa))

        politica = ajustes.POLITICA_NO_ENCENDER if conservador else None
        decision = self._evaluator.evaluate(sala, tramo, self.plan.config, politica)
        if forzar and not decision.start:
            decision = Decision(True, ajustes.COD_FORZADO, ajustes.MOTIVO_FORZADO,
                                decision.outdoor, decision.indoor)

        if not decision.start:
            if decision.code in ajustes.CODIGOS_REEVALUABLES:
                self._pendientes.add((sala.id, tramo.id))  # se reevaluará mientras dure el tramo
                if decision.code in ajustes.CODIGOS_SIN_DATOS:
                    self._sin_datos.add((sala.id, tramo.id))
                else:
                    self._sin_datos.discard((sala.id, tramo.id))
            # Tras un reinicio, la falta de datos es normal: se omite sin dar el error
            accion = (ajustes.ACCION_ERROR
                      if decision.code in ajustes.CODIGOS_FALLO and not conservador
                      else ajustes.ACCION_OMITIR)
            return await self._emitir(sala, tramo, tipo, accion, decision.code,
                                      decision.reason, decision)

        if not self.plan.config.shadow_mode:
            try:
                await self._encender(sala.actuator, tramo)
            except Exception as err:  # noqa: BLE001 - cualquier fallo del actuador
                _LOGGER.exception("Error al encender %s", sala.id)
                return await self._emitir(
                    sala, tramo, tipo, ajustes.ACCION_ERROR, ajustes.COD_NO_DISPONIBLE,
                    ajustes.MOTIVO_ACTUADOR_ERROR.format(error=err), decision)
        self._quitar_pendiente((sala.id, tramo.id))
        motivo = ajustes.MOTIVO_REEVALUACION if reevaluacion else decision.reason
        return await self._emitir(sala, tramo, tipo, ajustes.ACCION_ENCENDER, decision.code,
                                  motivo, decision)

    async def _encender(self, act: Actuator, tramo: Slot) -> None:
        """Enciende el actuador y aplica el bloqueo infantil de inicio."""
        if act.type == ajustes.TIPO_CLIMATE:
            await self._actuator.climate_heat(act.entity_id, act.hvac_mode_on, tramo.setpoint)
            await self._bloqueo(act, act.child_lock_on_start)
        else:
            await self._actuator.switch_set(act.entity_id, True)

    # --- Fin y reintento ---------------------------------------------------------
    async def _fin(self, sala: Room, tramo: Slot, tipo: str) -> Record | None:
        """Fin o reintento: apaga con verificación. None si no hay nada que hacer."""
        if tipo == ajustes.EVENTO_FIN:
            self._quitar_pendiente((sala.id, tramo.id))  # el tramo terminó: deja de reevaluarse
        act = sala.actuator
        ahora = self._clock.now()
        if tipo == ajustes.EVENTO_REINTENTO:
            otros = [t for t in self.planner.active_slots(sala, ahora) if t.id != tramo.id]
            if otros:
                return None  # otro tramo está activo: no se apaga
        solo_si_encendido = act.off_only_if_heating or tipo == ajustes.EVENTO_REINTENTO
        estado = self._state.get_state(act.entity_id)
        if (solo_si_encendido and estado is not None
                and estado not in ajustes.ESTADOS_NO_DISPONIBLE
                and estado != act.estado_encendido):
            return None  # ya está apagado: ni acción ni aviso

        if self.plan.config.shadow_mode:
            return await self._emitir(sala, tramo, tipo, ajustes.ACCION_APAGAR,
                                      ajustes.COD_OK, ajustes.MOTIVO_OK)

        verificado, error = await self._apagar_verificado(act)
        if not verificado:
            motivo = ajustes.MOTIVO_APAGADO_NO_VERIFICADO.format(intentos=act.verify_attempts)
            if error:
                motivo = f"{motivo} ({error})"
            return await self._emitir(sala, tramo, tipo, ajustes.ACCION_ERROR,
                                      ajustes.COD_APAGADO_NO_VERIFICADO, motivo)
        await self._bloqueo(act, act.child_lock_on_end)
        return await self._emitir(sala, tramo, tipo, ajustes.ACCION_APAGAR,
                                  ajustes.COD_OK, ajustes.MOTIVO_OK)

    async def _apagar_verificado(self, act: Actuator) -> tuple[bool, str | None]:
        """Apaga y comprueba el estado, con reintentos. Devuelve (ok, último error)."""
        ultimo_error: str | None = None
        for _ in range(act.verify_attempts):
            if not await self._esperar_disponible(act.entity_id):
                continue
            try:
                if act.type == ajustes.TIPO_CLIMATE:
                    await self._actuator.climate_off(act.entity_id)
                else:
                    await self._actuator.switch_set(act.entity_id, False)
            except Exception as err:  # noqa: BLE001 - cuenta como intento fallido
                _LOGGER.exception("Error al apagar %s", act.entity_id)
                ultimo_error = str(err)
                continue
            await self._clock.sleep(ajustes.VERIFICAR_ESPERA_SEGUNDOS)
            if self._state.is_state(act.entity_id, act.estado_apagado):
                return True, None
        return False, ultimo_error

    async def _esperar_disponible(self, entity_id: str) -> bool:
        """Espera (hasta el tiempo máximo) a que la entidad esté disponible."""
        esperado = 0
        while not self._state.is_available(entity_id):
            if esperado >= ajustes.DISPONIBILIDAD_TIMEOUT_SEGUNDOS:
                return False
            await self._clock.sleep(ajustes.DISPONIBILIDAD_SONDEO_SEGUNDOS)
            esperado += ajustes.DISPONIBILIDAD_SONDEO_SEGUNDOS
        return True

    # --- Utilidades ---------------------------------------------------------------
    async def _bloqueo(self, act: Actuator, accion: str) -> None:
        """Aplica el bloqueo infantil; un fallo se registra pero no es crítico."""
        if not act.tiene_bloqueo or accion == ajustes.BLOQUEO_NADA:
            return
        try:
            await self._actuator.switch_set(act.child_lock_switch,
                                            accion == ajustes.BLOQUEO_BLOQUEAR)
        except Exception:  # noqa: BLE001 - el bloqueo no debe romper el encendido
            _LOGGER.exception("No se pudo aplicar el bloqueo infantil de %s", act.entity_id)

    async def _emitir(self, sala: Room, tramo: Slot, tipo: str, accion: str, codigo: str,
                      motivo: str, decision: Decision | None = None) -> Record:
        """Crea el registro, dispara el evento y avisa (salvo en modo sombra)."""
        if tipo == ajustes.EVENTO_INICIO:
            self._registrar_manejo(sala, tramo, accion, codigo)
        sombra = self.plan.config.shadow_mode
        if sombra:
            motivo = ajustes.MOTIVO_SIMULACION.format(accion=accion, motivo=motivo)
            codigo = ajustes.COD_SIMULACION
        registro = Record(
            when=self._clock.now(), room_id=sala.id, room_name=sala.name,
            slot_id=tramo.id, slot_name=tramo.name, kind=tipo, action=accion,
            code=codigo, reason=motivo, setpoint=tramo.setpoint,
            outdoor=decision.outdoor if decision else None,
            indoor=decision.indoor if decision else None, simulated=sombra)
        datos = registro.to_dict()
        self._events.record(datos)
        self._events.fire(ajustes.EVENTO_ACCION, datos)
        if not sombra:
            await self._notifier.notificar(sala, tramo, registro)
        return registro
