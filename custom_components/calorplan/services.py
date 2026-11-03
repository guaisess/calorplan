# Versión: 2026.11.2
"""Servicios de Calorplan: importar, ejecutar tramo, ausencia, prueba y recarga."""
from __future__ import annotations

import json
from pathlib import Path

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .core import settings as ajustes
from .core.models import ConfigError, Plan
from .ha.controller import Controller

SERVICIOS = (ajustes.SERVICIO_IMPORTAR, ajustes.SERVICIO_EJECUTAR, ajustes.SERVICIO_AUSENCIA,
             ajustes.SERVICIO_PRUEBA, ajustes.SERVICIO_RECARGAR)

ESQUEMA_IMPORTAR = vol.All(
    vol.Schema({vol.Optional(ajustes.CAMPO_RUTA): cv.string,
                vol.Optional(ajustes.CAMPO_CONFIG): dict}),
    cv.has_at_least_one_key(ajustes.CAMPO_RUTA, ajustes.CAMPO_CONFIG))
ESQUEMA_EJECUTAR = vol.Schema({
    vol.Required(ajustes.CAMPO_HABITACION): cv.string,
    vol.Required(ajustes.CAMPO_TRAMO): cv.string,
    vol.Optional(ajustes.CAMPO_FORZAR, default=False): cv.boolean})
ESQUEMA_AUSENCIA = vol.Schema({vol.Required(ajustes.CAMPO_AUSENTE): cv.boolean})
ESQUEMA_PRUEBA = vol.Schema({vol.Required(ajustes.CAMPO_CANAL): cv.string})
ESQUEMA_RECARGAR = vol.Schema({})


def _entrada_y_controlador(hass: HomeAssistant) -> tuple[str, Controller]:
    """Devuelve (entry_id, controlador) de la única instancia activa."""
    instancias = hass.data.get(ajustes.DOMAIN) or {}
    if not instancias:
        raise ServiceValidationError("Calorplan no está configurado")
    return next(iter(instancias.items()))


def _recargar_entrada(hass: HomeAssistant, entry_id: str) -> None:
    """Recarga la entrada (recrea las entidades) sin bloquear la llamada."""
    hass.async_create_task(hass.config_entries.async_reload(entry_id))


def async_registrar(hass: HomeAssistant) -> None:
    """Registra los servicios (una sola vez)."""
    if hass.services.has_service(ajustes.DOMAIN, ajustes.SERVICIO_IMPORTAR):
        return

    async def importar(llamada: ServiceCall) -> None:
        entry_id, controlador = _entrada_y_controlador(hass)
        datos = llamada.data.get(ajustes.CAMPO_CONFIG)
        ruta = llamada.data.get(ajustes.CAMPO_RUTA)
        if datos is None:
            if not hass.config.is_allowed_path(ruta):
                raise ServiceValidationError(f"Ruta no permitida: {ruta}")
            try:
                texto = await hass.async_add_executor_job(Path(ruta).read_text, "utf-8")
                datos = json.loads(texto)
            except (OSError, ValueError) as err:
                raise ServiceValidationError(f"No se pudo leer {ruta}: {err}") from err
        try:
            plan = Plan.from_dict(datos)
        except ConfigError as err:
            raise ServiceValidationError(f"Configuración inválida: {err}") from err
        await controlador.async_replace_plan(plan)
        _recargar_entrada(hass, entry_id)

    async def ejecutar(llamada: ServiceCall) -> None:
        _, controlador = _entrada_y_controlador(hass)
        sala_id = llamada.data[ajustes.CAMPO_HABITACION]
        tramo_id = llamada.data[ajustes.CAMPO_TRAMO]
        sala = controlador.plan.room(sala_id)
        if sala is None or sala.slot(tramo_id) is None:
            raise ServiceValidationError(f"No existe el tramo {sala_id}/{tramo_id}")
        await controlador.async_run_slot(sala_id, tramo_id, llamada.data[ajustes.CAMPO_FORZAR])

    async def ausencia(llamada: ServiceCall) -> None:
        _, controlador = _entrada_y_controlador(hass)
        await controlador.async_set_away(llamada.data[ajustes.CAMPO_AUSENTE])

    async def prueba(llamada: ServiceCall) -> None:
        _, controlador = _entrada_y_controlador(hass)
        canal = llamada.data[ajustes.CAMPO_CANAL]
        if not await controlador.async_test_notification(canal):
            raise HomeAssistantError(f"No se pudo enviar el aviso de prueba al canal '{canal}'")

    async def recargar(llamada: ServiceCall) -> None:
        entry_id, _ = _entrada_y_controlador(hass)
        _recargar_entrada(hass, entry_id)

    hass.services.async_register(ajustes.DOMAIN, ajustes.SERVICIO_IMPORTAR, importar,
                                 schema=ESQUEMA_IMPORTAR)
    hass.services.async_register(ajustes.DOMAIN, ajustes.SERVICIO_EJECUTAR, ejecutar,
                                 schema=ESQUEMA_EJECUTAR)
    hass.services.async_register(ajustes.DOMAIN, ajustes.SERVICIO_AUSENCIA, ausencia,
                                 schema=ESQUEMA_AUSENCIA)
    hass.services.async_register(ajustes.DOMAIN, ajustes.SERVICIO_PRUEBA, prueba,
                                 schema=ESQUEMA_PRUEBA)
    hass.services.async_register(ajustes.DOMAIN, ajustes.SERVICIO_RECARGAR, recargar,
                                 schema=ESQUEMA_RECARGAR)


def async_quitar(hass: HomeAssistant) -> None:
    """Elimina los servicios al descargar la última instancia."""
    for servicio in SERVICIOS:
        hass.services.async_remove(ajustes.DOMAIN, servicio)
