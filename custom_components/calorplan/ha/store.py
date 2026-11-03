# Versión: 2026.11.2
"""Almacén persistente del plan (`.storage/calorplan`)."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from ..core import settings as ajustes
from ..core.models import ConfigError, Plan


class PlanStore:
    """Carga y guarda el plan usando el `Store` de Home Assistant."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store = Store(hass, ajustes.SCHEMA_VERSION, ajustes.STORAGE_KEY)

    async def async_load(self) -> Plan:
        """Lee el plan guardado; si no hay datos o son inválidos, un plan vacío."""
        datos = await self._store.async_load()
        try:
            return Plan.from_dict(datos)
        except ConfigError:
            return Plan()

    async def async_save(self, plan: Plan) -> None:
        """Guarda el plan completo."""
        await self._store.async_save(plan.to_dict())


class HistoryStore:
    """Persistencia del historial de versiones del plan."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store = Store(hass, ajustes.SCHEMA_VERSION, ajustes.HISTORIAL_STORAGE_KEY)

    async def async_load(self) -> list[dict]:
        """Lee las versiones guardadas (lista vacía si no hay)."""
        datos = await self._store.async_load()
        return list((datos or {}).get("entries", []))

    async def async_save(self, entradas: list[dict]) -> None:
        """Guarda las versiones."""
        await self._store.async_save({"entries": entradas})
