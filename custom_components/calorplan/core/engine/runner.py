# Versión: 2026.11.8
"""Ejecutor: aplica los eventos planificados sobre los actuadores."""
from __future__ import annotations

import logging

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
                registro = await self._inicio(sala, tramo, False)
                if registro is not None:
                    registros.append(registro)
        return registros

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

    # --- Inicio ------------------------------------------------------------------
    async def _inicio(self, sala: Room, tramo: Slot, forzar: bool) -> Record:
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

        decision = self._evaluator.evaluate(sala, tramo, self.plan.config)
        if forzar and not decision.start:
            decision = Decision(True, ajustes.COD_FORZADO, ajustes.MOTIVO_FORZADO,
                                decision.outdoor, decision.indoor)

        if not decision.start:
            accion = (ajustes.ACCION_ERROR if decision.code in ajustes.CODIGOS_FALLO
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
        return await self._emitir(sala, tramo, tipo, ajustes.ACCION_ENCENDER, decision.code,
                                  decision.reason, decision)

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
