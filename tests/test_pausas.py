# Versión: 2026.11.8
"""Tests de las pausas (vacaciones, visitas...): modelo, motor, resumen y editor."""
from __future__ import annotations

import asyncio
import copy
import json
from datetime import date

import pytest

from calorplan_core import settings as aj
from calorplan_core.engine import Notifier, PlannedEvent, Runner
from calorplan_core.engine.editor import PlanEditor
from calorplan_core.engine.overview import OverviewBuilder
from calorplan_core.models import ConfigError, Pause, Plan, pausa_activa
from fakes import (FakeActuator, FakeClock, FakeEvents, FakeNotify, FakeState,
                   RAIZ, instante)

DATOS = json.loads((RAIZ / "examples" / "config_ejemplo.json").read_text(encoding="utf-8"))
CLIMA = "climate.calefaccion_dormitorio"
ESTADOS = {"sensor.temperatura_exterior": "8", "sensor.temperatura_porche": "9",
           "sensor.dormitorio_temperatura": "15", "sensor.dormitorio_temperatura_2": "17",
           CLIMA: "off", "switch.calefaccion_despacho_enchufe": "off", "sensor.despacho_temperatura": "18"}


def p(**extra):
    base = {"id": "vac", "reason": "Vacaciones", "from": "2026-11-10", "until": "2026-11-15", "enabled": True}
    base.update(extra)
    return base


def plan_con(pausas_casa=None, pausas_dormitorio=None, **g):
    d = copy.deepcopy(DATOS)
    d["global"]["shadow_mode"] = False
    d["global"].update(g)
    if pausas_casa is not None:
        d["global"]["pauses"] = pausas_casa
    if pausas_dormitorio is not None:
        d["rooms"][0]["pauses"] = pausas_dormitorio
    return Plan.from_dict(d)


# --- Modelo ------------------------------------------------------------------------------------------
def test_pausa_con_fechas_inclusivas():
    pausa = Pause.from_dict(p())
    assert not pausa.activa_en(date(2026, 11, 9))
    assert pausa.activa_en(date(2026, 11, 10)) and pausa.activa_en(date(2026, 11, 15))
    assert not pausa.activa_en(date(2026, 11, 16))


def test_pausa_sin_fecha_de_fin_dura_hasta_que_se_quite():
    pausa = Pause.from_dict(p(until=None))
    assert pausa.end is None and pausa.activa_en(date(2030, 1, 1)) and not pausa.activa_en(date(2026, 11, 9))
    with pytest.raises(ConfigError, match="AAAA-MM-DD"):
        Pause.from_dict(p(until=""))  # vacío ≠ sin fin: evita pausas indefinidas por descuido


def test_pausa_deshabilitada_no_esta_activa():
    assert not Pause.from_dict(p(enabled=False)).activa_en(date(2026, 11, 12))


@pytest.mark.parametrize("hoy,estado", [
    ("2026-11-09", "upcoming"), ("2026-11-10", "active"), ("2026-11-15", "active"), ("2026-11-16", "expired")])
def test_estado_de_la_pausa(hoy, estado):
    y, m, d = map(int, hoy.split("-"))
    assert Pause.from_dict(p()).estado(date(y, m, d)) == estado
    assert Pause.from_dict(p(enabled=False)).estado(date(y, m, d)) == "disabled"


@pytest.mark.parametrize("cambios,fragmento", [
    ({"from": "10/11/2026"}, "AAAA-MM-DD"), ({"from": None}, "AAAA-MM-DD"), ({"until": "mañana"}, "AAAA-MM-DD"),
    ({"until": "2026-11-09"}, "anterior"), ({"id": ""}, "necesita 'id'"),
])
def test_pausa_invalida(cambios, fragmento):
    with pytest.raises(ConfigError, match=fragmento):
        Pause.from_dict(p(**cambios))


def test_ida_y_vuelta_y_ids_repetidos():
    plan = plan_con([p(), p(id="otra", until=None)], [p(id="x")])
    assert Plan.from_dict(plan.to_dict()).to_dict() == plan.to_dict()
    with pytest.raises(ConfigError, match="repetidos"):
        plan_con([p(), p()])
    with pytest.raises(ConfigError, match="lista"):
        plan_con("nada")


def test_pausa_activa_devuelve_la_primera_vigente():
    pausas = [Pause.from_dict(p(id="a", until="2026-11-11")), Pause.from_dict(p(id="b"))]
    assert pausa_activa(pausas, date(2026, 11, 10)).id == "a"
    assert pausa_activa(pausas, date(2026, 11, 14)).id == "b"
    assert pausa_activa(pausas, date(2026, 12, 1)) is None


# --- Motor -----------------------------------------------------------------------------------------------
def montar(plan, dia="2026-11-12", hora="06:00"):
    estado = FakeState(dict(ESTADOS))
    reloj = FakeClock(instante(dia, hora))
    envio, eventos = FakeNotify(), FakeEvents()
    act = FakeActuator(estado)
    runner = Runner(plan, estado, act, Notifier(plan, envio, reloj), reloj, eventos)
    return runner, estado, act, envio, eventos, reloj


def inicio(runner, sala="dormitorio", tramo="madrugada", **kw):
    return asyncio.run(runner.handle(PlannedEvent(instante("2026-11-12", "06:00"), "start", sala, tramo), **kw))


def test_pausa_de_la_habitacion_omite_el_encendido():
    runner, estado, act, envio, ev, _ = montar(plan_con(pausas_dormitorio=[p()]))
    reg = inicio(runner)
    assert (reg.action, reg.code) == ("skip", aj.COD_PAUSA)
    assert "Vacaciones" in reg.reason and "2026-11-10" in reg.reason and "habitación" in reg.reason
    assert act.llamadas == [] and envio.enviados == []


def test_pausa_global_afecta_a_todas_las_habitaciones():
    runner, *_ = montar(plan_con(pausas_casa=[p(reason="Viaje")]))
    r1 = inicio(runner)
    r2 = inicio(runner, "despacho", "mediodia")
    assert r1.code == r2.code == aj.COD_PAUSA and "toda la casa" in r1.reason


def test_la_pausa_de_otra_habitacion_no_afecta():
    runner, *_ = montar(plan_con(pausas_dormitorio=[p()]))
    assert inicio(runner, "despacho", "mediodia").action == "on"


def test_fuera_de_fechas_enciende_con_normalidad():
    for dia in ("2026-11-09", "2026-11-16"):
        runner, _, act, *_ = montar(plan_con(pausas_dormitorio=[p()]), dia=dia)
        assert inicio(runner).action == "on", dia
        assert act.llamadas[0][0] == "heat"


def test_pausa_sin_fin_y_deshabilitada():
    runner, *_ = montar(plan_con(pausas_dormitorio=[p(until=None)]), dia="2027-05-01")
    assert inicio(runner).code == aj.COD_PAUSA
    runner, *_ = montar(plan_con(pausas_dormitorio=[p(until=None, enabled=False)]))
    assert inicio(runner).action == "on"


def test_el_apagado_sigue_funcionando_durante_la_pausa():
    runner, estado, act, envio, *_ = montar(plan_con(pausas_casa=[p()]), hora="07:00")
    estado.estados[CLIMA] = "heat"
    reg = asyncio.run(runner.handle(PlannedEvent(instante("2026-11-12", "07:00"), "end", "dormitorio", "madrugada")))
    assert reg.action == "off" and estado.estados[CLIMA] == "off"


def test_ejecucion_forzada_ignora_la_pausa():
    runner, _, act, *_ = montar(plan_con(pausas_casa=[p()]))
    assert inicio(runner).code == aj.COD_PAUSA  # sin forzar, se omite
    reg = inicio(runner, forzar=True)
    assert reg.action == "on" and act.llamadas[0][0] == "heat"


def test_la_omision_por_pausa_nunca_avisa_aunque_se_pida():
    plan = plan_con(pausas_dormitorio=[p()])
    plan.room("dormitorio").slot("madrugada").notify_on_skip = True
    runner, _, _, envio, *_ = montar(plan)
    inicio(runner)
    assert envio.enviados == []


def test_omision_por_condicion_sigue_avisando_si_se_pide():
    plan = plan_con()
    plan.room("dormitorio").slot("madrugada").notify_on_skip = True
    runner, estado, _, envio, *_ = montar(plan)
    estado.estados["sensor.temperatura_exterior"] = "30"
    estado.estados["sensor.temperatura_porche"] = "30"
    assert inicio(runner).code == aj.COD_EXTERIOR_ALTO and len(envio.enviados) == 1


def test_modo_sombra_registra_la_pausa_como_simulacion():
    plan = plan_con(pausas_casa=[p()])
    plan.config.shadow_mode = True
    runner, _, act, *_ = montar(plan)
    reg = inicio(runner)
    assert reg.simulated and reg.code == aj.COD_SIMULACION and "Pausa" in reg.reason
    assert act.llamadas == []


def test_catch_up_respeta_la_pausa():
    plan = plan_con(pausas_dormitorio=[p()], catch_up="evaluate")
    runner, _, act, *_ = montar(plan, hora="06:30")
    registros = asyncio.run(runner.catch_up())
    assert any(r.code == aj.COD_PAUSA for r in registros)
    assert not any(c[0] == "heat" for c in act.llamadas)


# --- Resumen ---------------------------------------------------------------------------------------------
def resumen(plan, dia="2026-11-12"):
    return OverviewBuilder(plan, FakeState(dict(ESTADOS))).build(instante(dia, "06:30"), {})


def test_resumen_incluye_pausas_estado_y_quien_pausa():
    r = resumen(plan_con(pausas_casa=[p(id="g", reason="Viaje", until=None)], pausas_dormitorio=[p(id="d")]))
    assert r["today"] == "2026-11-12"
    assert r["global_pauses"][0]["status"] == "active" and r["global_pauses"][0]["until"] is None
    sala = r["rooms"][0]
    assert sala["pauses"][0]["id"] == "d" and sala["pauses"][0]["status"] == "active"
    assert sala["paused_by"] == {"scope": "room", "id": "d", "reason": "Vacaciones", "until": "2026-11-15"}
    assert r["rooms"][1]["paused_by"]["scope"] == "global"  # despacho: la pausa global
    assert sala["simulation"]["code"] == "paused" and sala["simulation"]["would_start"] is False


def test_resumen_sin_pausas():
    r = resumen(plan_con())
    assert r["global_pauses"] == [] and r["rooms"][0]["paused_by"] is None


def test_resumen_pausa_proxima_y_caducada_no_bloquean():
    r = resumen(plan_con(pausas_dormitorio=[p(id="f", **{"from": "2026-12-01", "until": "2026-12-05"}),
                                            p(id="c", **{"from": "2026-10-01", "until": "2026-10-05"})]))
    estados = {x["id"]: x["status"] for x in r["rooms"][0]["pauses"]}
    assert estados == {"f": "upcoming", "c": "expired"}
    assert r["rooms"][0]["paused_by"] is None and r["rooms"][0]["simulation"]["code"] == "ok"


# --- Editor ------------------------------------------------------------------------------------------------
def test_alta_de_pausa_de_habitacion_y_global():
    original = plan_con()
    nuevo, id_ = PlanEditor.guardar_pausa(original, {"reason": "Visita de mamá", "from": "2026-12-20", "until": None},
                                          room_id="dormitorio")
    assert id_ == "visita_de_mama" and nuevo.room("dormitorio").pauses[0].end is None
    assert original.room("dormitorio").pauses == []
    nuevo, id_ = PlanEditor.guardar_pausa(original, {"reason": "", "from": "2026-12-20"})
    assert id_ == "pausa" and nuevo.config.pauses[0].id == "pausa"
    nuevo, id2 = PlanEditor.guardar_pausa(nuevo, {"reason": "", "from": "2027-01-01"})
    assert id2 == "pausa_2"


def test_modificar_y_borrar_pausa():
    original = plan_con(pausas_dormitorio=[p()])
    nuevo, _ = PlanEditor.guardar_pausa(original, {"reason": "Ampliada", "from": "2026-11-10", "until": "2026-11-30"},
                                        "vac", "dormitorio")
    assert nuevo.room("dormitorio").pauses[0].reason == "Ampliada" and nuevo.room("dormitorio").pauses[0].id == "vac"
    sin = PlanEditor.borrar_pausa(nuevo, "vac", "dormitorio")
    assert sin.room("dormitorio").pauses == []
    with pytest.raises(ConfigError, match="no existe"):
        PlanEditor.borrar_pausa(original, "fantasma", "dormitorio")
    with pytest.raises(ConfigError, match="no existe"):
        PlanEditor.guardar_pausa(original, p(), "fantasma", "dormitorio")
    with pytest.raises(ConfigError, match="habitación"):
        PlanEditor.guardar_pausa(original, p(), None, "fantasma")


def test_validar_pausa():
    original = plan_con()
    assert PlanEditor.validar_pausa(original, p()) == {"ok": True, "error": None}
    r = PlanEditor.validar_pausa(original, p(until="2026-11-01"))
    assert r["ok"] is False and "anterior" in r["error"]


def test_guardar_ajustes_globales_conserva_las_pausas():
    original = plan_con(pausas_casa=[p(id="g")])
    datos = original.config.to_dict()
    del datos["pauses"]  # el formulario del panel no las lleva
    datos["catch_up"] = "none"
    nuevo = PlanEditor.guardar_global(original, datos)
    assert [x.id for x in nuevo.config.pauses] == ["g"] and nuevo.config.catch_up == "none"


def test_editar_una_habitacion_conserva_sus_pausas():
    original = plan_con(pausas_dormitorio=[p(id="d")])
    nuevo, _ = PlanEditor.guardar_habitacion(original, {"name": "Dormitorio 2"}, "dormitorio")
    assert nuevo.room("dormitorio").name == "Dormitorio 2" and nuevo.room("dormitorio").pauses[0].id == "d"
