# Versión: 2026.11.5
"""Tests de la línea de tiempo y del resumen/simulador para el panel."""
from __future__ import annotations

import copy
import json

from calorplan_core.engine import Planner
from calorplan_core.engine.overview import OverviewBuilder
from calorplan_core.engine.timeline import segmentos_dia, semana_habitacion
from calorplan_core.models import Plan, Slot
from fakes import FakeState, RAIZ, cargar_plan, instante

DATOS = json.loads((RAIZ / "examples" / "config_ejemplo.json").read_text(encoding="utf-8"))
EXT = ["sensor.temperatura_exterior", "sensor.temperatura_porche"]
INT = ["sensor.dormitorio_temperatura", "sensor.dormitorio_temperatura_2"]


def tramo(**extra):
    base = {"id": "t", "start": "08:00", "end": "09:30", "days": [0]}
    base.update(extra)
    return Slot.from_dict(base)


def construir(estados=None, cambios=None, ahora=("2026-11-02", "06:30")):
    datos = copy.deepcopy(DATOS)
    if cambios:
        cambios(datos)
    plan = Plan.from_dict(datos)
    estado = FakeState({EXT[0]: "8", EXT[1]: "9", INT[0]: "15", INT[1]: "17",
                        "climate.calefaccion_dormitorio": "off", **(estados or {})})
    return OverviewBuilder(plan, estado).build(instante(*ahora), {}), plan


# --- Línea de tiempo --------------------------------------------------------
def test_segmento_simple():
    assert segmentos_dia(tramo(), 0) == [{
        "slot_id": "t", "start": 480, "end": 570,
        "continued_from_prev": False, "continues_next": False}]
    assert segmentos_dia(tramo(), 1) == []


def test_tramo_que_cruza_la_medianoche_aparece_en_dos_dias():
    t = tramo(start="23:00", end="01:00", days=[4])  # viernes
    viernes, sabado = segmentos_dia(t, 4)[0], segmentos_dia(t, 5)[0]
    assert (viernes["start"], viernes["end"], viernes["continues_next"]) == (1380, 1440, True)
    assert (sabado["start"], sabado["end"], sabado["continued_from_prev"]) == (0, 60, True)


def test_la_semana_es_circular():
    t = tramo(start="23:00", end="01:00", days=[6])  # domingo → lunes
    lunes = segmentos_dia(t, 0)
    assert len(lunes) == 1 and (lunes[0]["start"], lunes[0]["end"]) == (0, 60)
    assert lunes[0]["continued_from_prev"] is True


def test_semana_habitacion_tiene_siete_dias_ordenados():
    plan = cargar_plan(RAIZ / "examples" / "config_ejemplo.json")
    semana = semana_habitacion(plan.room("dormitorio"))
    assert len(semana) == 7
    assert [s["slot_id"] for s in semana[0]] == ["madrugada", "tarde", "noche"]  # lunes
    assert [s["slot_id"] for s in semana[5]] == ["tarde"]  # sábado
    assert all(a["start"] <= b["start"] for dia in semana for a, b in zip(dia, dia[1:]))


# --- Resumen ------------------------------------------------------------------
def test_resumen_general():
    r, _ = construir()
    assert r["weekday"] == 0 and r["minute"] == 390
    assert r["shadow_mode"] is True and r["away_mode"] is False
    assert r["outdoor"] == 8.0
    assert [h["id"] for h in r["rooms"]] == ["dormitorio", "despacho", "toallero"]


def test_resumen_no_incluye_servicios_de_aviso():
    r, _ = construir()
    texto = json.dumps(r)
    assert "telegram_ejemplo" not in texto and "mobile_app" not in texto and '"service"' not in texto
    assert r["channels"] == ["telegram", "movil"]  # solo los ids


def test_habitacion_activa_y_proximo_evento():
    r, _ = construir()
    sala = r["rooms"][0]
    assert sala["active_slot"] == "madrugada"
    assert sala["next"]["kind"] == "end" and sala["next"]["slot_id"] == "madrugada"
    assert sala["actuator"] == {"type": "climate",
                                "entity_id": "climate.calefaccion_dormitorio", "state": "off"}
    assert sala["slots"][0]["duration_minutes"] == 60 and len(sala["week"]) == 7


def test_simulacion_tramo_activo_cumple_condiciones():
    sim = construir()[0]["rooms"][0]["simulation"]
    assert sim["active"] and sim["would_start"] and sim["code"] == "ok"
    assert (sim["outdoor"], sim["indoor"]) == (8.0, 15.0)


def test_simulacion_usa_el_proximo_tramo_si_no_hay_activo():
    sim = construir(ahora=("2026-11-02", "08:00"))[0]["rooms"][0]["simulation"]
    assert sim["slot_id"] == "tarde" and sim["active"] is False


def test_simulacion_condicion_no_cumplida():
    sim = construir({EXT[0]: "20", EXT[1]: "21"})[0]["rooms"][0]["simulation"]
    assert not sim["would_start"] and sim["code"] == "outdoor_too_warm"
    assert sim["reason"] == "Exterior 20 ≥ 10"


def test_simulacion_sin_datos():
    sim = construir({INT[0]: "unknown", INT[1]: "unavailable"})[0]["rooms"][0]["simulation"]
    assert not sim["would_start"] and sim["code"] == "indoor_unavailable"


def test_simulacion_respeta_ausencia_y_deshabilitados():
    def ausencia(d): d["global"]["away_mode"] = True
    sim = construir(cambios=ausencia)[0]["rooms"][0]["simulation"]
    assert not sim["would_start"] and sim["code"] == "away"

    def sala_off(d): d["rooms"][0]["enabled"] = False
    sim = construir(cambios=sala_off)[0]["rooms"][0]["simulation"]
    assert sim["code"] == "room_disabled"

    def tramo_off(d): d["rooms"][0]["slots"][0]["enabled"] = False
    r = construir(cambios=tramo_off)[0]["rooms"][0]
    assert r["simulation"]["code"] == "slot_disabled" and r["active_slot"] is None


def test_habitacion_sin_tramos_no_tiene_simulacion():
    def vaciar(d): d["rooms"][2]["slots"] = []
    sala = construir(cambios=vaciar)[0]["rooms"][2]
    assert sala["simulation"] is None and sala["next"] is None and sala["week"] == [[]] * 7


def test_la_ultima_accion_se_incluye():
    plan = Plan.from_dict(copy.deepcopy(DATOS))
    ultimo = {"dormitorio": {"action": "on", "code": "dry_run"}}
    r = OverviewBuilder(plan, FakeState()).build(instante("2026-11-02", "12:00"), ultimo)
    assert r["rooms"][0]["last"]["action"] == "on" and r["rooms"][1]["last"] is None


def test_next_start_ignora_fines_y_reintentos():
    plan = cargar_plan(RAIZ / "examples" / "config_ejemplo.json")
    inicio = Planner(plan).next_start(instante("2026-11-02", "06:30"), "dormitorio")
    assert inicio.kind == "start" and inicio.slot_id == "tarde"
