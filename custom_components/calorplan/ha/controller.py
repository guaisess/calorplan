# Versión: 2026.11.2
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
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.start import async_at_started

from ..core import settings as ajustes
from ..core.engine import Notifier, PlannedEvent, Runner
from ..core.engine.overview import OverviewBuilder
from ..core.models import Plan, Slot
from .adapters import HAActuator, HAClock, HAEvents, HANotify, HAState
from .store import PlanStore

_LOGGER = logging.getLogger(__name__)


class Controller:
    """Programa un único temporizador al próximo evento y ejecuta el motor."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.store = PlanStore(hass)
        self.clock = HAClock()
        self.plan = Plan()
        self.runner: Runner | None = None
        self.notifier: Notifier | None = None
        # Última decisión por habitación (para los sensores)
        self.ultimos: dict[str, dict[str, Any]] = {}
        self._cancelar_temporizador: Callable[[], None] | None = None
        self._cancelar_arranque: Callable[[], None] | None = None
        self._ultimo_instante: datetime = self.clock.now()
        self._tareas: set[asyncio.Task] = set()
        self._cerrojos: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    # --- Ciclo de vida -----------------------------------------------------------
    async def async_start(self) -> None:
        """Carga el plan, crea el motor y programa el primer evento."""
        self.plan = await self.store.async_load()
        self.notifier = Notifier(self.plan, HANotify(self.hass), self.clock)
        self.runner = Runner(self.plan, HAState(self.hass), HAActuator(self.hass),
                             self.notifier, self.clock, HAEvents(self.hass, self._registrar))
        self._ultimo_instante = self.clock.now()
        self._cancelar_arranque = async_at_started(self.hass, self._al_arrancar)
        self._programar()

    def async_stop(self) -> None:
        """Cancela el temporizador y las tareas en curso."""
        if self._cancelar_temporizador:
            self._cancelar_temporizador()
            self._cancelar_temporizador = None
        if self._cancelar_arranque:
            self._cancelar_arranque()
            self._cancelar_arranque = None
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

    async def async_replace_plan(self, plan: Plan) -> None:
        """Sustituye el plan completo (importación), lo guarda y reprograma."""
        assert self.runner is not None
        self.plan = plan
        self.runner.set_plan(plan)
        await self.store.async_save(plan)
        self._ultimo_instante = self.clock.now()
        self._programar()
        self._avisar()

    async def async_run_slot(self, room_id: str, slot_id: str, forzar: bool) -> None:
        """Ejecuta ahora el inicio de un tramo."""
        evento = PlannedEvent(self.clock.now(), ajustes.EVENTO_INICIO, room_id, slot_id)
        await self._ejecutar_sala(room_id, [evento], forzar=forzar)

    async def async_test_notification(self, canal_id: str) -> bool:
        """Envía un aviso de prueba a un canal."""
        assert self.notifier is not None
        return await self.notifier.probar(canal_id)
