# Versión: 2026.11.6
"""Historial de versiones del plan (copia automática antes de cada cambio)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .. import settings as ajustes
from ..models import ConfigError, Plan


class History:
    """Guarda las últimas N versiones del plan, de la más reciente a la más antigua."""

    def __init__(self, entradas: list[dict[str, Any]] | None = None,
                 maximo: int = ajustes.HISTORIAL_MAX) -> None:
        self._maximo = maximo
        self._entradas: list[dict[str, Any]] = list(entradas or [])[:maximo]

    def registrar(self, plan: Plan, motivo: str, cuando: datetime) -> None:
        """Guarda una copia del plan (antes de cambiarlo)."""
        self._entradas.insert(0, {"time": cuando.isoformat(), "reason": motivo,
                                  "plan": plan.to_dict()})
        del self._entradas[self._maximo:]

    def listar(self) -> list[dict[str, Any]]:
        """Resumen de cada versión (sin el plan completo)."""
        resumen = []
        for indice, entrada in enumerate(self._entradas):
            salas = entrada["plan"].get("rooms", [])
            resumen.append({
                "index": indice, "time": entrada["time"], "reason": entrada["reason"],
                "rooms": len(salas), "slots": sum(len(r.get("slots", [])) for r in salas)})
        return resumen

    def obtener(self, indice: int) -> Plan:
        """Reconstruye (y valida) el plan de una versión."""
        if not 0 <= indice < len(self._entradas):
            raise ConfigError(ajustes.ERROR_VERSION_INEXISTENTE.format(indice=indice))
        return Plan.from_dict(self._entradas[indice]["plan"])

    def to_list(self) -> list[dict[str, Any]]:
        """Datos para persistir."""
        return list(self._entradas)
