# Versión: 2026.11.25
"""Interruptores: habilitar cada habitación, cada grupo y modo ausencia global."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .core import settings as ajustes
from .core.engine.editor import generar_id
from .entity import CalorplanEntity
from .ha.controller import Controller


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    """Crea el modo ausencia y un interruptor por habitación."""
    controlador: Controller = hass.data[ajustes.DOMAIN][entry.entry_id]
    entidades: list[SwitchEntity] = [AusenciaSwitch(controlador)]
    entidades += [HabitacionSwitch(controlador, r.id, r.name) for r in controlador.plan.rooms]
    grupos = list(dict.fromkeys(r.group for r in controlador.plan.rooms if r.group))
    entidades += [GrupoSwitch(controlador, g) for g in grupos]
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


class GrupoSwitch(CalorplanEntity, SwitchEntity):
    """Habilita o deshabilita de una vez todos los dispositivos de un grupo (una estancia)."""

    _attr_icon = ajustes.ICONO_SWITCH_GRUPO

    def __init__(self, controlador: Controller, grupo: str) -> None:
        super().__init__(controlador)
        self._grupo = grupo
        self._attr_name = ajustes.NOMBRE_SWITCH_GRUPO.format(grupo=grupo)
        self._attr_unique_id = ajustes.ID_UNICO_SWITCH_GRUPO.format(
            dominio=ajustes.DOMAIN, grupo=generar_id(grupo, [], "grupo"))

    @property
    def is_on(self) -> bool:
        """Encendido si al menos un dispositivo del grupo está habilitado (apagado solo si todos lo están)."""
        salas = [self._controller.plan.room(i) for i in self._controller.habitaciones_del_grupo(self._grupo)]
        return any(s is not None and s.enabled for s in salas)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"rooms": self._controller.habitaciones_del_grupo(self._grupo)}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._controller.async_set_group_enabled(self._grupo, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._controller.async_set_group_enabled(self._grupo, False)


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
