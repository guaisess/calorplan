# Versión: 2026.11.8
"""Habitación: actuador, sensores, avisos y tramos."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .. import settings as ajustes
from .actuator import Actuator
from .errors import ConfigError
from .notify import NotifyConfig
from .pause import Pause, pausas_desde
from .slot import Slot


@dataclass
class Room:
    """Habitación con su calefacción y sus tramos horarios."""

    id: str
    name: str
    actuator: Actuator
    sensors: list[str] = field(default_factory=list)
    indoor_aggregation: str = ajustes.AGREGACION_DEFECTO
    enabled: bool = True
    notify: NotifyConfig | None = None
    slots: list[Slot] = field(default_factory=list)
    pauses: list[Pause] = field(default_factory=list)

    def slot(self, slot_id: str) -> Slot | None:
        """Devuelve el tramo con ese id, o None."""
        return next((s for s in self.slots if s.id == slot_id), None)

    def validar(self) -> None:
        """Comprueba ids únicos y ausencia de solapes entre tramos."""
        ids = [s.id for s in self.slots]
        if len(ids) != len(set(ids)):
            raise ConfigError(f"Habitación '{self.id}': ids de tramo repetidos")
        for i, a in enumerate(self.slots):
            for b in self.slots[i + 1:]:
                if a.solapa_con(b):
                    raise ConfigError(
                        f"Habitación '{self.id}': los tramos '{a.id}' y '{b.id}' se solapan")

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "Room":
        """Crea la habitación desde un diccionario y la valida."""
        if not isinstance(datos, dict):
            raise ConfigError("Una habitación debe ser un objeto")
        id_ = str(datos.get("id", "")).strip()
        if not id_:
            raise ConfigError("Una habitación necesita 'id'")
        sensores = datos.get("sensors", [])
        if not isinstance(sensores, list):
            raise ConfigError(f"Habitación '{id_}': 'sensors' debe ser una lista")
        agregacion = datos.get("indoor_aggregation", ajustes.AGREGACION_DEFECTO)
        if agregacion not in ajustes.AGREGACIONES:
            raise ConfigError(f"Habitación '{id_}': agregación no válida: {agregacion}")
        sala = cls(
            id=id_,
            name=str(datos.get("name", id_)),
            actuator=Actuator.from_dict(datos.get("actuator")),
            sensors=[str(s) for s in sensores],
            indoor_aggregation=agregacion,
            enabled=bool(datos.get("enabled", True)),
            notify=NotifyConfig.from_dict(datos.get("notify")),
            slots=[Slot.from_dict(s) for s in datos.get("slots", [])],
            pauses=pausas_desde(datos.get("pauses"), f"Habitación '{id_}'"),
        )
        sala.validar()
        return sala

    def to_dict(self) -> dict[str, Any]:
        """Serializa la habitación."""
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "actuator": self.actuator.to_dict(),
            "sensors": list(self.sensors),
            "indoor_aggregation": self.indoor_aggregation,
            "notify": self.notify.to_dict() if self.notify else None,
            "slots": [s.to_dict() for s in self.slots],
            "pauses": [p.to_dict() for p in self.pauses],
        }
