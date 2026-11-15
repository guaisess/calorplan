# Versión: 2026.11.22
"""Tests del límite de lo encendido a mano (ManualGuard y su integración en el motor)."""
from __future__ import annotations

import asyncio
import copy
from datetime import timedelta

import pytest

from calorplan_core import settings as aj
from calorplan_core.models import ConfigError, Plan
from test_runner import CLIMA, DATOS, TOALLERO, montar
from fakes import instante


def con_limite(minutos=180, sala="dormitorio"):
    datos = copy.deepcopy(DATOS)
    for r in datos["rooms"]:
        if r["id"] == sala:
            r["manual_max_minutes"] = minutos
    return datos


# --- Modelo -----------------------------------------------------------------------------------------
def test_el_limite_manual_se_valida_y_se_serializa():
    plan = Plan.from_dict(con_limite(90))
    assert plan.room("dormitorio").manual_max_minutes == 90
    assert Plan.from_dict(plan.to_dict()).room("dormitorio").manual_max_minutes == 90
    assert Plan.from_dict(DATOS).room("dormitorio").manual_max_minutes is None
    for malo in (0, -5, 1441, "3", 2.5, True):
        with pytest.raises(ConfigError):
            Plan.from_dict(con_limite(malo))


# --- Vigilante ----------------------------------------------------------------------------------------
def test_encendido_manual_fija_el_limite_y_apagar_lo_borra():
    e = montar(datos=con_limite(180), hora="09:00", estados={CLIMA: "heat"})
    r = e.runner
    r.cambio_estado("dormitorio")
    assert r.manual.limite("dormitorio") == instante("2026-11-02", "12:00")
    e.estado.estados[CLIMA] = "off"
    r.cambio_estado("dormitorio")
    assert r.manual.limite("dormitorio") is None


def test_un_encendido_de_calorplan_no_es_manual():
    e = montar(datos=con_limite(180), hora="06:00")
    asyncio.run(e.runner.handle(__import__("test_runner").ev("start")))
    e.runner.cambio_estado("dormitorio")
    assert e.runner.manual.limite("dormitorio") is None


def test_sin_limite_configurado_no_se_vigila():
    e = montar(hora="09:00", estados={CLIMA: "heat"})
    e.runner.cambio_estado("dormitorio")
    assert e.runner.manual.limite("dormitorio") is None


def test_vence_apaga_verifica_y_avisa():
    e = montar(datos=con_limite(180), hora="09:00", estados={CLIMA: "heat"})
    e.runner.cambio_estado("dormitorio")
    e.reloj.fijar(instante("2026-11-02", "12:01"))
    regs = asyncio.run(e.runner.vigilar_manual())
    assert [r.action for r in regs] == ["off"] and e.estado.estados[CLIMA] == "off"
    assert regs[0].slot_name == aj.TRAMO_MANUAL_NOMBRE and e.runner.manual.limite("dormitorio") is None
    assert e.eventos.registros and e.eventos.registros[-1]["code"] == aj.COD_MANUAL_APAGADO
    assert len(e.envio.enviados) == 1 and "encendida a mano" in e.envio.enviados[0][2]


def test_antes_del_limite_no_se_apaga():
    e = montar(datos=con_limite(180), hora="09:00", estados={CLIMA: "heat"})
    e.runner.cambio_estado("dormitorio")
    assert asyncio.run(e.runner.vigilar_manual()) == [] and e.estado.estados[CLIMA] == "heat"


def test_habitacion_deshabilitada_no_tiene_limite():
    e = montar(datos=con_limite(180), hora="09:00", estados={CLIMA: "heat"})
    e.plan.room("dormitorio").enabled = False
    e.runner.cambio_estado("dormitorio")
    assert e.runner.manual.limite("dormitorio") is None


def test_estado_persistente_y_adopcion_tras_reinicio():
    e = montar(datos=con_limite(60), hora="09:00", estados={CLIMA: "heat"})
    e.runner.adoptar_encendidos()  # encendido de origen desconocido: cuenta desde ahora
    guardado = e.runner.estado_arranque()
    assert aj.CLAVE_MANUAL in guardado
    n = montar(datos=con_limite(60), hora="09:30", estados={CLIMA: "heat"})
    n.runner.cargar_estado(guardado)
    assert n.runner.manual.limite("dormitorio") == instante("2026-11-02", "10:00")  # se conserva el inicio


def test_adoptar_no_toca_lo_que_encendio_un_tramo_de_calorplan():
    e = montar(datos=con_limite(60), hora="06:00")
    asyncio.run(e.runner.handle(__import__("test_runner").ev("start")))
    e.runner.adoptar_encendidos()
    assert e.runner.manual.limite("dormitorio") is None
