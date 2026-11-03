# Versión: 2026.11.5
"""Resumen de solo lectura para el panel: línea de tiempo, estado y simulación.

El simulador responde «¿qué haría ahora?» evaluando las condiciones con los
valores actuales, sin ejecutar nada ni avisar.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .. import settings as ajustes
from ..models import Plan, Room, Slot
from .evaluator import Evaluator
from .planner import Planner
from .ports import StatePort
from .timeline import semana_habitacion


class OverviewBuilder:
    """Construye el diccionario que consume el panel."""

    def __init__(self, plan: Plan, state: StatePort) -> None:
        self._plan = plan
        self._state = state
        self._planner = Planner(plan)
        self._evaluator = Evaluator(state)

    # --- Simulación ---------------------------------------------------------
    def _simular(self, sala: Room, ahora: datetime) -> dict[str, Any] | None:
        """Decisión que tomaría el motor para el tramo activo (o el próximo)."""
        activos = [t for t in self._planner.active_slots(sala, ahora)]
        tramo: Slot | None
        if activos:
            tramo, activo = activos[0], True
        else:
            inicio = self._planner.next_start(ahora, sala.id)
            tramo = sala.slot(inicio.slot_id) if inicio else None
            activo = False
        if tramo is None:
            return None
        bloqueo = None
        if not sala.enabled:
            bloqueo = ajustes.COD_HABITACION_DESHABILITADA
        elif not tramo.enabled:
            bloqueo = ajustes.COD_TRAMO_DESHABILITADO
        elif self._plan.config.away_mode:
            bloqueo = ajustes.COD_AUSENCIA
        decision = self._evaluator.evaluate(sala, tramo, self._plan.config)
        return {
            "slot_id": tramo.id,
            "slot": tramo.name,
            "active": activo,
            "would_start": decision.start and bloqueo is None,
            "code": bloqueo or decision.code,
            "reason": decision.reason,
            "outdoor": decision.outdoor,
            "indoor": decision.indoor,
        }

    # --- Habitación ------------------------------------------------------------
    def _habitacion(self, sala: Room, ahora: datetime,
                    ultimos: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Datos de una habitación: configuración visible, estado y simulación."""
        proximo = self._planner.next_event(ahora, sala.id)
        activo = next((t for t in self._planner.active_slots(sala, ahora) if t.enabled), None)
        return {
            "id": sala.id,
            "name": sala.name,
            "enabled": sala.enabled,
            "actuator": {"type": sala.actuator.type, "entity_id": sala.actuator.entity_id,
                         "state": self._state.get_state(sala.actuator.entity_id)},
            "slots": [{
                "id": t.id, "name": t.name, "enabled": t.enabled, "days": t.days,
                "start": t.start.strftime(ajustes.FORMATO_HORA),
                "duration_minutes": t.duracion_minutos, "setpoint": t.setpoint,
                "outdoor_below": t.outdoor_below, "indoor_below": t.indoor_below,
            } for t in sala.slots],
            "week": semana_habitacion(sala),
            "active_slot": activo.id if activo else None,
            "next": ({"time": proximo.when.isoformat(), "kind": proximo.kind,
                      "slot_id": proximo.slot_id} if proximo else None),
            "last": ultimos.get(sala.id),
            "simulation": self._simular(sala, ahora),
        }

    def build(self, ahora: datetime, ultimos: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Resumen completo para el panel (no incluye servicios ni identificadores de aviso)."""
        cfg = self._plan.config
        return {
            "version": ajustes.VERSION,
            "now": ahora.isoformat(),
            "weekday": ahora.weekday(),
            "minute": ahora.hour * 60 + ahora.minute,
            "shadow_mode": cfg.shadow_mode,
            "away_mode": cfg.away_mode,
            "outdoor": self._evaluator.aggregate_min(cfg.outdoor_sensors),
            "rooms": [self._habitacion(r, ahora, ultimos) for r in self._plan.rooms],
        }
