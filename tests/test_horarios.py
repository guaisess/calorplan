# Versión: 2026.11.2
"""Los horarios de ejemplo y (si existe) la configuración real local generan el día esperado."""
from __future__ import annotations

import pytest

from calorplan_core.engine import Planner
from fakes import RAIZ, cargar_plan, instante

EJEMPLO = RAIZ / "examples" / "config_ejemplo.json"
LOCAL = RAIZ / "local" / "config_alfredo.json"


def horario(plan, dia):
    """(habitación, tramo, inicio, fin) de todos los tramos de un día."""
    planner = Planner(plan)
    eventos = planner.events_between(instante(dia, "00:00"), instante(dia, "23:59"))
    res = {}
    for e in eventos:
        if e.kind in ("start", "end"):
            res.setdefault((e.room_id, e.slot_id), {})[e.kind] = e.when.strftime("%H:%M")
    return {k: (v["start"], v["end"]) for k, v in res.items()}


def test_horario_de_ejemplo_lunes_y_domingo():
    plan = cargar_plan(EJEMPLO)
    lunes = horario(plan, "2026-11-02")
    assert lunes[("dormitorio", "madrugada")] == ("06:00", "07:00")
    assert ("despacho", "fin_semana") not in lunes  # solo sábado y domingo
    assert lunes[("toallero", "manana")] == ("05:50", "07:35")
    assert ("despacho", "fin_semana") in horario(plan, "2026-11-08")


@pytest.mark.skipif(not LOCAL.exists(), reason="No hay configuración real en local/")
def test_configuracion_real_local():
    """Valida la configuración real (sin subirla al repositorio)."""
    plan = cargar_plan(LOCAL)
    assert len([r for r in plan.rooms if r.actuator.type == "climate"]) == 4
    assert len([r for r in plan.rooms if r.actuator.type == "switch"]) == 3
    lunes = horario(plan, "2026-11-02")
    assert lunes[("alba", "madrugada")] == ("06:00", "07:00")
    assert lunes[("alba", "noche")] == ("19:00", "21:00")
    assert lunes[("principal", "noche")] == ("20:30", "22:15")
    assert lunes[("marta", "noche")] == ("21:15", "23:00")
    assert lunes[("polivalente", "tarde2")] == ("17:30", "19:10")
    assert lunes[("toallero_aseo", "manana")] == ("05:45", "07:15")
    assert lunes[("toallero_bano", "manana")] == ("05:50", "07:35")
    assert ("office", "fin_semana") not in lunes and ("office", "mediodia") in lunes
    sabado = horario(plan, "2026-11-07")
    assert ("alba", "madrugada") not in sabado and ("alba", "noche") not in sabado
    assert sabado[("office", "fin_semana")] == ("07:00", "09:30")
    assert ("alba", "noche") in horario(plan, "2026-11-08")  # domingo
