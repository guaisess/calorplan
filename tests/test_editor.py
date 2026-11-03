# Versión: 2026.11.6
"""Tests del editor de tramos y del historial de versiones."""
from __future__ import annotations

import copy
import json

import pytest

from calorplan_core import settings as aj
from calorplan_core.engine.editor import PlanEditor, generar_id
from calorplan_core.engine.history import History
from calorplan_core.models import ConfigError, Plan
from fakes import RAIZ, instante

DATOS = json.loads((RAIZ / "examples" / "config_ejemplo.json").read_text(encoding="utf-8"))


def plan() -> Plan:
    return Plan.from_dict(copy.deepcopy(DATOS))


def tramo(**extra):
    base = {"name": "Noche tardía", "start": "22:00", "end": "23:00", "days": [0, 1],
            "setpoint": 19, "conditions": {"outdoor_below": 12, "indoor_below": 18}}
    base.update(extra)
    return base


# --- Identificadores -------------------------------------------------------------
def test_generar_id_quita_tildes_y_evita_repetidos():
    assert generar_id("Mañana tardía", []) == "manana_tardia"
    assert generar_id("Tarde", ["tarde"]) == "tarde_2"
    assert generar_id("Tarde", ["tarde", "tarde_2"]) == "tarde_3"
    assert generar_id("", []) == aj.ID_TRAMO_PREFIJO
    assert generar_id("¡¡¿??", []) == aj.ID_TRAMO_PREFIJO


# --- Alta y cambio ------------------------------------------------------------------
def test_alta_de_tramo_no_modifica_el_plan_original():
    original = plan()
    nuevo, id_ = PlanEditor.guardar_tramo(original, "dormitorio", tramo())
    assert id_ == "noche_tardia"
    assert len(original.room("dormitorio").slots) == 3
    t = nuevo.room("dormitorio").slot(id_)
    assert (t.setpoint, t.outdoor_below, t.indoor_below) == (19.0, 12.0, 18.0)


def test_cambio_de_tramo_conserva_el_id_y_el_orden():
    nuevo, id_ = PlanEditor.guardar_tramo(plan(), "dormitorio", tramo(
        name="Tarde cambiada", start="12:00", end="16:00", days=[0, 1, 2, 3, 4, 5, 6]), "tarde")
    assert id_ == "tarde"
    assert [t.id for t in nuevo.room("dormitorio").slots] == ["madrugada", "tarde", "noche"]
    assert nuevo.room("dormitorio").slot("tarde").name == "Tarde cambiada"


def test_se_ignora_un_id_enviado_por_el_cliente():
    nuevo, id_ = PlanEditor.guardar_tramo(plan(), "dormitorio", tramo(id="tarde"))
    assert id_ == "noche_tardia"


def test_solape_rechazado_y_plan_intacto():
    original = plan()
    with pytest.raises(ConfigError, match="solapan"):
        PlanEditor.guardar_tramo(original, "dormitorio", tramo(start="10:00", end="12:00", days=[0]))
    assert len(original.room("dormitorio").slots) == 3


def test_cambiar_un_tramo_no_choca_consigo_mismo():
    PlanEditor.guardar_tramo(plan(), "dormitorio", tramo(
        start="11:00", end="16:00", days=[0, 1, 2, 3, 4, 5, 6]), "tarde")


def test_errores_de_habitacion_tramo_y_datos():
    with pytest.raises(ConfigError, match="habitación"):
        PlanEditor.guardar_tramo(plan(), "fantasma", tramo())
    with pytest.raises(ConfigError, match="no existe"):
        PlanEditor.guardar_tramo(plan(), "dormitorio", tramo(), "fantasma")
    with pytest.raises(ConfigError):
        PlanEditor.guardar_tramo(plan(), "dormitorio", tramo(start="8h"))
    with pytest.raises(ConfigError, match="no ambos"):
        PlanEditor.guardar_tramo(plan(), "dormitorio", tramo(duration_minutes=30))


def test_canal_inexistente_en_el_tramo():
    with pytest.raises(ConfigError, match="fantasma"):
        PlanEditor.guardar_tramo(plan(), "dormitorio", tramo(
            notify={"mode": "on", "channels": ["fantasma"]}))


def test_aviso_propio_del_tramo():
    nuevo, id_ = PlanEditor.guardar_tramo(plan(), "dormitorio", tramo(
        notify={"mode": "both", "channels": ["telegram", "movil"]}, notify_on_skip=True))
    t = nuevo.room("dormitorio").slot(id_)
    assert t.notify.channels == ["telegram", "movil"] and t.notify_on_skip


# --- Baja ----------------------------------------------------------------------------
def test_borrar_tramo():
    original = plan()
    nuevo = PlanEditor.borrar_tramo(original, "dormitorio", "tarde")
    assert [t.id for t in nuevo.room("dormitorio").slots] == ["madrugada", "noche"]
    assert len(original.room("dormitorio").slots) == 3
    with pytest.raises(ConfigError):
        PlanEditor.borrar_tramo(original, "dormitorio", "fantasma")
    with pytest.raises(ConfigError):
        PlanEditor.borrar_tramo(original, "fantasma", "tarde")


# --- Validación previa -----------------------------------------------------------------
def test_validar_ok():
    assert PlanEditor.validar(plan(), "dormitorio", tramo()) == {
        "ok": True, "error": None, "conflicts": []}


def test_validar_devuelve_los_tramos_en_conflicto():
    r = PlanEditor.validar(plan(), "dormitorio", tramo(start="10:00", end="12:00", days=[0]))
    assert r["ok"] is False and r["conflicts"] == ["tarde"] and "solapan" in r["error"]


def test_validar_datos_invalidos_sin_conflictos():
    r = PlanEditor.validar(plan(), "dormitorio", tramo(start="25:99"))
    assert r["ok"] is False and r["conflicts"] == [] and "HH:MM" in r["error"]


def test_validar_al_editar_no_cuenta_el_propio_tramo():
    assert PlanEditor.validar(plan(), "dormitorio", tramo(
        start="11:00", end="16:00", days=[0, 1, 2, 3, 4, 5, 6]), "tarde")["ok"]


# --- Historial ----------------------------------------------------------------------------
def test_historial_registra_lista_y_restaura():
    h = History()
    original = plan()
    h.registrar(original, "primero", instante("2026-11-03", "10:00"))
    nuevo, _ = PlanEditor.guardar_tramo(original, "dormitorio", tramo())
    h.registrar(nuevo, "segundo", instante("2026-11-03", "11:00"))
    lista = h.listar()
    assert [e["reason"] for e in lista] == ["segundo", "primero"]  # la más reciente primero
    assert lista[0]["slots"] == 7 and lista[1]["slots"] == 6 and lista[0]["rooms"] == 3
    assert "plan" not in lista[0]
    assert h.obtener(1).to_dict() == original.to_dict()


def test_historial_limita_el_numero_de_versiones():
    h = History(maximo=3)
    for i in range(5):
        h.registrar(plan(), f"v{i}", instante("2026-11-03", "10:00"))
    assert [e["reason"] for e in h.listar()] == ["v4", "v3", "v2"]


def test_historial_se_persiste_y_recupera():
    h = History()
    h.registrar(plan(), "x", instante("2026-11-03", "10:00"))
    copia = History(json.loads(json.dumps(h.to_list())))
    assert copia.listar() == h.listar()


def test_historial_version_inexistente():
    with pytest.raises(ConfigError):
        History().obtener(0)
    h = History()
    h.registrar(plan(), "x", instante("2026-11-03", "10:00"))
    with pytest.raises(ConfigError):
        h.obtener(-1)


def test_sin_nombre_se_usa_el_identificador():
    nuevo, id_ = PlanEditor.guardar_tramo(plan(), "dormitorio", tramo(name="  "))
    assert id_ == aj.ID_TRAMO_PREFIJO and nuevo.room("dormitorio").slot(id_).name == id_
    nuevo, id_ = PlanEditor.guardar_tramo(plan(), "dormitorio", tramo(name=""), "tarde")
    assert nuevo.room("dormitorio").slot("tarde").name == "tarde"
