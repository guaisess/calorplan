# Versión: 2026.11.5
"""Registro del panel lateral (web component sin compilación)."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .core import settings as ajustes


async def async_registrar_panel(hass: HomeAssistant) -> None:
    """Sirve los ficheros del panel y lo añade a la barra lateral (solo administradores)."""
    if not hass.data.get(ajustes.CLAVE_ESTATICO):
        carpeta = Path(__file__).parent / ajustes.ESTATICO_CARPETA
        await hass.http.async_register_static_paths(
            [StaticPathConfig(ajustes.ESTATICO_URL, str(carpeta), False)])
        hass.data[ajustes.CLAVE_ESTATICO] = True  # las rutas estáticas no se pueden quitar
    if hass.data.get(ajustes.CLAVE_PANEL):
        return
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=ajustes.PANEL_COMPONENTE,
        frontend_url_path=ajustes.PANEL_URL,
        module_url=f"{ajustes.ESTATICO_URL}/{ajustes.PANEL_FICHERO}?v={ajustes.VERSION}",
        sidebar_title=ajustes.PANEL_TITULO,
        sidebar_icon=ajustes.PANEL_ICONO,
        require_admin=True,
        config={},
    )
    hass.data[ajustes.CLAVE_PANEL] = True


def async_quitar_panel(hass: HomeAssistant) -> None:
    """Quita el panel de la barra lateral."""
    if hass.data.pop(ajustes.CLAVE_PANEL, False):
        frontend.async_remove_panel(hass, ajustes.PANEL_URL)
