# Versión: 2026.11.9
"""Controlador: une el motor puro con Home Assistant (temporizador y estado)."""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (async_track_point_in_time, async_track_time_change,
                                        async_track_time_interval)
from homeassistant.helpers.start import async_at_started

from ..core import settings as ajustes
from ..core.engine import Notifier, PlannedEvent, Runner
from ..core.engine.editor import PlanEditor
from ..core.engine.history import History
from ..core.engine.overview import OverviewBuilder
from ..core.models import Plan, Slot
from .adapters import HAActuator, HAClock, HAEvents, HANotify, HAState
from .store import HistoryStore, PlanStore

_LOGGER = logging.getLogger(__name__)


class Controller:
    """Programa un único temporizador al próximo evento y ejecuta el motor."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.store = PlanStore(hass)
        self.history_store = HistoryStore(hass)
        self.history = History()
        self.clock = HAClock()
        self.plan = Plan()
        self.runner: Runner | None = None
        self.notifier: Notifier | None = None
        # Última decisión por habitación (para los sensores)
        self.ultimos: dict[str, dict[str, Any]] = {}
        self._cancelar_temporizador: Callable[[], None] | None = None
        self._cancelar_arranque: Callable[[], None] | None = None
        self._cancelar_medianoche: Callable[[], None] | None = None
        self._cancelar_reevaluacion: Callable[[], None] | None = None
        self._ultimo_instante: datetime = self.clock.now()
        self._tareas: set[asyncio.Task] = set()
        self._cerrojos: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    # --- Ciclo de vida -----------------------------------------------------------
    async def async_start(self) -> None:
        """Carga el plan, crea el motor y programa el primer evento."""
        self.plan = await self.store.async_load()
        self.history = History(await self.history_store.async_load())
        self.notifier = Notifier(self.plan, HANotify(self.hass), self.clock)
        self.runner = Runner(self.plan, HAState(self.hass), HAActuator(self.hass),
                             self.notifier, self.clock, HAEvents(self.hass, self._registrar))
        self._ultimo_instante = self.clock.now()
        self._programar_reevaluacion()
        self._cancelar_arranque = async_at_started(self.hass, self._al_arrancar)
        self._cancelar_medianoche = async_track_time_change(
            self.hass, self._medianoche, hour=0, minute=0, second=10)
        self._programar()

    def async_stop(self) -> None:
        """Cancela el temporizador y las tareas en curso."""
        if self._cancelar_temporizador:
            self._cancelar_temporizador()
            self._cancelar_temporizador = None
        if self._cancelar_arranque:
            self._cancelar_arranque()
            self._cancelar_arranque = None
        if self._cancelar_medianoche:
            self._cancelar_medianoche()
            self._cancelar_medianoche = None
        if self._cancelar_reevaluacion:
            self._cancelar_reevaluacion()
            self._cancelar_reevaluacion = None
        for tarea in list(self._tareas):
            tarea.cancel()
        self._tareas.clear()

    async def _al_arrancar(self, _hass: HomeAssistant) -> None:
        """Cuando Home Assistant ha arrancado, aplica `catch_up` si corresponde."""
        assert self.runner is not None
        await self.runner.catch_up()
        self._avisar()

    # --- Planificación -----------------------------------------------------------
    def _programar(self) -> None:
        """Programa el temporizador al siguiente evento del plan."""
        if self._cancelar_temporizador:
            self._cancelar_temporizador()
            self._cancelar_temporizador = None
        assert self.runner is not None
        siguiente = self.runner.planner.next_event(self.clock.now())
        if siguiente is not None:
            self._cancelar_temporizador = async_track_point_in_time(
                self.hass, self._disparar, siguiente.when)

    async def _disparar(self, _ahora: datetime) -> None:
        """Se ejecuta al llegar el instante programado."""
        assert self.runner is not None
        ahora = self.clock.now()
        # Los eventos demasiado antiguos (p. ej. tras suspender el equipo) se descartan
        desde = max(self._ultimo_instante,
                    ahora - timedelta(seconds=ajustes.TOLERANCIA_RETRASO_SEGUNDOS))
        self._ultimo_instante = ahora
        eventos = self.runner.planner.events_between(desde, ahora)
        self._programar()
        por_sala: dict[str, list[PlannedEvent]] = defaultdict(list)
        for evento in eventos:
            por_sala[evento.room_id].append(evento)
        for sala_id, lista in por_sala.items():
            tarea = self.hass.async_create_background_task(
                self._ejecutar_sala(sala_id, lista), name=f"{ajustes.DOMAIN}_{sala_id}")
            self._tareas.add(tarea)
            tarea.add_done_callback(self._tareas.discard)
        self._avisar()

    async def _ejecutar_sala(self, sala_id: str, eventos: list[PlannedEvent],
                             forzar: bool = False) -> None:
        """Ejecuta en orden los eventos de una habitación (con cerrojo por habitación)."""
        assert self.runner is not None
        async with self._cerrojos[sala_id]:
            for evento in eventos:
                try:
                    await self.runner.handle(evento, forzar=forzar)
                except Exception:  # noqa: BLE001 - un fallo no debe parar el resto
                    _LOGGER.exception("Error al procesar el evento %s", evento)
        self._avisar()

    # --- Registro y señales -------------------------------------------------------
    def _registrar(self, datos: dict[str, Any]) -> None:
        """Guarda la última decisión de la habitación y avisa a las entidades."""
        self.ultimos[datos["room_id"]] = datos
        self._avisar()

    def _avisar(self) -> None:
        """Pide a las entidades que se actualicen."""
        async_dispatcher_send(self.hass, ajustes.SENAL_ACTUALIZACION)

    # --- Consultas para las entidades ------------------------------------------------
    def proximo(self, room_id: str) -> PlannedEvent | None:
        """Próximo evento (inicio/fin/reintento) de la habitación."""
        assert self.runner is not None
        return self.runner.planner.next_event(self.clock.now(), room_id)

    def tramo_activo(self, room_id: str) -> Slot | None:
        """Tramo habilitado activo ahora en una habitación habilitada."""
        sala = self.plan.room(room_id)
        if sala is None or not sala.enabled or self.runner is None:
            return None
        for tramo in self.runner.planner.active_slots(sala, self.clock.now()):
            if tramo.enabled:
                return tramo
        return None

    def overview(self) -> dict[str, Any]:
        """Resumen de solo lectura para el panel (línea de tiempo, estado, simulación)."""
        return OverviewBuilder(self.plan, HAState(self.hass)).build(self.clock.now(), self.ultimos)

    # --- Operaciones ----------------------------------------------------------------
    async def async_set_room_enabled(self, room_id: str, habilitada: bool) -> None:
        """Habilita o deshabilita una habitación y lo guarda."""
        sala = self.plan.room(room_id)
        if sala is not None:
            sala.enabled = habilitada
            await self.store.async_save(self.plan)
            self._avisar()

    async def async_set_away(self, ausente: bool) -> None:
        """Activa o desactiva el modo ausencia global y lo guarda."""
        self.plan.config.away_mode = ausente
        await self.store.async_save(self.plan)
        self._avisar()

    async def async_replace_plan(self, plan: Plan, motivo: str | None = None) -> None:
        """Sustituye el plan completo, lo guarda y reprograma.

        Si se indica `motivo`, antes se guarda una copia del plan actual en el historial.
        """
        assert self.runner is not None
        if motivo and self.plan.rooms:
            self.history.registrar(self.plan, motivo, self.clock.now())
            await self.history_store.async_save(self.history.to_list())
        self.plan = plan
        self.runner.set_plan(plan)
        await self.store.async_save(plan)
        self._ultimo_instante = self.clock.now()
        self._programar()
        self._programar_reevaluacion()
        self._avisar()

    # --- Edición de tramos (la validación completa la hace PlanEditor) -----------------
    def validar_tramo(self, room_id: str, tramo: dict[str, Any], slot_id: str | None) -> dict[str, Any]:
        """Valida un tramo sin guardarlo (vista previa del editor)."""
        return PlanEditor.validar(self.plan, room_id, tramo, slot_id)

    async def async_guardar_tramo(self, room_id: str, tramo: dict[str, Any],
                                  slot_id: str | None = None) -> str:
        """Crea o modifica un tramo. Lanza ConfigError si no es válido."""
        nuevo, id_ = PlanEditor.guardar_tramo(self.plan, room_id, tramo, slot_id)
        await self.async_replace_plan(nuevo, ajustes.MOTIVO_HIST_GUARDAR.format(
            habitacion=room_id, tramo=id_))
        return id_

    async def async_borrar_tramo(self, room_id: str, slot_id: str) -> None:
        """Elimina un tramo. Lanza ConfigError si no existe."""
        nuevo = PlanEditor.borrar_tramo(self.plan, room_id, slot_id)
        await self.async_replace_plan(nuevo, ajustes.MOTIVO_HIST_BORRAR.format(
            habitacion=room_id, tramo=slot_id))

    # --- Habitaciones -------------------------------------------------------------------
    def validar_habitacion(self, datos: dict[str, Any], room_id: str | None) -> dict[str, Any]:
        """Valida una habitación sin guardarla."""
        return PlanEditor.validar_habitacion(self.plan, datos, room_id)

    async def async_guardar_habitacion(self, datos: dict[str, Any], room_id: str | None = None) -> str:
        """Crea o modifica una habitación (copia previa en el historial). Lanza ConfigError."""
        nuevo, id_ = PlanEditor.guardar_habitacion(self.plan, datos, room_id)
        await self.async_replace_plan(nuevo, ajustes.MOTIVO_HIST_HAB_GUARDAR.format(habitacion=id_))
        return id_

    async def async_borrar_habitacion(self, room_id: str) -> None:
        """Elimina una habitación y sus tramos. Lanza ConfigError si no existe."""
        nuevo = PlanEditor.borrar_habitacion(self.plan, room_id)
        await self.async_replace_plan(nuevo, ajustes.MOTIVO_HIST_HAB_BORRAR.format(habitacion=room_id))

    def firma_habitaciones(self) -> list[tuple[str, str]]:
        """(id, nombre) de cada habitación: si cambia, hay que recrear las entidades."""
        return [(r.id, r.name) for r in self.plan.rooms]

    # --- Ajustes globales («Casa») --------------------------------------------------------
    def global_config(self) -> dict[str, Any]:
        """Ajustes globales completos (incluye los servicios de aviso: solo para administradores)."""
        return self.plan.config.to_dict()

    def validar_global(self, datos: dict[str, Any]) -> dict[str, Any]:
        """Valida los ajustes globales sin guardarlos."""
        return PlanEditor.validar_global(self.plan, datos)

    async def async_guardar_global(self, datos: dict[str, Any]) -> None:
        """Guarda los ajustes globales (copia previa en el historial). Lanza ConfigError."""
        nuevo = PlanEditor.guardar_global(self.plan, datos)
        await self.async_replace_plan(nuevo, ajustes.MOTIVO_HIST_GLOBAL)

    # --- Pausas -----------------------------------------------------------------------------
    def validar_pausa(self, pausa: dict[str, Any], pause_id: str | None, room_id: str | None) -> dict[str, Any]:
        """Valida una pausa sin guardarla."""
        return PlanEditor.validar_pausa(self.plan, pausa, pause_id, room_id)

    async def async_guardar_pausa(self, pausa: dict[str, Any], pause_id: str | None = None,
                                  room_id: str | None = None) -> str:
        """Crea o modifica una pausa (copia previa en el historial). Lanza ConfigError."""
        nuevo, id_ = PlanEditor.guardar_pausa(self.plan, pausa, pause_id, room_id)
        ambito = room_id or ajustes.PAUSA_AMBITO_CASA
        await self.async_replace_plan(nuevo, ajustes.MOTIVO_HIST_PAUSA_GUARDAR.format(ambito=ambito, pausa=id_))
        return id_

    async def async_borrar_pausa(self, pause_id: str, room_id: str | None = None) -> None:
        """Elimina una pausa. Lanza ConfigError si no existe."""
        nuevo = PlanEditor.borrar_pausa(self.plan, pause_id, room_id)
        ambito = room_id or ajustes.PAUSA_AMBITO_CASA
        await self.async_replace_plan(nuevo, ajustes.MOTIVO_HIST_PAUSA_BORRAR.format(ambito=ambito, pausa=pause_id))

    def en_pausa(self, room_id: str) -> tuple[Any, bool] | None:
        """Pausa vigente que afecta a la habitación: (pausa, es_global) o None."""
        sala = self.plan.room(room_id)
        if sala is None or self.runner is None:
            return None
        return self.runner.pausa_vigente(sala)

    def _programar_reevaluacion(self) -> None:
        """(Re)programa la reevaluación periódica de tramos omitidos por condiciones."""
        if self._cancelar_reevaluacion:
            self._cancelar_reevaluacion()
            self._cancelar_reevaluacion = None
        minutos = self.plan.config.reevaluate_minutes
        if minutos > 0:
            self._cancelar_reevaluacion = async_track_time_interval(
                self.hass, self._reevaluar, timedelta(minutes=minutos))

    async def _reevaluar(self, _ahora: datetime) -> None:
        """Reevalúa, habitación a habitación, los tramos omitidos por condiciones."""
        assert self.runner is not None
        for sala_id in sorted(self.runner.salas_pendientes()):
            async with self._cerrojos[sala_id]:
                try:
                    await self.runner.reevaluate(sala_id)
                except Exception:  # noqa: BLE001 - un fallo no debe parar el resto
                    _LOGGER.exception("Error al reevaluar %s", sala_id)
        self._avisar()

    def _medianoche(self, _ahora: datetime) -> None:
        """Las pausas cambian por fecha: se refrescan las entidades a medianoche."""
        self._avisar()

    def historial(self) -> list[dict[str, Any]]:
        """Versiones guardadas del plan (de la más reciente a la más antigua)."""
        return self.history.listar()

    async def async_restaurar(self, indice: int) -> None:
        """Restaura una versión; conserva el modo ausencia y las habitaciones habilitadas actuales."""
        plan = self.history.obtener(indice)
        plan.config.away_mode = self.plan.config.away_mode
        for sala in plan.rooms:
            actual = self.plan.room(sala.id)
            if actual is not None:
                sala.enabled = actual.enabled
        await self.async_replace_plan(plan, ajustes.MOTIVO_HIST_RESTAURAR)

    async def async_run_slot(self, room_id: str, slot_id: str, forzar: bool) -> None:
        """Ejecuta ahora el inicio de un tramo."""
        evento = PlannedEvent(self.clock.now(), ajustes.EVENTO_INICIO, room_id, slot_id)
        await self._ejecutar_sala(room_id, [evento], forzar=forzar)

    async def async_test_notification(self, canal_id: str) -> bool:
        """Envía un aviso de prueba a un canal."""
        assert self.notifier is not None
        return await self.notifier.probar(canal_id)
