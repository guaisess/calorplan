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
    entidades: list[BinarySensorEntity] = []
    for sala in controlador.plan.rooms:
        entidades.append(TramoActivoSensor(controlador, sala.id, sala.name))
        entidades.append(EnPausaSensor(controlador, sala.id, sala.name))
    async_add_entities(entidades)


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


class EnPausaSensor(CalorplanEntity, BinarySensorEntity):
    """`on` mientras hay una pausa vigente (de la habitación o de toda la casa)."""

    def __init__(self, controlador: Controller, room_id: str, nombre: str) -> None:
        super().__init__(controlador)
        self._room_id = room_id
        self._attr_name = ajustes.NOMBRE_EN_PAUSA.format(habitacion=nombre)
        self._attr_unique_id = ajustes.ID_UNICO_EN_PAUSA.format(
            dominio=ajustes.DOMAIN, habitacion=room_id)

    @property
    def is_on(self) -> bool:
        return self._controller.en_pausa(self._room_id) is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        encontrada = self._controller.en_pausa(self._room_id)
        if encontrada is None:
            return {}
        pausa, es_global = encontrada
        return {"scope": "global" if es_global else "room", "reason": pausa.reason,
                "from": pausa.start.isoformat(), "until": pausa.end.isoformat() if pausa.end else None}
