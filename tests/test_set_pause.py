# Versión: 2026.11.11
"""Tests de la lógica de calorplan.set_pause / clear_pause (idempotente, pensada para automatizaciones)."""
from __future__ import annotations

import copy
import json

import pytest

from calorplan_core import settings as aj
from calorplan_core.engine.editor import PlanEditor
from calorplan_core.models import ConfigError, Plan
from fakes import RAIZ

DATOS = json.loads((RAIZ / "examples" / "config_ejemplo.json").read_text(encoding="utf-8"))


def plan() -> Plan:
    return Plan.from_dict(copy.deepcopy(DATOS))


def fijar(p, motivo="Vacaciones", sala=None, desde="2026-12-20", hasta="2027-01-06", habilitada=True):
    return PlanEditor.fijar_pausa(p, sala, motivo, desde, hasta, habilitada)


# --- set_pause ---------------------------------------------------------------------------------------------
def test_crea_la_pausa_de_la_casa_y_de_una_habitacion():
    p, id_, res = fijar(plan())
    assert (id_, res) == ("vacaciones", aj.PAUSA_CREADA)
    assert [x.id for x in p.config.pauses] == ["vacaciones"] and p.config.pauses[0].end.isoformat() == "2027-01-06"
    p, id_, res = fijar(p, sala="dormitorio")
    assert res == "created" and [x.id for x in p.room("dormitorio").pauses] == ["vacaciones"]
    assert len(p.config.pauses) == 1  # la de la casa no cambia


def test_repetir_la_llamada_no_duplica_ni_cambia_nada():
    p, _, _ = fijar(plan())
    mismo, id_, res = fijar(p)
    assert res == aj.PAUSA_SIN_CAMBIOS and id_ == "vacaciones"
    assert mismo is p  # el plan no se toca (así no se llena el historial)
    assert len(mismo.config.pauses) == 1


def test_el_motivo_se_compara_sin_mayusculas_ni_espacios_sobrantes():
    p, _, _ = fijar(plan(), motivo="Vacaciones")
    p2, id_, res = fijar(p, motivo="  vacaciones  ", hasta="2027-01-10")
    assert res == aj.PAUSA_ACTUALIZADA and id_ == "vacaciones" and len(p2.config.pauses) == 1
    assert p2.config.pauses[0].end.isoformat() == "2027-01-10"
    assert fijar(p, motivo="VACACIONES   de   verano")[2] == "created"  # otro motivo distinto


def test_actualiza_fechas_y_estado_de_la_pausa_existente():
    p, _, _ = fijar(plan())
    p, _, res = fijar(p, desde="2026-12-22", hasta=None)  # pasa a «sin fecha de fin»
    assert res == "updated" and p.config.pauses[0].end is None
    assert p.config.pauses[0].start.isoformat() == "2026-12-22"
    p, _, res = fijar(p, desde="2026-12-22", hasta=None, habilitada=False)
    assert res == "updated" and p.config.pauses[0].enabled is False


def test_mismo_motivo_en_ambitos_distintos_son_pausas_distintas():
    p, _, _ = fijar(plan())
    p, _, res = fijar(p, sala="despacho")
    assert res == "created"
    assert len(p.config.pauses) == 1 and len(p.room("despacho").pauses) == 1


def test_sin_fecha_de_fin_y_motivo_vacio():
    p, id_, res = fijar(plan(), motivo="", hasta=None)
    assert res == "created" and id_ == "pausa" and p.config.pauses[0].end is None
    _, id2, res2 = fijar(p, motivo="  ", hasta=None)  # el motivo vacío también identifica a la pausa
    assert (id2, res2) == ("pausa", aj.PAUSA_SIN_CAMBIOS)


def test_errores_no_modifican_el_plan():
    original = plan()
    with pytest.raises(ConfigError, match="anterior"):
        fijar(original, desde="2026-12-20", hasta="2026-12-01")
    with pytest.raises(ConfigError, match="habitación"):
        fijar(original, sala="fantasma")
    with pytest.raises(ConfigError, match="AAAA-MM-DD"):
        fijar(original, desde="20/12/2026")
    with pytest.raises(ConfigError, match="AAAA-MM-DD"):
        fijar(original, hasta="")  # vacío ≠ sin fin
    assert original.config.pauses == []


def test_no_modifica_el_plan_original_al_crear():
    original = plan()
    nuevo, _, _ = fijar(original)
    assert original.config.pauses == [] and len(nuevo.config.pauses) == 1


# --- clear_pause ---------------------------------------------------------------------------------------------
def test_quita_por_motivo_y_por_id():
    p, _, _ = fijar(plan())
    p, _, _ = fijar(p, motivo="Obras")
    sin, n = PlanEditor.quitar_pausas(p, None, motivo=" vacaciones ")
    assert n == 1 and [x.id for x in sin.config.pauses] == ["obras"]
    sin, n = PlanEditor.quitar_pausas(p, None, pause_id="obras")
    assert n == 1 and [x.id for x in sin.config.pauses] == ["vacaciones"]


def test_quita_todas_las_que_compartan_motivo():
    d = copy.deepcopy(DATOS)
    d["global"]["pauses"] = [
        {"id": "a", "reason": "Viaje", "from": "2026-12-01", "until": "2026-12-05", "enabled": True},
        {"id": "b", "reason": "viaje", "from": "2027-01-01", "until": None, "enabled": True}]
    sin, n = PlanEditor.quitar_pausas(Plan.from_dict(d), None, motivo="VIAJE")
    assert n == 2 and sin.config.pauses == []


def test_quitar_algo_que_no_existe_no_falla_y_no_cambia_el_plan():
    p, _, _ = fijar(plan())
    mismo, n = PlanEditor.quitar_pausas(p, None, motivo="inexistente")
    assert n == 0 and mismo is p
    assert PlanEditor.quitar_pausas(p, "despacho", pause_id="vacaciones")[1] == 0  # es de la casa, no del despacho


def test_quitar_exige_id_o_motivo_y_valida_la_habitacion():
    with pytest.raises(ConfigError, match="pause_id"):
        PlanEditor.quitar_pausas(plan(), None)
    with pytest.raises(ConfigError, match="habitación"):
        PlanEditor.quitar_pausas(plan(), "fantasma", motivo="x")


def test_ciclo_completo_como_lo_haria_una_automatizacion():
    """Casa vacía: se pausa sin fin; al volver alguien, se quita. Repetir cada paso es inocuo."""
    p = plan()
    for _ in range(3):  # la automatización se dispara varias veces
        p, _, res = fijar(p, motivo="Casa vacía", hasta=None)
    assert len(p.config.pauses) == 1 and res == aj.PAUSA_SIN_CAMBIOS
    p, n = PlanEditor.quitar_pausas(p, None, motivo="Casa vacía")
    assert n == 1 and p.config.pauses == []
    p, n = PlanEditor.quitar_pausas(p, None, motivo="Casa vacía")
    assert n == 0
