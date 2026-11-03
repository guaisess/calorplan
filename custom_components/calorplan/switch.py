# Versión: 2026.11.2
"""Interruptores: habilitar cada habitación y modo ausencia global."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .core import settings as ajustes
from .entity import CalorplanEntity
from .ha.controller import Controller


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    """Crea el modo ausencia y un interruptor por habitación."""
    controlador: Controller = hass.data[ajustes.DOMAIN][entry.entry_id]
    entidades: list[SwitchEntity] = [AusenciaSwitch(controlador)]
    entidades += [HabitacionSwitch(controlador, r.id, r.name) for r in controlador.plan.rooms]
    async_add_entities(entidades)


class HabitacionSwitch(CalorplanEntity, SwitchEntity):
    """Habilita o deshabilita todos los tramos de una habitación."""

    def __init__(self, controlador: Controller, room_id: str, nombre: str) -> None:
        super().__init__(controlador)
        self._room_id = room_id
        self._attr_name = ajustes.NOMBRE_SWITCH_HABITACION.format(habitacion=nombre)
        self._attr_unique_id = ajustes.ID_UNICO_SWITCH_HABITACION.format(
            dominio=ajustes.DOMAIN, habitacion=room_id)

    @property
    def is_on(self) -> bool:
        sala = self._controller.plan.room(self._room_id)
        return bool(sala and sala.enabled)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._controller.async_set_room_enabled(self._room_id, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._controller.async_set_room_enabled(self._room_id, False)


class AusenciaSwitch(CalorplanEntity, SwitchEntity):
    """Modo ausencia: omite los inicios (los apagados siguen funcionando)."""

    _attr_name = ajustes.NOMBRE_SWITCH_AUSENCIA
    _attr_unique_id = ajustes.ID_UNICO_SWITCH_AUSENCIA.format(dominio=ajustes.DOMAIN)

    @property
    def is_on(self) -> bool:
        return self._controller.plan.config.away_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._controller.async_set_away(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._controller.async_set_away(False)
