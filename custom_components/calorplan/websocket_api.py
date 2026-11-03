# Versión: 2026.11.6
"""API WebSocket del panel: lectura (resumen) y edición de tramos (solo administradores)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .core import settings as ajustes
from .core.models import ConfigError
from .ha.controller import Controller

ERR_NO_CARGADO = "not_loaded"
ERR_INVALIDO = "invalid_config"
MSG_NO_CARGADO = "Calorplan no está configurado"


def _instancia(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
               msg: dict[str, Any]) -> tuple[str, Controller] | None:
    """Devuelve (entry_id, controlador) o responde con error si no hay instancia."""
    instancias = hass.data.get(ajustes.DOMAIN) or {}
    if not instancias:
        connection.send_error(msg["id"], ERR_NO_CARGADO, MSG_NO_CARGADO)
        return None
    return next(iter(instancias.items()))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): ajustes.WS_OVERVIEW})
@callback
def ws_overview(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                msg: dict[str, Any]) -> None:
    """Resumen completo: plan visible, línea de tiempo y simulación."""
    if (instancia := _instancia(hass, connection, msg)) is not None:
        connection.send_result(msg["id"], instancia[1].overview())


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): ajustes.WS_VALIDAR_TRAMO,
    vol.Required("room_id"): str,
    vol.Required("slot"): dict,
    vol.Optional("slot_id"): vol.Any(str, None),
})
@callback
def ws_validate_slot(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                     msg: dict[str, Any]) -> None:
    """Valida un tramo sin guardarlo: {ok, error, conflicts}."""
    if (instancia := _instancia(hass, connection, msg)) is not None:
        connection.send_result(msg["id"], instancia[1].validar_tramo(
            msg["room_id"], msg["slot"], msg.get("slot_id")))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): ajustes.WS_GUARDAR_TRAMO,
    vol.Required("room_id"): str,
    vol.Required("slot"): dict,
    vol.Optional("slot_id"): vol.Any(str, None),
})
@websocket_api.async_response
async def ws_save_slot(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                       msg: dict[str, Any]) -> None:
    """Crea o modifica un tramo (guarda antes una copia en el historial)."""
    if (instancia := _instancia(hass, connection, msg)) is None:
        return
    controlador = instancia[1]
    try:
        slot_id = await controlador.async_guardar_tramo(
            msg["room_id"], msg["slot"], msg.get("slot_id"))
    except ConfigError as err:
        connection.send_error(msg["id"], ERR_INVALIDO, str(err))
        return
    connection.send_result(msg["id"], {"slot_id": slot_id, "overview": controlador.overview()})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): ajustes.WS_BORRAR_TRAMO,
    vol.Required("room_id"): str,
    vol.Required("slot_id"): str,
})
@websocket_api.async_response
async def ws_delete_slot(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                         msg: dict[str, Any]) -> None:
    """Elimina un tramo (guarda antes una copia en el historial)."""
    if (instancia := _instancia(hass, connection, msg)) is None:
        return
    try:
        await instancia[1].async_borrar_tramo(msg["room_id"], msg["slot_id"])
    except ConfigError as err:
        connection.send_error(msg["id"], ERR_INVALIDO, str(err))
        return
    connection.send_result(msg["id"], {"overview": instancia[1].overview()})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): ajustes.WS_HISTORIAL})
@callback
def ws_history(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
               msg: dict[str, Any]) -> None:
    """Lista las versiones guardadas del plan."""
    if (instancia := _instancia(hass, connection, msg)) is not None:
        connection.send_result(msg["id"], instancia[1].historial())


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): ajustes.WS_RESTAURAR,
    vol.Required("index"): vol.All(int, vol.Range(min=0)),
})
@websocket_api.async_response
async def ws_restore(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                     msg: dict[str, Any]) -> None:
    """Restaura una versión anterior (antes guarda copia de la actual)."""
    if (instancia := _instancia(hass, connection, msg)) is None:
        return
    entry_id, controlador = instancia
    antes = [r.id for r in controlador.plan.rooms]
    try:
        await controlador.async_restaurar(msg["index"])
    except ConfigError as err:
        connection.send_error(msg["id"], ERR_INVALIDO, str(err))
        return
    if [r.id for r in controlador.plan.rooms] != antes:
        # Cambió el conjunto de habitaciones: se recrean las entidades
        hass.async_create_task(hass.config_entries.async_reload(entry_id))
    connection.send_result(msg["id"], {"overview": controlador.overview()})


def _advertencias(hass: HomeAssistant, datos: dict[str, Any]) -> list[str]:
    """Avisos no bloqueantes: canales o sensores que no existen en Home Assistant."""
    avisos = []
    for canal in datos.get("channels", []):
        servicio = str(canal.get("service", ""))
        dominio, _, nombre = servicio.partition(".")
        if not hass.services.has_service(dominio, nombre) and hass.states.get(servicio) is None:
            avisos.append(ajustes.ADVERTENCIA_CANAL_INEXISTENTE.format(servicio=servicio))
    for sensor in datos.get("outdoor_sensors", []):
        if hass.states.get(sensor) is None:
            avisos.append(ajustes.ADVERTENCIA_SENSOR_INEXISTENTE.format(sensor=sensor))
    if not datos.get("shadow_mode"):
        avisos.append(ajustes.ADVERTENCIA_SOMBRA_APAGADO)
    return avisos


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): ajustes.WS_GET_GLOBAL})
@callback
def ws_get_global(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                  msg: dict[str, Any]) -> None:
    """Devuelve los ajustes globales completos para el editor."""
    if (instancia := _instancia(hass, connection, msg)) is not None:
        connection.send_result(msg["id"], {"global": instancia[1].global_config()})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): ajustes.WS_VALIDAR_GLOBAL,
    vol.Required("global"): dict,
})
@callback
def ws_validate_global(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                       msg: dict[str, Any]) -> None:
    """Valida los ajustes globales: {ok, error, warnings}."""
    if (instancia := _instancia(hass, connection, msg)) is None:
        return
    resultado = instancia[1].validar_global(msg["global"])
    resultado["warnings"] = _advertencias(hass, msg["global"]) if resultado["ok"] else []
    connection.send_result(msg["id"], resultado)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): ajustes.WS_GUARDAR_GLOBAL,
    vol.Required("global"): dict,
})
@websocket_api.async_response
async def ws_save_global(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                         msg: dict[str, Any]) -> None:
    """Guarda los ajustes globales (copia previa en el historial)."""
    if (instancia := _instancia(hass, connection, msg)) is None:
        return
    controlador = instancia[1]
    try:
        await controlador.async_guardar_global(msg["global"])
    except ConfigError as err:
        connection.send_error(msg["id"], ERR_INVALIDO, str(err))
        return
    connection.send_result(msg["id"], {
        "global": controlador.global_config(), "overview": controlador.overview()})


def _advertencias_habitacion(hass: HomeAssistant, datos: dict[str, Any]) -> list[str]:
    """Avisos no bloqueantes: actuador o sensores inexistentes o que no son de temperatura."""
    avisos = []
    entidad = str((datos.get("actuator") or {}).get("entity_id", ""))
    if entidad and hass.states.get(entidad) is None:
        avisos.append(ajustes.ADVERTENCIA_ACTUADOR_INEXISTENTE.format(entidad=entidad))
    for sensor in datos.get("sensors", []):
        estado = hass.states.get(sensor)
        if estado is None:
            avisos.append(ajustes.ADVERTENCIA_SENSOR_INEXISTENTE.format(sensor=sensor))
        elif estado.attributes.get("device_class") != ajustes.DEVICE_CLASS_TEMPERATURA:
            avisos.append(ajustes.ADVERTENCIA_SENSOR_NO_TEMPERATURA.format(
                sensor=sensor, clase=estado.attributes.get("device_class")))
    return avisos


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): ajustes.WS_VALIDAR_HABITACION,
    vol.Required("room"): dict,
    vol.Optional("room_id"): vol.Any(str, None),
})
@callback
def ws_validate_room(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                     msg: dict[str, Any]) -> None:
    """Valida una habitación: {ok, error, warnings}."""
    if (instancia := _instancia(hass, connection, msg)) is None:
        return
    resultado = instancia[1].validar_habitacion(msg["room"], msg.get("room_id"))
    resultado["warnings"] = _advertencias_habitacion(hass, msg["room"]) if resultado["ok"] else []
    connection.send_result(msg["id"], resultado)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): ajustes.WS_GUARDAR_HABITACION,
    vol.Required("room"): dict,
    vol.Optional("room_id"): vol.Any(str, None),
})
@websocket_api.async_response
async def ws_save_room(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                       msg: dict[str, Any]) -> None:
    """Crea o modifica una habitación; recrea las entidades si cambian ids o nombres."""
    if (instancia := _instancia(hass, connection, msg)) is None:
        return
    entry_id, controlador = instancia
    antes = controlador.firma_habitaciones()
    try:
        room_id = await controlador.async_guardar_habitacion(msg["room"], msg.get("room_id"))
    except ConfigError as err:
        connection.send_error(msg["id"], ERR_INVALIDO, str(err))
        return
    if controlador.firma_habitaciones() != antes:
        hass.async_create_task(hass.config_entries.async_reload(entry_id))
    connection.send_result(msg["id"], {"room_id": room_id, "overview": controlador.overview()})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): ajustes.WS_BORRAR_HABITACION,
    vol.Required("room_id"): str,
})
@websocket_api.async_response
async def ws_delete_room(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                         msg: dict[str, Any]) -> None:
    """Elimina una habitación y recrea las entidades."""
    if (instancia := _instancia(hass, connection, msg)) is None:
        return
    entry_id, controlador = instancia
    try:
        await controlador.async_borrar_habitacion(msg["room_id"])
    except ConfigError as err:
        connection.send_error(msg["id"], ERR_INVALIDO, str(err))
        return
    hass.async_create_task(hass.config_entries.async_reload(entry_id))
    connection.send_result(msg["id"], {"overview": controlador.overview()})


def async_registrar(hass: HomeAssistant) -> None:
    """Registra los comandos WebSocket."""
    for comando in (ws_overview, ws_validate_slot, ws_save_slot, ws_delete_slot,
                    ws_history, ws_restore, ws_get_global, ws_validate_global, ws_save_global,
                    ws_validate_room, ws_save_room, ws_delete_room):
        websocket_api.async_register_command(hass, comando)
