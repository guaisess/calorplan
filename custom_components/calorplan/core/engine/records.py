# Versión: 2026.11.2
"""Estructuras de datos del motor: eventos planificados, decisiones y registros."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .. import settings as ajustes


@dataclass(frozen=True)
class PlannedEvent:
    """Evento planificado: inicio, fin o reintento de un tramo."""

    when: datetime
    kind: str  # ajustes.EVENTO_INICIO | EVENTO_FIN | EVENTO_REINTENTO
    room_id: str
    slot_id: str

    @property
    def orden(self) -> tuple:
        """Clave de ordenación: instante y luego fin → reintento → inicio."""
        return (self.when, ajustes.ORDEN_EVENTOS[self.kind], self.room_id, self.slot_id)


@dataclass
class Decision:
    """Resultado de evaluar las condiciones de un tramo."""

    start: bool
    code: str
    reason: str
    outdoor: float | None = None
    indoor: float | None = None


@dataclass
class Record:
    """Decisión ejecutada (o simulada) por el motor."""

    when: datetime
    room_id: str
    room_name: str
    slot_id: str
    slot_name: str
    kind: str  # tipo de evento que la provocó
    action: str  # ajustes.ACCION_*
    code: str  # ajustes.COD_*
    reason: str
    setpoint: float | None = None
    outdoor: float | None = None
    indoor: float | None = None
    simulated: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serializa el registro (datos del evento del bus y de las entidades)."""
        return {
            "time": self.when.isoformat(),
            "room_id": self.room_id,
            "room": self.room_name,
            "slot_id": self.slot_id,
            "slot": self.slot_name,
            "event": self.kind,
            "action": self.action,
            "code": self.code,
            "reason": self.reason,
            "setpoint": self.setpoint,
            "outdoor": self.outdoor,
            "indoor": self.indoor,
            "simulated": self.simulated,
        }
