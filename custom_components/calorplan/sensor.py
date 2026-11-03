# Versión: 2026.11.2
"""Sensores: próximo evento y última acción de cada habitación."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .core import settings as ajustes
from .entity import CalorplanEntity
from .ha.controller import Controller


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    """Crea dos sensores por habitación."""
    controlador: Controller = hass.data[ajustes.DOMAIN][entry.entry_id]
    entidades: list[SensorEntity] = []
    for sala in controlador.plan.rooms:
        entidades.append(ProximoSensor(controlador, sala.id, sala.name))
        entidades.append(UltimaAccionSensor(controlador, sala.id, sala.name))
    async_add_entities(entidades)


class ProximoSensor(CalorplanEntity, SensorEntity):
    """Marca de tiempo del próximo evento de la habitación."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, controlador: Controller, room_id: str, nombre: str) -> None:
        super().__init__(controlador)
        self._room_id = room_id
        self._attr_name = ajustes.NOMBRE_SENSOR_PROXIMO.format(habitacion=nombre)
        self._attr_unique_id = ajustes.ID_UNICO_SENSOR_PROXIMO.format(
            dominio=ajustes.DOMAIN, habitacion=room_id)

    @property
    def native_value(self) -> datetime | None:
        evento = self._controller.proximo(self._room_id)
        return evento.when if evento else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        evento = self._controller.proximo(self._room_id)
        if evento is None:
            return {}
        return {"slot_id": evento.slot_id, "event": evento.kind}


class UltimaAccionSensor(CalorplanEntity, SensorEntity):
    """Última decisión del motor en la habitación y su motivo."""

    def __init__(self, controlador: Controller, room_id: str, nombre: str) -> None:
        super().__init__(controlador)
        self._room_id = room_id
        self._attr_name = ajustes.NOMBRE_SENSOR_ULTIMA.format(habitacion=nombre)
        self._attr_unique_id = ajustes.ID_UNICO_SENSOR_ULTIMA.format(
            dominio=ajustes.DOMAIN, habitacion=room_id)

    @property
    def native_value(self) -> str | None:
        registro = self._controller.ultimos.get(self._room_id)
        return registro["action"] if registro else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return dict(self._controller.ultimos.get(self._room_id, {}))
