# Versión: 2026.11.2
"""Tests del planificador."""
from __future__ import annotations

from datetime import timedelta

from calorplan_core.engine import Planner
from calorplan_core.models import Plan
from fakes import RAIZ, cargar_plan, instante

EJEMPLO = cargar_plan(RAIZ / "examples" / "config_ejemplo.json")


def plan_con(tramos: list[dict]) -> Plan:
    """Plan de una habitación con los tramos indicados."""
    return Plan.from_dict({"rooms": [{
        "id": "h", "name": "H",
        "actuator": {"type": "switch", "entity_id": "switch.h"},
        "slots": tramos}]})


def resumen(eventos):
    """Lista legible (hora local, tipo, tramo)."""
    return [(e.when.strftime("%a %H:%M"), e.kind, e.slot_id) for e in eventos]


def test_eventos_de_un_dia_laborable():
    planner = Planner(EJEMPLO)
    eventos = planner.events_between(instante("2026-11-02", "00:00"),
                                     instante("2026-11-02", "23:59"), "dormitorio")
    assert resumen(eventos) == [
        ("Mon 06:00", "start", "madrugada"), ("Mon 07:00", "end", "madrugada"),
        ("Mon 07:05", "retry", "madrugada"),
        ("Mon 11:00", "start", "tarde"), ("Mon 17:00", "end", "tarde"),
        ("Mon 17:05", "retry", "tarde"),
        ("Mon 19:00", "start", "noche"), ("Mon 21:00", "end", "noche"),
        ("Mon 21:05", "retry", "noche"),
    ]


def test_los_dias_se_respetan():
    planner = Planner(EJEMPLO)
    # Sábado: madrugada (L-V) y noche (D-V) no existen; la tarde sí
    sabado = planner.events_between(instante("2026-11-07", "00:00"),
                                    instante("2026-11-07", "23:59"), "dormitorio")
    assert {e.slot_id for e in sabado} == {"tarde"}
    # Domingo: noche sí (6 está en D-V)
    domingo = planner.events_between(instante("2026-11-08", "00:00"),
                                     instante("2026-11-08", "23:59"), "dormitorio")
    assert {e.slot_id for e in domingo} == {"tarde", "noche"}


def test_limites_del_intervalo():
    planner = Planner(EJEMPLO)
    inicio = instante("2026-11-02", "06:00")
    # (desde, hasta]: el instante exacto de `desde` no se repite
    assert planner.events_between(inicio, inicio + timedelta(minutes=1), "dormitorio") == []
    assert len(planner.events_between(inicio - timedelta(minutes=1), inicio, "dormitorio")) == 1


def test_duracion_en_lugar_de_hora_de_fin():
    planner = Planner(EJEMPLO)
    eventos = planner.events_between(instante("2026-11-02", "00:00"),
                                     instante("2026-11-02", "12:00"), "toallero")
    assert resumen(eventos) == [("Mon 05:50", "start", "manana"), ("Mon 07:35", "end", "manana"),
                                ("Mon 07:40", "retry", "manana")]


def test_tramo_que_cruza_la_medianoche_pertenece_al_dia_de_inicio():
    plan = plan_con([{"id": "n", "start": "23:00", "end": "01:00", "days": [4]}])  # viernes
    planner = Planner(plan)
    eventos = planner.events_between(instante("2026-11-06", "00:00"),
                                     instante("2026-11-08", "00:00"))
    assert resumen(eventos) == [("Fri 23:00", "start", "n"), ("Sat 01:00", "end", "n"),
                                ("Sat 01:05", "retry", "n")]


def test_orden_fin_reintento_inicio_en_el_mismo_instante():
    plan = plan_con([
        {"id": "a", "start": "08:00", "end": "09:00", "days": [0], "retry_off_minutes": 0},
        {"id": "b", "start": "09:00", "end": "10:00", "days": [0], "retry_off_minutes": 0}])
    eventos = Planner(plan).events_between(instante("2026-11-02", "08:30"),
                                           instante("2026-11-02", "09:30"))
    assert resumen(eventos) == [("Mon 09:00", "end", "a"), ("Mon 09:00", "start", "b")]
    # Con reintento que coincide con otro inicio: fin → reintento → inicio
    plan = plan_con([
        {"id": "a", "start": "08:00", "end": "09:00", "days": [0], "retry_off_minutes": 5},
        {"id": "b", "start": "09:05", "end": "10:00", "days": [0], "retry_off_minutes": 0}])
    eventos = Planner(plan).events_between(instante("2026-11-02", "09:00"),
                                           instante("2026-11-02", "09:30"))
    assert [e.kind for e in eventos] == ["retry", "start"]


def test_retry_cero_no_genera_reintento():
    plan = plan_con([{"id": "a", "start": "08:00", "end": "09:00", "days": [0],
                      "retry_off_minutes": 0}])
    eventos = Planner(plan).events_between(instante("2026-11-02", "00:00"),
                                           instante("2026-11-03", "00:00"))
    assert [e.kind for e in eventos] == ["start", "end"]


def test_proximo_evento():
    planner = Planner(EJEMPLO)
    siguiente = planner.next_event(instante("2026-11-02", "12:00"), "dormitorio")
    assert (siguiente.kind, siguiente.slot_id) == ("end", "tarde")
    # Tras el último evento del viernes sigue el del sábado
    siguiente = planner.next_event(instante("2026-11-06", "21:05"), "dormitorio")
    assert siguiente.when == instante("2026-11-07", "11:00")
    # Sin filtro devuelve el más cercano de cualquier habitación
    assert planner.next_event(instante("2026-11-02", "05:00")).slot_id == "manana"


def test_proximo_evento_sin_tramos():
    assert Planner(Plan()).next_event(instante("2026-11-02", "05:00")) is None


def test_tramos_activos():
    planner = Planner(EJEMPLO)
    sala = EJEMPLO.room("dormitorio")
    activos = lambda d, h: [t.id for t in planner.active_slots(sala, instante(d, h))]
    assert activos("2026-11-02", "06:30") == ["madrugada"]
    assert activos("2026-11-02", "06:00") == ["madrugada"]  # el inicio cuenta
    assert activos("2026-11-02", "07:00") == []  # el fin no
    assert activos("2026-11-07", "06:30") == []  # sábado


def test_tramo_activo_tras_la_medianoche_y_cruzando_la_semana():
    plan = plan_con([{"id": "n", "start": "23:00", "end": "01:00", "days": [6]}])  # domingo
    sala = plan.rooms[0]
    planner = Planner(plan)
    assert [t.id for t in planner.active_slots(sala, instante("2026-11-09", "00:30"))] == ["n"]
    assert planner.active_slots(sala, instante("2026-11-09", "01:00")) == []


def test_cambio_de_hora_mantiene_la_hora_local():
    planner = Planner(EJEMPLO)
    # El fin del horario de verano fue el 25-oct-2026: el lunes 26 sigue siendo 11:00 local
    eventos = planner.events_between(instante("2026-10-24", "00:00"),
                                     instante("2026-10-27", "00:00"), "dormitorio")
    inicios = [e.when for e in eventos if e.slot_id == "tarde" and e.kind == "start"]
    assert len(inicios) == 3 and all(h.hour == 11 for h in inicios)
