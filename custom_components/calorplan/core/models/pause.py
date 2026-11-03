# Versión: 2026.11.8
"""Pausa: periodo en el que no se programan encendidos (vacaciones, visitas, obras...)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from .. import settings as ajustes
from .errors import ConfigError


def _fecha(valor: Any, nombre: str) -> date:
    """Convierte «AAAA-MM-DD» en `date` o lanza ConfigError."""
    try:
        return datetime.strptime(str(valor), ajustes.FORMATO_FECHA).date()
    except ValueError as err:
        raise ConfigError(ajustes.ERROR_PAUSA_FECHA.format(campo=nombre)) from err


@dataclass
class Pause:
    """Pausa entre dos días, ambos incluidos; sin `end` dura hasta que se quite."""

    id: str
    start: date
    end: date | None = None
    reason: str = ""
    enabled: bool = True

    def activa_en(self, dia: date) -> bool:
        """Indica si la pausa está vigente (y habilitada) en un día."""
        return self.enabled and self.start <= dia and (self.end is None or dia <= self.end)

    def estado(self, hoy: date) -> str:
        """Estado respecto a hoy: disabled | active | upcoming | expired."""
        if not self.enabled:
            return ajustes.PAUSA_DESHABILITADA
        if self.start > hoy:
            return ajustes.PAUSA_PROXIMA
        if self.end is not None and self.end < hoy:
            return ajustes.PAUSA_CADUCADA
        return ajustes.PAUSA_ACTIVA

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "Pause":
        """Crea la pausa validando sus campos."""
        if not isinstance(datos, dict):
            raise ConfigError(ajustes.ERROR_PAUSA_OBJETO)
        id_ = str(datos.get("id", "")).strip()
        if not id_:
            raise ConfigError(ajustes.ERROR_PAUSA_ID)
        inicio = _fecha(datos.get("from"), "from")
        # «Sin fecha de fin» es explícito (null); un valor vacío es un descuido y se rechaza
        fin = _fecha(datos["until"], "until") if datos.get("until") is not None else None
        if fin is not None and fin < inicio:
            raise ConfigError(ajustes.ERROR_PAUSA_ORDEN)
        return cls(id=id_, start=inicio, end=fin, reason=str(datos.get("reason", "")).strip(),
                   enabled=bool(datos.get("enabled", True)))

    def to_dict(self) -> dict[str, Any]:
        """Serializa la pausa."""
        return {
            "id": self.id,
            "reason": self.reason,
            "from": self.start.strftime(ajustes.FORMATO_FECHA),
            "until": self.end.strftime(ajustes.FORMATO_FECHA) if self.end else None,
            "enabled": self.enabled,
        }


def pausas_desde(datos: Any, donde: str) -> list[Pause]:
    """Lista de pausas validada (ids únicos dentro del mismo propietario)."""
    if datos is None:
        return []
    if not isinstance(datos, list):
        raise ConfigError(f"{donde}: " + ajustes.ERROR_PAUSAS_LISTA)
    pausas = [Pause.from_dict(p) for p in datos]
    ids = [p.id for p in pausas]
    if len(ids) != len(set(ids)):
        raise ConfigError(f"{donde}: " + ajustes.ERROR_PAUSA_REPETIDA)
    return pausas


def pausa_activa(pausas: list[Pause], dia: date) -> Pause | None:
    """Primera pausa vigente en un día, o None."""
    return next((p for p in pausas if p.activa_en(dia)), None)
