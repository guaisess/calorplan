# Versión: 2026.11.23
"""Tests de los calefactores tipo fan (potencia 0-100 %) y del campo `group` de las habitaciones."""
from __future__ import annotations

import asyncio
import copy
import pytest

from calorplan_core import settings as aj
from calorplan_core.models import ConfigError, Plan, Room
from test_runner import DATOS, correr, ev, montar

FAN = "fan.calefactor_bano"


def datos_con_fan(potencia=66, grupo="Baño", hora_fan="05:50"):
    """Ejemplo + un calefactor fan en el mismo grupo que el toallero (tramos solapados)."""
    datos = copy.deepcopy(DATOS)
    toallero = next(r for r in datos["rooms"] if r["id"] == "toallero")
    toallero["group"] = grupo
    datos["rooms"].append({
        "id": "calefactor_bano", "name": "Baño · Calefactor", "group": grupo,
        "actuator": {"type": "fan", "entity_id": FAN},
        "sensors": ["sensor.bano_temperatura"],
        "slots": [{"id": "manana", "name": "Mañana", "days": [0, 1, 2, 3, 4, 5, 6],
                   "start": hora_fan, "duration_minutes": 30, "power": potencia}],
    })
    return datos


# --- Modelos ----------------------------------------------------------------
def test_un_fan_se_acepta_y_se_serializa_con_potencia_y_grupo():
    plan = Plan.from_dict(datos_con_fan())
    sala = plan.room("calefactor_bano")
    assert sala.actuator.type == aj.TIPO_FAN and sala.group == "Baño"
    assert sala.slots[0].power == 66
    otra = Plan.from_dict(plan.to_dict())
    assert otra.room("calefactor_bano").slots[0].power == 66
    assert otra.room("toallero").group == "Baño"


def test_el_fan_exige_dominio_fan():
    datos = datos_con_fan()
    datos["rooms"][-1]["actuator"]["entity_id"] = "switch.no_es_un_fan"
    with pytest.raises(ConfigError):
        Plan.from_dict(datos)


@pytest.mark.parametrize("valor", [-1, 101, 50.5, "50", True])
def test_potencia_fuera_de_rango_o_de_tipo_invalido(valor):
    datos = datos_con_fan(potencia=valor)
    with pytest.raises(ConfigError):
        Plan.from_dict(datos)


def test_group_invalido_o_vacio():
    with pytest.raises(ConfigError):
        Plan.from_dict(datos_con_fan(grupo=5))
    assert Plan.from_dict(datos_con_fan(grupo="  ")).room("calefactor_bano").group is None


def test_sin_group_sigue_siendo_valido():
    assert all(r.group is None for r in Plan.from_dict(DATOS).rooms)


def test_dispositivos_del_mismo_grupo_pueden_solaparse():
    plan = Plan.from_dict(datos_con_fan())  # toallero 05:50-07:35 y calefactor 05:50-06:20
    assert plan.room("toallero").slots and plan.room("calefactor_bano").slots


# --- Motor ----------------------------------------------------------------------
def montar_fan(**kw):
    e = montar(datos_con_fan(**kw), hora="05:50", estados={FAN: "off"})
    return e


def ev_fan(tipo):
    return ev(tipo, sala="calefactor_bano", tramo="manana")


def test_inicio_enciende_el_fan_a_la_potencia_del_tramo():
    e = montar_fan(potencia=66)
    reg = correr(e, ev_fan("start"))
    assert reg.action == "on" and reg.power == 66
    assert e.actuador.llamadas == [("fan_on", FAN, 66)]
    assert "Potencia: 66 %" in e.envio.enviados[0][2]


def test_sin_potencia_en_el_tramo_usa_la_de_por_defecto():
    datos = datos_con_fan()
    del datos["rooms"][-1]["slots"][0]["power"]
    e = montar(datos, hora="05:50", estados={FAN: "off"})
    correr(e, ev_fan("start"))
    assert e.actuador.llamadas == [("fan_on", FAN, aj.POTENCIA_DEFECTO)]


def test_no_reenvia_si_ya_esta_a_esa_potencia_ni_con_redondeo():
    e = montar_fan(potencia=60)
    e.estado.estados[FAN] = "on"
    e.estado.atributos[FAN] = {"percentage": 66}  # el fan solo tiene niveles 33/66/100
    correr(e, ev_fan("start"))
    assert e.actuador.llamadas == []


def test_si_esta_encendido_a_otra_potencia_la_cambia():
    e = montar_fan(potencia=100)
    e.estado.estados[FAN] = "on"
    e.estado.atributos[FAN] = {"percentage": 33}
    correr(e, ev_fan("start"))
    assert ("fan_on", FAN, 100) in e.actuador.llamadas


def test_potencia_no_confirmada_acaba_en_error():
    e = montar_fan(potencia=100)
    e.actuador.ignorar_potencia = True
    e.estado.atributos[FAN] = {"percentage": 33}
    reg = correr(e, ev_fan("start"))
    assert reg.action == "error"


def test_fan_sin_atributo_de_porcentaje_basta_con_que_este_encendido():
    e = montar_fan()
    e.actuador.ignorar_potencia = True  # nunca informa del porcentaje
    reg = correr(e, ev_fan("start"))
    assert reg.action == "on" and len(e.actuador.llamadas) == 1


def test_fin_apaga_el_fan_con_fan_turn_off():
    e = montar_fan()
    e.estado.estados[FAN] = "on"
    reg = correr(e, ev_fan("end"))
    assert reg.action == "off"
    assert e.actuador.llamadas == [("fan_off", FAN)]
    assert e.estado.estados[FAN] == "off"


def test_cada_dispositivo_del_grupo_se_programa_por_separado():
    e = montar_fan()
    correr(e, ev_fan("start"))
    assert e.estado.estados[FAN] == "on" and e.estado.estados["switch.toallero_bano"] == "off"
    correr(e, ev("start", sala="toallero", tramo="manana"))
    assert e.estado.estados["switch.toallero_bano"] == "on"
    correr(e, ev_fan("end"))
    assert e.estado.estados[FAN] == "off" and e.estado.estados["switch.toallero_bano"] == "on"


def test_overview_expone_group_y_power():
    sala = Plan.from_dict(datos_con_fan()).room("calefactor_bano")
    assert sala.to_dict()["group"] == "Baño" and sala.slots[0].to_dict()["power"] == 66
