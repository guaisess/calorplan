# Versión: 2026.11.5
"""Calorplan: programador de calefacción por habitación para Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import panel, services, websocket_api
from .core import settings as ajustes
from .ha.controller import Controller


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Pone en marcha el controlador, las plataformas, la API y el panel."""
    controlador = Controller(hass)
    await controlador.async_start()
    hass.data.setdefault(ajustes.DOMAIN, {})[entry.entry_id] = controlador
    await hass.config_entries.async_forward_entry_setups(entry, list(ajustes.PLATAFORMAS))
    services.async_registrar(hass)
    websocket_api.async_registrar(hass)
    await panel.async_registrar_panel(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarga las plataformas y detiene el controlador."""
    descargado = await hass.config_entries.async_unload_platforms(
        entry, list(ajustes.PLATAFORMAS))
    if descargado:
        controlador: Controller = hass.data[ajustes.DOMAIN].pop(entry.entry_id)
        controlador.async_stop()
        if not hass.data[ajustes.DOMAIN]:
            services.async_quitar(hass)
            panel.async_quitar_panel(hass)
    return descargado
