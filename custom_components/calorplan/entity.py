# Versión: 2026.11.2
"""Entidad base: se actualiza con la señal del controlador."""
from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .core import settings as ajustes
from .ha.controller import Controller


class CalorplanEntity(Entity):
    """Base común de las entidades de Calorplan."""

    _attr_should_poll = False

    def __init__(self, controlador: Controller) -> None:
        self._controller = controlador

    async def async_added_to_hass(self) -> None:
        """Se suscribe a las actualizaciones del controlador."""
        self.async_on_remove(async_dispatcher_connect(
            self.hass, ajustes.SENAL_ACTUALIZACION, self._al_actualizar))

    @callback
    def _al_actualizar(self) -> None:
        """Refresca el estado de la entidad."""
        self.async_write_ha_state()
