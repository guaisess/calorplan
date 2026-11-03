# Versión: 2026.11.2
"""Tests del evaluador de condiciones."""
from __future__ import annotations

from calorplan_core import settings as aj
from calorplan_core.engine import Evaluator
from calorplan_core.models import Plan
from fakes import FakeState, RAIZ, cargar_plan

PLAN: Plan = cargar_plan(RAIZ / "examples" / "config_ejemplo.json")
SALA = PLAN.room("dormitorio")
TRAMO = SALA.slot("madrugada")  # exterior < 10, interior < 16
EXT = PLAN.config.outdoor_sensors
INT = SALA.sensors


def evaluar(estados, politica=aj.POLITICA_NO_ENCENDER):
    PLAN.config.unavailable_policy = politica
    return Evaluator(FakeState(estados)).evaluate(SALA, TRAMO, PLAN.config)


def test_agregacion_minimo_ignora_no_disponibles():
    ev = Evaluator(FakeState({"a": "12", "b": "unavailable", "c": "7.5", "d": "texto"}))
    assert ev.aggregate_min(["a", "b", "c", "d", "e"]) == 7.5
    assert ev.aggregate_min(["b", "d"]) is None


def test_enciende_con_condiciones_cumplidas():
    d = evaluar({EXT[0]: "8", EXT[1]: "9", INT[0]: "15", INT[1]: "17"})
    assert d.start and d.code == aj.COD_OK
    assert (d.outdoor, d.indoor) == (8.0, 15.0)  # mínimo de cada grupo


def test_exterior_alto_no_enciende_y_explica():
    d = evaluar({EXT[0]: "17", EXT[1]: "12", INT[0]: "15"})
    assert d.start is False  # 12 < 10 es falso: el mínimo exterior es 12
    assert d.code == aj.COD_EXTERIOR_ALTO
    assert d.reason == "Exterior 12 ≥ 10"


def test_la_comparacion_es_estricta():
    assert not evaluar({EXT[0]: "10", INT[0]: "10"}).start
    assert not evaluar({EXT[0]: "5", INT[0]: "16"}).start
    assert evaluar({EXT[0]: "9.9", INT[0]: "15.9"}).start


def test_interior_calido():
    d = evaluar({EXT[0]: "5", INT[0]: "20", INT[1]: "21"})
    assert (d.start, d.code) == (False, aj.COD_INTERIOR_CALIDO)


def test_sin_datos_exteriores_politica_no_encender():
    d = evaluar({INT[0]: "15"})
    assert (d.start, d.code) == (False, aj.COD_EXTERIOR_NO_DISPONIBLE)


def test_sin_datos_interiores_politica_no_encender():
    d = evaluar({EXT[0]: "5", INT[0]: "unavailable"})
    assert (d.start, d.code) == (False, aj.COD_INTERIOR_NO_DISPONIBLE)


def test_sin_datos_politica_encender_igual():
    assert evaluar({}, aj.POLITICA_ENCENDER_IGUAL).start
    # Con un dato disponible sigue aplicándose su condición
    assert not evaluar({EXT[0]: "20"}, aj.POLITICA_ENCENDER_IGUAL).start


def test_condicion_no_definida_no_exige_sensor():
    despacho = PLAN.room("despacho")
    tramo = despacho.slot("mediodia")
    tramo.indoor_below = None
    d = Evaluator(FakeState({EXT[0]: "5"})).evaluate(despacho, tramo, PLAN.config)
    assert d.start  # no hay sensor interior y no se exige
    tramo.outdoor_below = None
    assert Evaluator(FakeState({})).evaluate(despacho, tramo, PLAN.config).start
