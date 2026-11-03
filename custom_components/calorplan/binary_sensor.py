# Versión: 2026.11.2
"""Sensor binario: la habitación está dentro de un tramo habilitado."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .core import settings as ajustes
from .entity import CalorplanEntity
from .ha.controller import Controller


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    """Crea un sensor de tramo activo por habitación."""
    controlador: Controller = hass.data[ajustes.DOMAIN][entry.entry_id]
    async_add_entities(TramoActivoSensor(controlador, r.id, r.name)
                       for r in controlador.plan.rooms)


class TramoActivoSensor(CalorplanEntity, BinarySensorEntity):
    """`on` mientras hay un tramo habilitado activo."""

    def __init__(self, controlador: Controller, room_id: str, nombre: str) -> None:
        super().__init__(controlador)
        self._room_id = room_id
        self._attr_name = ajustes.NOMBRE_TRAMO_ACTIVO.format(habitacion=nombre)
        self._attr_unique_id = ajustes.ID_UNICO_TRAMO_ACTIVO.format(
            dominio=ajustes.DOMAIN, habitacion=room_id)

    @property
    def is_on(self) -> bool:
        return self._controller.tramo_activo(self._room_id) is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        tramo = self._controller.tramo_activo(self._room_id)
        return {"slot_id": tramo.id, "slot": tramo.name} if tramo else {}
