# Versión: 2026.11.5
"""API WebSocket (solo lectura) que usa el panel."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .core import settings as ajustes


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): ajustes.WS_OVERVIEW})
@callback
def ws_overview(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                msg: dict[str, Any]) -> None:
    """Devuelve el resumen completo: plan visible, línea de tiempo y simulación."""
    instancias = hass.data.get(ajustes.DOMAIN) or {}
    if not instancias:
        connection.send_error(msg["id"], "not_loaded", "Calorplan no está configurado")
        return
    controlador = next(iter(instancias.values()))
    connection.send_result(msg["id"], controlador.overview())


def async_registrar(hass: HomeAssistant) -> None:
    """Registra los comandos WebSocket."""
    websocket_api.async_register_command(hass, ws_overview)
