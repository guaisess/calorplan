# Versión: 2026.11.16
"""Resumen de solo lectura para el panel: línea de tiempo, estado y simulación.

El simulador responde «¿qué haría ahora?» evaluando las condiciones con los
valores actuales, sin ejecutar nada ni avisar.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .. import settings as ajustes
from ..models import Pause, Plan, Room, Slot, pausa_activa
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

    # --- Pausas -------------------------------------------------------------------
    def _pausa_de(self, sala: Room, ahora: datetime) -> tuple[Pause, str] | None:
        """Pausa vigente que afecta a la habitación: (pausa, ámbito «room» o «global»)."""
        hoy = ahora.date()
        propia = pausa_activa(sala.pauses, hoy)
        if propia is not None:
            return propia, "room"
        global_ = pausa_activa(self._plan.config.pauses, hoy)
        return (global_, "global") if global_ is not None else None

    @staticmethod
    def _pausas(pausas: list[Pause], hoy) -> list[dict[str, Any]]:
        """Pausas con su estado respecto a hoy."""
        return [{**p.to_dict(), "status": p.estado(hoy)} for p in pausas]

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
        elif self._pausa_de(sala, ahora) is not None:
            bloqueo = ajustes.COD_PAUSA
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
            "indoor_aggregation": sala.indoor_aggregation,
            "config": {k: v for k, v in sala.to_dict().items() if k != "slots"},
            "actuator": {"type": sala.actuator.type, "entity_id": sala.actuator.entity_id,
                         "state": self._state.get_state(sala.actuator.entity_id)},
            "slots": [{
                "id": t.id, "name": t.name, "enabled": t.enabled, "days": t.days,
                "start": t.start.strftime(ajustes.FORMATO_HORA),
                "duration_minutes": t.duracion_minutos, "setpoint": t.setpoint,
                "outdoor_below": t.outdoor_below, "indoor_below": t.indoor_below,
                "config": t.to_dict(),  # datos completos para el editor
            } for t in sala.slots],
            "week": semana_habitacion(sala),
            "active_slot": activo.id if activo else None,
            "next": ({"time": proximo.when.isoformat(), "kind": proximo.kind,
                      "slot_id": proximo.slot_id} if proximo else None),
            "last": ultimos.get(sala.id),
            "simulation": self._simular(sala, ahora),
            "pauses": self._pausas(sala.pauses, ahora.date()),
            "paused_by": self._resumen_pausa(self._pausa_de(sala, ahora)),
        }

    @staticmethod
    def _resumen_pausa(encontrada: tuple[Pause, str] | None) -> dict[str, Any] | None:
        """Resumen de la pausa vigente: ámbito, motivo y hasta cuándo."""
        if encontrada is None:
            return None
        pausa, ambito = encontrada
        return {"scope": ambito, "id": pausa.id, "reason": pausa.reason,
                "until": pausa.end.strftime(ajustes.FORMATO_FECHA) if pausa.end else None}

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
            "today": ahora.strftime(ajustes.FORMATO_FECHA),
            "global_pauses": self._pausas(cfg.pauses, ahora.date()),
            "outdoor": self._evaluator.aggregate(cfg.outdoor_sensors, cfg.outdoor_aggregation),
            "outdoor_aggregation": cfg.outdoor_aggregation,
            "channels": [c.id for c in cfg.channels],  # solo ids: nunca los servicios
            "rooms": [self._habitacion(r, ahora, ultimos) for r in self._plan.rooms],
        }

    @staticmethod
    def _norm(texto: Any) -> str:
        """Motivo normalizado para compararlo (sin mayúsculas ni espacios sobrantes)."""
        return " ".join(str(texto or "").split()).casefold()

    def build_card(self, ahora: datetime, ultimos: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Resumen reducido para la tarjeta Lovelace (la ve cualquier usuario).

        Solo lleva lo necesario para dibujarla: sin entidades, canales ni plantillas.
        """
        o = self.build(ahora, ultimos)
        minuto, dia = o["minute"], o["weekday"]
        rapida = self._norm(ajustes.MOTIVO_PAUSA_RAPIDA)
        activas_casa = [p for p in o["global_pauses"] if p["status"] == ajustes.PAUSA_ACTIVA]
        habitaciones = []
        for h in o["rooms"]:
            tramos = {t["id"]: t for t in h["slots"]}
            hoy = []
            activo = None
            for seg in h["week"][dia]:
                t = tramos.get(seg["slot_id"], {})
                hoy.append({"slot_id": seg["slot_id"], "name": t.get("name", seg["slot_id"]),
                            "start": seg["start"], "end": seg["end"],
                            "enabled": bool(t.get("enabled", True)) and h["enabled"],
                            "continued_from_prev": seg["continued_from_prev"],
                            "continues_next": seg["continues_next"]})
                if h["active_slot"] == seg["slot_id"] and seg["start"] <= minuto < seg["end"]:
                    activo = {"id": seg["slot_id"], "name": t.get("name", seg["slot_id"]), "end": seg["end"]}
            if activo is None and h["active_slot"] in tramos:  # tramo que viene de ayer
                activo = {"id": h["active_slot"], "name": tramos[h["active_slot"]]["name"], "end": None}
            siguiente = h["next"]
            if siguiente:
                siguiente = {**siguiente, "slot_name": tramos.get(siguiente["slot_id"], {}).get("name", siguiente["slot_id"])}
            ultima = h["last"] or {}
            habitaciones.append({
                "id": h["id"], "name": h["name"], "enabled": h["enabled"],
                "kind": h["actuator"]["type"], "state": h["actuator"]["state"],
                "active": activo, "next": siguiente, "paused_by": h["paused_by"],
                "quick_pause": any(p["status"] == ajustes.PAUSA_ACTIVA and self._norm(p["reason"]) == rapida
                                   for p in h["pauses"]),
                "today": hoy,
                "last": {"action": ultima.get("action"), "code": ultima.get("code"),
                         "time": ultima.get("time"), "simulated": ultima.get("simulated")} if ultima else None,
            })
        return {
            "version": o["version"], "now": o["now"], "today": o["today"], "weekday": dia, "minute": minuto,
            "shadow_mode": o["shadow_mode"], "away_mode": o["away_mode"], "outdoor": o["outdoor"],
            "quick_pause_reason": ajustes.MOTIVO_PAUSA_RAPIDA,
            "global_pause": ({"reason": activas_casa[0]["reason"], "until": activas_casa[0]["until"]}
                             if activas_casa else None),
            "rooms": habitaciones,
        }
