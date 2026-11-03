# Versión: 2026.11.2
"""Tests de los modelos y su validación."""
from __future__ import annotations

import copy
import json

import pytest

from calorplan_core.models import ConfigError, Plan, Slot
from fakes import RAIZ

EJEMPLO = json.loads((RAIZ / "examples" / "config_ejemplo.json").read_text(encoding="utf-8"))


def tramo(**cambios):
    """Diccionario de tramo válido con cambios."""
    base = {"id": "t", "start": "08:00", "end": "09:00", "days": [0]}
    base.update(cambios)
    return base


def test_ejemplo_valido_y_ida_y_vuelta():
    plan = Plan.from_dict(EJEMPLO)
    assert [r.id for r in plan.rooms] == ["dormitorio", "despacho", "toallero"]
    assert Plan.from_dict(plan.to_dict()).to_dict() == plan.to_dict()


def test_plan_vacio_por_defecto():
    assert Plan.from_dict(None).rooms == []


def test_fin_y_duracion_a_la_vez_es_error():
    with pytest.raises(ConfigError):
        Slot.from_dict(tramo(duration_minutes=30))


def test_sin_fin_ni_duracion_es_error():
    with pytest.raises(ConfigError):
        Slot.from_dict({"id": "t", "start": "08:00", "days": [0]})


@pytest.mark.parametrize("campo,valor", [
    ("start", "8h"), ("days", [7]), ("days", []), ("retry_off_minutes", -1),
    ("setpoint", "caliente"),
])
def test_valores_invalidos(campo, valor):
    with pytest.raises(ConfigError):
        Slot.from_dict(tramo(**{campo: valor}))


def test_duracion_con_cruce_de_medianoche():
    assert Slot.from_dict(tramo(start="23:00", end="01:00")).duracion_minutos == 120
    assert Slot.from_dict(tramo(start="08:00", end="08:00")).duracion_minutos == 1440


def test_solape_mismo_dia():
    a = Slot.from_dict(tramo(id="a", start="08:00", end="10:00"))
    b = Slot.from_dict(tramo(id="b", start="09:59", end="11:00"))
    c = Slot.from_dict(tramo(id="c", start="10:00", end="11:00"))
    assert a.solapa_con(b)
    assert not a.solapa_con(c)  # tocarse no es solapar


def test_solape_cruzando_medianoche():
    noche = Slot.from_dict(tramo(id="n", start="23:00", end="01:00", days=[0]))
    madrugada = Slot.from_dict(tramo(id="m", start="00:30", end="02:00", days=[1]))
    otro_dia = Slot.from_dict(tramo(id="o", start="00:30", end="02:00", days=[2]))
    assert noche.solapa_con(madrugada)
    assert not noche.solapa_con(otro_dia)


def test_solape_cruzando_la_semana():
    domingo = Slot.from_dict(tramo(id="d", start="23:00", end="01:00", days=[6]))
    lunes = Slot.from_dict(tramo(id="l", start="00:30", end="02:00", days=[0]))
    assert domingo.solapa_con(lunes)


def test_habitacion_rechaza_solapes_e_ids_repetidos():
    datos = copy.deepcopy(EJEMPLO)
    sala = datos["rooms"][1]
    sala["slots"].append({**sala["slots"][1], "id": "otro", "start": "12:00"})
    with pytest.raises(ConfigError, match="solapan"):
        Plan.from_dict(datos)
    datos = copy.deepcopy(EJEMPLO)
    datos["rooms"][1]["slots"][1]["id"] = datos["rooms"][1]["slots"][0]["id"]
    with pytest.raises(ConfigError, match="repetidos"):
        Plan.from_dict(datos)


def test_canal_inexistente_y_ids_repetidos():
    datos = copy.deepcopy(EJEMPLO)
    datos["rooms"][0]["slots"][0]["notify"] = {"mode": "on", "channels": ["fantasma"]}
    with pytest.raises(ConfigError, match="fantasma"):
        Plan.from_dict(datos)
    datos = copy.deepcopy(EJEMPLO)
    datos["rooms"][1]["id"] = "dormitorio"
    with pytest.raises(ConfigError, match="habitación"):
        Plan.from_dict(datos)


def test_actuador_dominio_y_bloqueo():
    datos = copy.deepcopy(EJEMPLO)
    datos["rooms"][0]["actuator"]["entity_id"] = "switch.mal"
    with pytest.raises(ConfigError):
        Plan.from_dict(datos)
    datos = copy.deepcopy(EJEMPLO)
    datos["rooms"][0]["actuator"]["child_lock_on_end"] = "quizas"
    with pytest.raises(ConfigError):
        Plan.from_dict(datos)


def test_defectos_de_bloqueo_infantil():
    act = Plan.from_dict(EJEMPLO).rooms[0].actuator
    assert (act.child_lock_on_start, act.child_lock_on_end) == ("lock", "none")
    assert act.tiene_bloqueo


def test_version_de_esquema_desconocida():
    with pytest.raises(ConfigError):
        Plan.from_dict({"version": 99})
