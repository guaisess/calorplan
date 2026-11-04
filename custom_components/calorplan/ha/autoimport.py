# Versión: 2026.11.17
"""Importación automática de `calorplan.json` en el primer arranque (alta sencilla)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant

from ..core import settings as ajustes
from ..core.models import ConfigError, Plan
from .controller import Controller

_LOGGER = logging.getLogger(__name__)


def _leer(ruta: Path) -> dict | None:
    """Lee el JSON si existe (bloqueante); `None` si no hay fichero."""
    if not ruta.is_file():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def _avisar(hass: HomeAssistant, mensaje: str) -> None:
    """Deja un aviso visible en Home Assistant."""
    persistent_notification.async_create(
        hass, mensaje, title=ajustes.AUTOIMPORTAR_TITULO, notification_id=ajustes.AUTOIMPORTAR_ID_AVISO)


async def async_importar_inicial(hass: HomeAssistant, controlador: Controller) -> None:
    """Si Calorplan nunca ha tenido datos y existe `calorplan.json`, lo importa solo una vez."""
    if await controlador.store.async_hay_datos():
        return  # ya hay plan guardado: nunca se sobrescribe
    ruta = Path(hass.config.config_dir) / ajustes.FICHERO_IMPORTACION
    try:
        datos = await hass.async_add_executor_job(_leer, ruta)
        if datos is None:
            return
        plan = Plan.from_dict(datos)
    except (OSError, ValueError, ConfigError) as err:
        _LOGGER.warning("No se pudo importar %s: %s", ruta, err)
        _avisar(hass, ajustes.AUTOIMPORTAR_ERROR.format(fichero=ajustes.FICHERO_IMPORTACION, error=err))
        return
    await controlador.async_replace_plan(plan, ajustes.MOTIVO_HIST_AUTOIMPORTAR)
    _avisar(hass, ajustes.AUTOIMPORTAR_OK.format(
        fichero=ajustes.FICHERO_IMPORTACION, habitaciones=len(plan.rooms)))
