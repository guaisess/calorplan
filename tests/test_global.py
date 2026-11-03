# Versión: 2026.11.6
"""Tests de la configuración global: agregación de sensores, plantillas y edición."""
from __future__ import annotations

import copy
import json

import pytest

from calorplan_core import settings as aj
from calorplan_core.engine import Evaluator
from calorplan_core.engine.editor import PlanEditor
from calorplan_core.models import ConfigError, Plan
from fakes import FakeState, RAIZ

DATOS = json.loads((RAIZ / "examples" / "config_ejemplo.json").read_text(encoding="utf-8"))
EXT = ["sensor.temperatura_exterior", "sensor.temperatura_porche"]
INT = ["sensor.dormitorio_temperatura", "sensor.dormitorio_temperatura_2"]


def plan(**cambios_global) -> Plan:
    datos = copy.deepcopy(DATOS)
    datos["global"].update(cambios_global)
    return Plan.from_dict(datos)


# --- Agregación de sensores -------------------------------------------------------------
@pytest.mark.parametrize("modo,esperado", [("min", 8.0), ("max", 12.0), ("mean", 10.0)])
def test_agregacion_exterior(modo, esperado):
    ev = Evaluator(FakeState({EXT[0]: "8", EXT[1]: "12"}))
    assert ev.aggregate(EXT, modo) == esperado


def test_la_media_ignora_los_sensores_sin_datos():
    ev = Evaluator(FakeState({EXT[0]: "8", EXT[1]: "unavailable"}))
    assert ev.aggregate(EXT, "mean") == 8.0 and ev.aggregate(EXT, "max") == 8.0
    assert ev.aggregate(["x"], "mean") is None


def test_por_defecto_es_el_minimo_y_se_conserva_el_comportamiento():
    assert plan().config.outdoor_aggregation == "min"
    assert plan().room("dormitorio").indoor_aggregation == "min"


def test_el_evaluador_usa_la_agregacion_configurada():
    sala_estados = {EXT[0]: "8", EXT[1]: "12", INT[0]: "15", INT[1]: "17", }
    for modo, enciende in [("min", True), ("mean", False), ("max", False)]:  # umbral exterior: < 10
        p = plan(outdoor_aggregation=modo)
        d = Evaluator(FakeState(sala_estados)).evaluate(
            p.room("dormitorio"), p.room("dormitorio").slot("madrugada"), p.config)
        assert d.start is enciende, modo


def test_agregacion_interior_por_habitacion():
    datos = copy.deepcopy(DATOS)
    datos["rooms"][0]["indoor_aggregation"] = "max"  # umbral interior: < 16
    p = Plan.from_dict(datos)
    estados = {EXT[0]: "5", EXT[1]: "5", INT[0]: "15", INT[1]: "17"}
    d = Evaluator(FakeState(estados)).evaluate(p.room("dormitorio"), p.room("dormitorio").slot("madrugada"), p.config)
    assert not d.start and d.code == aj.COD_INTERIOR_CALIDO and d.indoor == 17.0


def test_agregacion_invalida():
    with pytest.raises(ConfigError, match="Agregación"):
        plan(outdoor_aggregation="mediana")
    datos = copy.deepcopy(DATOS)
    datos["rooms"][0]["indoor_aggregation"] = "mediana"
    with pytest.raises(ConfigError, match="agregación"):
        Plan.from_dict(datos)


def test_agregacion_ida_y_vuelta():
    p = plan(outdoor_aggregation="mean")
    assert Plan.from_dict(p.to_dict()).config.outdoor_aggregation == "mean"


# --- Plantillas ------------------------------------------------------------------------------
def test_plantilla_valida():
    p = plan(templates={"on": "Enciende {room} a {setpoint} °C ({time})"})
    assert p.config.plantilla("on").startswith("Enciende")


@pytest.mark.parametrize("texto,fragmento", [
    ("Hola {rom}", "variable desconocida {rom}"),
    ("Hola {room", "formato no válido"),
    ("Hola {}", "variable desconocida"),
    ("Hola {0}", "variable desconocida"),
])
def test_plantilla_invalida(texto, fragmento):
    with pytest.raises(ConfigError, match="Plantillas globales") as err:
        plan(templates={"on": texto})
    assert fragmento in str(err.value)


def test_plantilla_de_accion_desconocida_y_de_canal():
    with pytest.raises(ConfigError, match="acción desconocida"):
        plan(templates={"encender": "x"})
    datos = copy.deepcopy(DATOS)
    datos["global"]["channels"][0]["templates"] = {"off": "{slott}"}
    with pytest.raises(ConfigError, match="Canal 'telegram'"):
        Plan.from_dict(datos)


def test_las_plantillas_por_defecto_son_validas():
    from calorplan_core.models.notify import validar_plantillas
    validar_plantillas(dict(aj.PLANTILLAS_DEFECTO), "defecto")


# --- Edición de ajustes globales ----------------------------------------------------------------
def test_guardar_global_cambia_ajustes_y_conserva_ausencia_y_habitaciones():
    original = plan(away_mode=True)
    nuevo_global = {**original.config.to_dict(), "shadow_mode": False,
                    "outdoor_aggregation": "mean", "away_mode": False,
                    "outdoor_sensors": [EXT[0]]}
    nuevo = PlanEditor.guardar_global(original, nuevo_global)
    assert nuevo.config.shadow_mode is False and nuevo.config.outdoor_aggregation == "mean"
    assert nuevo.config.outdoor_sensors == [EXT[0]]
    assert nuevo.config.away_mode is True  # se gestiona con su propio interruptor
    assert [r.id for r in nuevo.rooms] == [r.id for r in original.rooms]
    assert original.config.shadow_mode is True  # el original no cambia


def test_no_se_puede_quitar_un_canal_en_uso():
    original = plan()
    datos = original.config.to_dict()
    datos["channels"] = [c for c in datos["channels"] if c["id"] != "telegram"]
    datos["default_notify"] = {"mode": "both", "channels": ["movil"]}
    plan_con_uso = copy.deepcopy(DATOS)
    plan_con_uso["rooms"][0]["slots"][0]["notify"] = {"mode": "on", "channels": ["telegram"]}
    with pytest.raises(ConfigError, match="telegram"):
        PlanEditor.guardar_global(Plan.from_dict(plan_con_uso), datos)


def test_validar_global():
    original = plan()
    ok = PlanEditor.validar_global(original, original.config.to_dict())
    assert ok == {"ok": True, "error": None}
    mal = {**original.config.to_dict(), "unavailable_policy": "quiza"}
    r = PlanEditor.validar_global(original, mal)
    assert r["ok"] is False and "Política" in r["error"]
    mal = {**original.config.to_dict(), "templates": {"on": "{nope}"}}
    assert PlanEditor.validar_global(original, mal)["ok"] is False


def test_canal_nuevo_y_aviso_por_defecto():
    original = plan()
    datos = original.config.to_dict()
    datos["channels"].append({"id": "salon", "type": "notify", "service": "notify.alexa_salon"})
    datos["default_notify"] = {"mode": "on", "channels": ["telegram", "salon"]}
    nuevo = PlanEditor.guardar_global(original, datos)
    assert nuevo.config.canal("salon").service == "notify.alexa_salon"
    assert nuevo.config.default_notify.channels == ["telegram", "salon"]
