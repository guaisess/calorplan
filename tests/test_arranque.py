# Versión: 2026.11.12
"""Tests del reinicio: lo ya gestionado se respeta, no se enciende con datos ausentes."""
from __future__ import annotations

import asyncio
import copy
import json
from types import SimpleNamespace

import pytest

from calorplan_core import settings as aj
from calorplan_core.engine import Evaluator, Notifier, PlannedEvent, Runner
from calorplan_core.models import ConfigError, Plan
from fakes import (FakeActuator, FakeClock, FakeEvents, FakeNotify, FakeState,
                   RAIZ, instante)

DATOS = json.loads((RAIZ / "examples" / "config_ejemplo.json").read_text(encoding="utf-8"))
CLIMA = "climate.calefaccion_dormitorio"
EXT = ["sensor.temperatura_exterior", "sensor.temperatura_porche"]
INT = ["sensor.dormitorio_temperatura", "sensor.dormitorio_temperatura_2"]
FRIO = {INT[0]: "15", INT[1]: "15"}
SIN_DATOS = {INT[0]: "unknown", INT[1]: "unavailable"}


def montar(dia="2026-11-02", hora="06:30", catch_up="evaluate", politica="start_anyway", estados=None):
    datos = copy.deepcopy(DATOS)
    datos["global"].update({"shadow_mode": False, "catch_up": catch_up, "unavailable_policy": politica})
    plan = Plan.from_dict(datos)
    estado = FakeState({EXT[0]: "8", EXT[1]: "9", **FRIO, CLIMA: "off", **(estados or {}),
                        "sensor.despacho_temperatura": "18", "switch.calefaccion_despacho_enchufe": "off"})
    reloj = FakeClock(instante(dia, hora))
    envio, eventos = FakeNotify(), FakeEvents()
    act = FakeActuator(estado)
    runner = Runner(plan, estado, act, Notifier(plan, envio, reloj), reloj, eventos)
    return SimpleNamespace(plan=plan, estado=estado, act=act, envio=envio, eventos=eventos, reloj=reloj, runner=runner)


def catch_up(e):
    return asyncio.run(e.runner.catch_up())


def evento(e, tipo="start", sala="dormitorio", tramo="madrugada", dia="2026-11-02", hora="06:00"):
    return asyncio.run(e.runner.handle(PlannedEvent(instante(dia, hora), tipo, sala, tramo)))


def encendidos(e):
    return [c for c in e.act.llamadas if c[0] in ("heat",) or (c[0] == "switch" and c[2] is True)]


# --- El caso que ocurrió: reinicio con sensores sin datos y «encender igualmente» -----------------------
def test_tras_un_reinicio_con_sensores_sin_datos_no_se_enciende_aunque_la_politica_lo_permita():
    e = montar(estados=SIN_DATOS)  # política start_anyway, catch_up evaluate, sensores sin datos
    registros = [r for r in catch_up(e) if r.room_id == "dormitorio"]
    assert [(r.action, r.code) for r in registros] == [("skip", aj.COD_INTERIOR_NO_DISPONIBLE)]  # no es un «error»
    assert encendidos(e) == [] and e.envio.enviados == []  # ni enciende ni avisa
    assert "dormitorio" in e.runner.salas_pendientes(solo_sin_datos=True)


def test_cuando_vuelven_los_datos_se_reintenta_y_se_enciende_si_procede():
    e = montar(estados=SIN_DATOS)
    catch_up(e)
    # Los sensores siguen sin datos: se sigue esperando
    assert asyncio.run(e.runner.reevaluate("dormitorio", solo_sin_datos=True)) == []
    e.estado.estados.update(FRIO)  # los sensores informan: hace frío
    registros = asyncio.run(e.runner.reevaluate("dormitorio", solo_sin_datos=True))
    assert [r.action for r in registros] == ["on"] and encendidos(e)[0][0] == "heat"
    assert "dormitorio" not in e.runner.salas_pendientes(solo_sin_datos=True)


def test_cuando_vuelven_los_datos_y_no_hace_falta_no_se_enciende():
    e = montar(estados=SIN_DATOS)
    catch_up(e)
    e.estado.estados.update({INT[0]: "20", INT[1]: "20"})  # la habitación ya está caliente
    assert asyncio.run(e.runner.reevaluate("dormitorio", solo_sin_datos=True)) == []
    assert encendidos(e) == []


def test_en_un_evento_normal_la_politica_del_usuario_se_respeta():
    e = montar(estados=SIN_DATOS)  # start_anyway
    reg = evento(e)
    assert reg.action == "on"  # solo el arranque es conservador, no los inicios programados


def test_en_un_evento_normal_con_no_encender_sigue_siendo_un_error_con_aviso():
    e = montar(estados=SIN_DATOS, politica="do_not_start")
    reg = evento(e)
    assert reg.action == "error" and len(e.envio.enviados) == 1


def test_con_datos_presentes_el_catch_up_funciona_como_siempre():
    e = montar()
    assert [(r.room_id, r.action) for r in catch_up(e) if r.room_id == "dormitorio"] == [("dormitorio", "on")]


# --- Lo ya gestionado antes del reinicio se respeta ------------------------------------------------------------
def test_un_tramo_ya_gestionado_antes_del_reinicio_no_se_vuelve_a_evaluar():
    antes = montar(hora="06:00")
    evento(antes)  # a las 06:00 se encendió (hace frío)
    guardado = json.loads(json.dumps(antes.runner.estado_arranque()))  # se guarda y se recupera tal cual

    despues = montar(hora="06:30", estados={CLIMA: "off"})  # tras el reinicio el usuario lo había apagado
    despues.runner.cargar_estado(guardado)
    assert [r for r in catch_up(despues) if r.room_id == "dormitorio"] == []
    assert despues.act.llamadas == [] and despues.estado.estados[CLIMA] == "off"  # se mantiene tal cual


def test_lo_omitido_antes_del_reinicio_tampoco_se_reevalua():
    antes = montar(hora="06:00", estados={INT[0]: "20", INT[1]: "20"})  # caliente: se omite
    evento(antes)
    despues = montar(hora="06:30")  # tras reiniciar hace frío, pero el inicio ya se gestionó
    despues.runner.cargar_estado(antes.runner.estado_arranque())
    assert [r for r in catch_up(despues) if r.room_id == "dormitorio"] == []
    assert encendidos(despues) == []


def test_un_inicio_perdido_durante_la_caida_si_se_aplica():
    antes = montar(dia="2026-11-02", hora="06:00")
    evento(antes)  # gestionado el lunes
    despues = montar(dia="2026-11-03", hora="06:30")  # martes: HA estaba apagado a las 06:00
    despues.runner.cargar_estado(antes.runner.estado_arranque())
    assert [(r.room_id, r.action) for r in catch_up(despues) if r.room_id == "dormitorio"] == [("dormitorio", "on")]


def test_primer_arranque_sin_estado_guardado_no_toca_nada():
    e = montar()
    e.runner.cargar_estado(None)  # primera vez: lo que está activo se considera gestionado
    assert catch_up(e) == [] and e.act.llamadas == []


def test_ya_gestionado_compara_ocurrencias():
    e = montar(hora="06:00")
    evento(e)
    inicio = instante("2026-11-02", "06:00")
    assert e.runner.ya_gestionado("dormitorio", "madrugada", inicio)
    assert not e.runner.ya_gestionado("dormitorio", "madrugada", instante("2026-11-03", "06:00"))
    assert not e.runner.ya_gestionado("dormitorio", "tarde", inicio)
    assert not e.runner.ya_gestionado("fantasma", "x", inicio)


def test_el_estado_restaura_los_pendientes():
    e = montar(estados=SIN_DATOS)
    catch_up(e)
    guardado = json.loads(json.dumps(e.runner.estado_arranque()))
    assert guardado["dormitorio/madrugada"]["outcome"] == aj.RESULTADO_PENDIENTE_DATOS
    otro = montar(estados=SIN_DATOS)
    otro.runner.cargar_estado(guardado)
    assert "dormitorio" in otro.runner.salas_pendientes(solo_sin_datos=True)


def test_estado_guardado_de_tramos_que_ya_no_existen_no_da_problemas():
    e = montar()
    e.runner.cargar_estado({"fantasma/x": {"start": "2026-11-02T06:00:00+01:00", "outcome": "pending"},
                            "rota": "no es un diccionario"})
    assert asyncio.run(e.runner.reevaluate()) == [] and e.runner.salas_pendientes() == set()


@pytest.mark.parametrize("estados,cambios,esperado", [
    ({}, None, "on"),
    ({INT[0]: "20", INT[1]: "20"}, None, "pending"),
    (SIN_DATOS, None, "pending_data"),
    ({}, "ausencia", "skip"),
])
def test_resultados_anotados(estados, cambios, esperado):
    e = montar(estados=estados, politica="do_not_start")
    if cambios == "ausencia":
        e.plan.config.away_mode = True
    evento(e)
    assert e.runner.estado_arranque()["dormitorio/madrugada"]["outcome"] == esperado


def test_un_fallo_del_actuador_se_anota_como_error():
    e = montar()

    async def falla(*a):
        raise RuntimeError("sin conexión")
    e.act.climate_set_mode = falla
    evento(e)
    assert e.runner.estado_arranque()["dormitorio/madrugada"]["outcome"] == aj.RESULTADO_ERROR


def test_una_ejecucion_manual_fuera_de_horario_no_se_anota():
    e = montar(hora="12:00")
    asyncio.run(e.runner.handle(PlannedEvent(e.reloj.now(), "start", "dormitorio", "madrugada"), forzar=True))
    assert "dormitorio/madrugada" not in e.runner.estado_arranque()


def test_la_reevaluacion_de_arranque_sigue_esperando_si_los_datos_no_llegan():
    e = montar(estados=SIN_DATOS)  # start_anyway
    catch_up(e)
    for minuto in ("06:35", "06:40", "06:45"):
        e.reloj.fijar(instante("2026-11-02", minuto))
        assert asyncio.run(e.runner.reevaluate("dormitorio", solo_sin_datos=True)) == []
    assert encendidos(e) == []


def test_evaluador_acepta_una_politica_forzada():
    e = montar(estados=SIN_DATOS)
    sala = e.plan.room("dormitorio")
    ev = Evaluator(e.estado)
    assert ev.evaluate(sala, sala.slot("madrugada"), e.plan.config).start  # start_anyway
    d = ev.evaluate(sala, sala.slot("madrugada"), e.plan.config, "do_not_start")
    assert not d.start and d.code == aj.COD_INTERIOR_NO_DISPONIBLE


# --- Configuración ----------------------------------------------------------------------------------------------------
def test_espera_de_arranque_por_defecto_y_validacion():
    assert Plan.from_dict(copy.deepcopy(DATOS)).config.startup_delay_seconds == 120
    datos = copy.deepcopy(DATOS)
    datos["global"]["startup_delay_seconds"] = 0
    plan = Plan.from_dict(datos)
    assert plan.config.startup_delay_seconds == 0
    assert Plan.from_dict(plan.to_dict()).config.startup_delay_seconds == 0
    for malo in (-1, 3601, "120", 1.5, True, None):
        datos["global"]["startup_delay_seconds"] = malo
        with pytest.raises(ConfigError, match="startup_delay_seconds"):
            Plan.from_dict(datos)
