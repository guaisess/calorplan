# Versión: 2026.11.6
"""Tests de la edición de habitaciones (actuador, sensores y agregación)."""
from __future__ import annotations

import copy
import json

import pytest

from calorplan_core.engine.editor import PlanEditor
from calorplan_core.models import ConfigError, Plan
from fakes import RAIZ

DATOS = json.loads((RAIZ / "examples" / "config_ejemplo.json").read_text(encoding="utf-8"))


def plan() -> Plan:
    return Plan.from_dict(copy.deepcopy(DATOS))


def habitacion(**extra):
    base = {"name": "Cocina", "actuator": {"type": "climate", "entity_id": "climate.cocina",
                                           "child_lock_switch": "switch.cocina_bloqueo"},
            "sensors": ["sensor.cocina_temp", "sensor.cocina_temp_2"],
            "indoor_aggregation": "mean"}
    base.update(extra)
    return base


def test_alta_de_habitacion_con_climate_sensores_y_media():
    original = plan()
    nuevo, id_ = PlanEditor.guardar_habitacion(original, habitacion())
    assert id_ == "cocina" and len(original.rooms) == 3  # el original no cambia
    sala = nuevo.room("cocina")
    assert sala.actuator.type == "climate" and sala.actuator.tiene_bloqueo
    assert sala.sensors == ["sensor.cocina_temp", "sensor.cocina_temp_2"]
    assert sala.indoor_aggregation == "mean" and sala.slots == [] and sala.enabled


def test_alta_de_habitacion_con_switch():
    nuevo, id_ = PlanEditor.guardar_habitacion(plan(), habitacion(
        name="Baño 2", actuator={"type": "switch", "entity_id": "switch.toallero2"},
        indoor_aggregation="max"))
    assert id_ == "bano_2" and not nuevo.room(id_).actuator.tiene_bloqueo


def test_los_ids_no_se_repiten_y_se_ignora_el_id_del_cliente():
    p, a = PlanEditor.guardar_habitacion(plan(), habitacion(id="dormitorio"))
    p, b = PlanEditor.guardar_habitacion(p, habitacion())
    assert (a, b) == ("cocina", "cocina_2")


def test_modificar_conserva_id_tramos_y_estado():
    original = plan()
    original.room("despacho").enabled = False
    nuevo, id_ = PlanEditor.guardar_habitacion(original, {
        "name": "Despacho nuevo", "sensors": ["sensor.a", "sensor.b"],
        "indoor_aggregation": "max", "slots": []}, "despacho")
    sala = nuevo.room("despacho")
    assert id_ == "despacho" and sala.name == "Despacho nuevo"
    assert sala.sensors == ["sensor.a", "sensor.b"] and sala.indoor_aggregation == "max"
    assert [t.id for t in sala.slots] == ["fin_semana", "mediodia"]  # los tramos se conservan
    assert sala.enabled is False and sala.actuator.entity_id == "switch.calefaccion_despacho_enchufe"


def test_cambiar_el_actuador_de_una_habitacion():
    nuevo, _ = PlanEditor.guardar_habitacion(plan(), {
        "actuator": {"type": "switch", "entity_id": "switch.otro"}}, "despacho")
    assert nuevo.room("despacho").actuator.entity_id == "switch.otro"


@pytest.mark.parametrize("cambios,fragmento", [
    ({"actuator": {"type": "climate", "entity_id": "switch.mal"}}, "dominio"),
    ({"actuator": {"type": "boiler", "entity_id": "climate.x"}}, "actuador"),
    ({"indoor_aggregation": "mediana"}, "agregación"),
    ({"sensors": "sensor.a"}, "lista"),
    ({"actuator": {"type": "climate", "entity_id": "climate.x", "child_lock_on_start": "quizas"}}, "bloqueo"),
])
def test_datos_invalidos(cambios, fragmento):
    with pytest.raises(ConfigError, match=fragmento):
        PlanEditor.guardar_habitacion(plan(), habitacion(**cambios))


def test_habitacion_inexistente():
    with pytest.raises(ConfigError, match="no existe"):
        PlanEditor.guardar_habitacion(plan(), {"name": "x"}, "fantasma")
    with pytest.raises(ConfigError, match="no existe"):
        PlanEditor.borrar_habitacion(plan(), "fantasma")


def test_borrar_habitacion_con_sus_tramos():
    original = plan()
    nuevo = PlanEditor.borrar_habitacion(original, "despacho")
    assert [r.id for r in nuevo.rooms] == ["dormitorio", "toallero"]
    assert len(original.rooms) == 3


def test_sin_nombre_usa_el_identificador():
    nuevo, id_ = PlanEditor.guardar_habitacion(plan(), habitacion(name=" "))
    assert id_ == "habitacion" and nuevo.room(id_).name == "habitacion"


def test_validar_habitacion():
    assert PlanEditor.validar_habitacion(plan(), habitacion()) == {"ok": True, "error": None}
    r = PlanEditor.validar_habitacion(plan(), habitacion(indoor_aggregation="x"))
    assert r["ok"] is False and "agregación" in r["error"]
    assert PlanEditor.validar_habitacion(plan(), {"name": "x"}, "fantasma")["ok"] is False


def test_la_agregacion_se_conserva_en_el_ciclo_completo():
    nuevo, id_ = PlanEditor.guardar_habitacion(plan(), habitacion())
    assert Plan.from_dict(nuevo.to_dict()).room(id_).indoor_aggregation == "mean"
