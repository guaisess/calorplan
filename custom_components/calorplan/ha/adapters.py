# Versión: 2026.11.2
"""Adaptadores de los puertos del núcleo sobre Home Assistant."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from ..core import settings as ajustes
from ..core.engine.ports import (ActuatorPort, ClockPort, EventPort, NotifyPort,
                                 StatePort)


class HAState(StatePort):
    """Lee estados de la máquina de estados de Home Assistant."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    def get_state(self, entity_id: str) -> str | None:
        estado = self._hass.states.get(entity_id)
        return estado.state if estado else None

    def get_float(self, entity_id: str) -> float | None:
        valor = self.get_state(entity_id)
        if valor is None or valor in ajustes.ESTADOS_NO_DISPONIBLE:
            return None
        try:
            return float(valor)
        except ValueError:
            return None

    def is_state(self, entity_id: str, state: str) -> bool:
        return self.get_state(entity_id) == state

    def is_available(self, entity_id: str) -> bool:
        valor = self.get_state(entity_id)
        return valor is not None and valor not in ajustes.ESTADOS_NO_DISPONIBLE


class HAActuator(ActuatorPort):
    """Llama a los servicios `climate.*` y `switch.*`."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def _llamar(self, dominio: str, servicio: str, datos: dict[str, Any]) -> None:
        await self._hass.services.async_call(dominio, servicio, datos, blocking=True)

    async def climate_heat(self, entity_id: str, hvac_mode: str, temperature: float | None) -> None:
        await self._llamar("climate", "set_hvac_mode",
                           {"entity_id": entity_id, "hvac_mode": hvac_mode})
        if temperature is not None:
            await self._llamar("climate", "set_temperature",
                               {"entity_id": entity_id, "temperature": temperature})

    async def climate_off(self, entity_id: str) -> None:
        await self._llamar("climate", "set_hvac_mode",
                           {"entity_id": entity_id, "hvac_mode": ajustes.HVAC_MODO_APAGADO})

    async def switch_set(self, entity_id: str, on: bool) -> None:
        await self._llamar("switch", "turn_on" if on else "turn_off", {"entity_id": entity_id})


class HANotify(NotifyPort):
    """Envía avisos con servicios `notify.<nombre>`."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def send(self, service: str, title: str, message: str) -> None:
        dominio, _, nombre = service.partition(".")
        await self._hass.services.async_call(
            dominio, nombre, {"title": title, "message": message}, blocking=True)


class HAClock(ClockPort):
    """Reloj de Home Assistant (hora local con zona horaria)."""

    def now(self) -> datetime:
        return dt_util.now()

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class HAEvents(EventPort):
    """Dispara eventos en el bus y reenvía los registros al controlador."""

    def __init__(self, hass: HomeAssistant, al_registrar: Callable[[dict[str, Any]], None]) -> None:
        self._hass = hass
        self._al_registrar = al_registrar

    def fire(self, event_type: str, data: dict[str, Any]) -> None:
        self._hass.bus.async_fire(event_type, data)

    def record(self, data: dict[str, Any]) -> None:
        self._al_registrar(data)
