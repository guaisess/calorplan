# Versión: 2026.11.2
"""Tests del notificador."""
from __future__ import annotations

import asyncio
import copy
import json

import pytest

from calorplan_core import settings as aj
from calorplan_core.engine import Notifier, Record
from calorplan_core.models import NotifyConfig, Plan
from fakes import FakeClock, FakeNotify, RAIZ, instante

DATOS = json.loads((RAIZ / "examples" / "config_ejemplo.json").read_text(encoding="utf-8"))
TELEGRAM = "notify.telegram_ejemplo"
MOVIL = "notify.mobile_app_ejemplo"


def montar():
    plan = Plan.from_dict(copy.deepcopy(DATOS))
    envio = FakeNotify()
    notificador = Notifier(plan, envio, FakeClock(instante("2026-11-02", "06:00")))
    sala = plan.room("dormitorio")
    return plan, sala, sala.slot("madrugada"), notificador, envio


def registro(accion, **extra):
    base = dict(when=instante("2026-11-02", "06:00"), room_id="dormitorio",
                room_name="Dormitorio", slot_id="madrugada", slot_name="Madrugada",
                kind="start", action=accion, code="ok", reason="motivo",
                setpoint=20.0, outdoor=8.5, indoor=15.0)
    base.update(extra)
    return Record(**base)


def enviar(notificador, sala, tramo, reg):
    return asyncio.run(notificador.notificar(sala, tramo, reg))


def test_herencia_tramo_habitacion_global():
    plan, sala, tramo, notif, _ = montar()
    assert notif.efectivo(sala, tramo) is plan.config.default_notify
    sala.notify = NotifyConfig("on", ["movil"])
    assert notif.efectivo(sala, tramo) is sala.notify
    tramo.notify = NotifyConfig("off", ["telegram"])
    assert notif.efectivo(sala, tramo) is tramo.notify


@pytest.mark.parametrize("modo,enciende,apaga", [
    ("none", False, False), ("on", True, False), ("off", False, True), ("both", True, True)])
def test_modos_de_aviso(modo, enciende, apaga):
    _, sala, tramo, notif, envio = montar()
    tramo.notify = NotifyConfig(modo, ["telegram"])
    assert enviar(notif, sala, tramo, registro("on")) == (1 if enciende else 0)
    assert enviar(notif, sala, tramo, registro("off")) == (1 if apaga else 0)
    assert len(envio.enviados) == int(enciende) + int(apaga)


def test_omision_solo_avisa_si_se_pide():
    _, sala, tramo, notif, envio = montar()
    assert enviar(notif, sala, tramo, registro("skip")) == 0
    tramo.notify_on_skip = True
    assert enviar(notif, sala, tramo, registro("skip")) == 1


def test_error_se_avisa_siempre_aunque_el_modo_sea_ninguno():
    _, sala, tramo, notif, envio = montar()
    tramo.notify = NotifyConfig("none", [])  # sin canales propios: usa los globales
    assert enviar(notif, sala, tramo, registro("error", reason="fallo")) == 1
    assert envio.enviados[0][0] == TELEGRAM


def test_varios_canales_y_fallo_de_uno():
    _, sala, tramo, notif, envio = montar()
    tramo.notify = NotifyConfig("both", ["telegram", "movil"])
    envio.fallar_en.add(TELEGRAM)
    assert enviar(notif, sala, tramo, registro("on")) == 1  # el móvil sí recibe el aviso
    assert [e[0] for e in envio.enviados] == [MOVIL]


def test_plantilla_por_defecto_y_variables():
    _, sala, tramo, notif, envio = montar()
    tramo.notify = NotifyConfig("on", ["telegram"])
    enviar(notif, sala, tramo, registro("on"))
    servicio, titulo, mensaje = envio.enviados[0]
    assert titulo == aj.TITULO_AVISO
    assert "Dormitorio · Madrugada" in mensaje
    assert "Exterior: 8.5 °C" in mensaje and "Estancia: 15 °C" in mensaje and "Objetivo: 20 °C" in mensaje


def test_plantilla_global_y_de_canal_con_variable_ausente():
    plan, sala, tramo, notif, envio = montar()
    plan.config.templates = {"on": "{room}/{inexistente}/{time}"}
    plan.config.canal("movil").templates = {"on": "móvil {slot}"}
    tramo.notify = NotifyConfig("on", ["telegram", "movil"])
    enviar(notif, sala, tramo, registro("on"))
    assert envio.enviados[0][2] == "Dormitorio//06:00"  # variable ausente → vacía
    assert envio.enviados[1][2] == "móvil Madrugada"


def test_valores_ausentes_quedan_vacios():
    _, sala, tramo, notif, envio = montar()
    tramo.notify = NotifyConfig("on", ["telegram"])
    enviar(notif, sala, tramo, registro("on", outdoor=None, indoor=None, setpoint=None))
    assert "Exterior:  °C" in envio.enviados[0][2]


def test_prueba_de_canal():
    _, _, _, notif, envio = montar()
    assert asyncio.run(notif.probar("movil")) is True
    assert envio.enviados[0][0] == MOVIL and envio.enviados[0][1] == aj.TITULO_PRUEBA
    assert asyncio.run(notif.probar("no_existe")) is False
