# Versión: 2026.11.9
"""Tests de la reevaluación durante el tramo (omisiones por condiciones que luego se cumplen)."""
from __future__ import annotations

import asyncio
import copy
import json
from types import SimpleNamespace

import pytest

from calorplan_core import settings as aj
from calorplan_core.engine import Notifier, PlannedEvent, Runner
from calorplan_core.models import ConfigError, Plan
from fakes import (FakeActuator, FakeClock, FakeEvents, FakeNotify, FakeState,
                   RAIZ, instante)

DATOS = json.loads((RAIZ / "examples" / "config_ejemplo.json").read_text(encoding="utf-8"))
CLIMA = "climate.calefaccion_dormitorio"
EXT = ["sensor.temperatura_exterior", "sensor.temperatura_porche"]
INT = ["sensor.dormitorio_temperatura", "sensor.dormitorio_temperatura_2"]
FRIO = {INT[0]: "15", INT[1]: "15"}
CALIDO = {INT[0]: "17", INT[1]: "17"}  # el umbral del tramo «madrugada» es interior < 16


def montar(sombra=False, hora="06:00", cambios=None, **global_):
    datos = copy.deepcopy(DATOS)
    datos["global"]["shadow_mode"] = sombra
    datos["global"].update(global_)
    if cambios:
        cambios(datos)
    plan = Plan.from_dict(datos)
    estado = FakeState({EXT[0]: "8", EXT[1]: "9", **CALIDO, CLIMA: "off",
                        "sensor.despacho_temperatura": "18", "switch.calefaccion_despacho_enchufe": "off"})
    reloj = FakeClock(instante("2026-11-02", hora))
    envio, eventos = FakeNotify(), FakeEvents()
    act = FakeActuator(estado)
    runner = Runner(plan, estado, act, Notifier(plan, envio, reloj), reloj, eventos)
    return SimpleNamespace(plan=plan, estado=estado, act=act, envio=envio, eventos=eventos,
                           reloj=reloj, runner=runner)


def inicio(e, sala="dormitorio", tramo="madrugada"):
    return asyncio.run(e.runner.handle(PlannedEvent(instante("2026-11-02", "06:00"), "start", sala, tramo)))


def reevaluar(e, sala=None):
    return asyncio.run(e.runner.reevaluate(sala))


def hora(e, texto):
    e.reloj.fijar(instante("2026-11-02", texto))


# --- Caso principal ---------------------------------------------------------------------------------------
def test_la_omision_por_condicion_deja_el_tramo_pendiente_y_se_reevalua():
    e = montar()
    assert inicio(e).code == aj.COD_INTERIOR_CALIDO
    assert e.runner.salas_pendientes() == {"dormitorio"}
    hora(e, "06:20")
    e.estado.estados.update(FRIO)  # la habitación se enfría
    registros = reevaluar(e)
    assert [(r.action, r.code) for r in registros] == [("on", aj.COD_OK)]
    assert registros[0].reason == aj.MOTIVO_REEVALUACION and registros[0].kind == "start"
    assert e.act.llamadas[0] == ("heat", CLIMA, "heat", 20.0)
    assert len(e.envio.enviados) == 1 and "ACTIVADA" in e.envio.enviados[0][2]
    assert e.runner.salas_pendientes() == set()


def test_mientras_no_se_cumpla_no_hay_registros_ni_avisos():
    e = montar()
    e.plan.room("dormitorio").slot("madrugada").notify_on_skip = True
    inicio(e)  # el inicio sí registra y avisa de la omisión (una vez)
    registros_antes, avisos_antes = len(e.eventos.registros), len(e.envio.enviados)
    assert avisos_antes == 1
    for minuto in ("06:15", "06:30", "06:45"):
        hora(e, minuto)
        assert reevaluar(e) == []
    assert len(e.eventos.registros) == registros_antes  # las omisiones repetidas no se registran
    assert len(e.envio.enviados) == avisos_antes  # ni avisan
    assert e.act.llamadas == []


def test_una_vez_encendido_no_vuelve_a_actuar():
    e = montar()
    inicio(e)
    e.estado.estados.update(FRIO)
    reevaluar(e)
    llamadas = len(e.act.llamadas)
    e.estado.estados[CLIMA] = "off"  # el usuario lo apaga a mano
    hora(e, "06:30")
    assert reevaluar(e) == [] and len(e.act.llamadas) == llamadas


def test_si_el_tramo_termina_se_descarta():
    e = montar()
    inicio(e)
    e.estado.estados.update(FRIO)
    hora(e, "07:30")  # el tramo 06:00-07:00 ya terminó
    assert reevaluar(e) == [] and e.act.llamadas == [] and e.runner.salas_pendientes() == set()


def test_el_fin_del_tramo_limpia_los_pendientes():
    e = montar()
    inicio(e)
    hora(e, "07:00")
    asyncio.run(e.runner.handle(PlannedEvent(instante("2026-11-02", "07:00"), "end", "dormitorio", "madrugada")))
    assert e.runner.salas_pendientes() == set()


def test_si_ya_esta_encendido_a_mano_no_se_interviene():
    e = montar()
    inicio(e)
    e.estado.estados.update(FRIO)
    e.estado.estados[CLIMA] = "heat"
    hora(e, "06:20")
    assert reevaluar(e) == [] and e.act.llamadas == [] and e.runner.salas_pendientes() == set()


# --- Bloqueos que se levantan ---------------------------------------------------------------------------------
@pytest.mark.parametrize("bloqueo", ["ausencia", "pausa", "habitacion", "tramo"])
def test_los_bloqueos_mantienen_el_tramo_pendiente_y_se_reanudan(bloqueo):
    e = montar()
    inicio(e)
    e.estado.estados.update(FRIO)
    sala = e.plan.room("dormitorio")
    if bloqueo == "ausencia":
        e.plan.config.away_mode = True
    elif bloqueo == "pausa":
        sala.pauses = [__import__("calorplan_core").models.Pause.from_dict(
            {"id": "p", "from": "2026-11-01", "until": "2026-11-05"})]
    elif bloqueo == "habitacion":
        sala.enabled = False
    else:
        sala.slot("madrugada").enabled = False
    hora(e, "06:20")
    assert reevaluar(e) == [] and e.act.llamadas == []
    assert e.runner.salas_pendientes() == {"dormitorio"}  # sigue pendiente
    e.plan.config.away_mode = False
    sala.pauses = []
    sala.enabled = True
    sala.slot("madrugada").enabled = True
    hora(e, "06:40")
    assert [r.action for r in reevaluar(e)] == ["on"]


def test_las_omisiones_por_ausencia_pausa_o_deshabilitado_no_quedan_pendientes():
    e = montar()
    e.plan.config.away_mode = True
    assert inicio(e).code == aj.COD_AUSENCIA
    assert e.runner.salas_pendientes() == set()


# --- Sin datos ---------------------------------------------------------------------------------------------------
def test_sin_datos_de_sensor_se_reevalua_cuando_vuelven():
    e = montar(unavailable_policy="do_not_start")
    e.estado.estados.update({INT[0]: "unavailable", INT[1]: "unknown"})
    assert inicio(e).code == aj.COD_INTERIOR_NO_DISPONIBLE
    hora(e, "06:15")
    assert reevaluar(e) == []
    e.estado.estados.update(FRIO)  # los sensores vuelven a informar
    hora(e, "06:30")
    assert [r.action for r in reevaluar(e)] == ["on"]


# --- Errores y varias habitaciones --------------------------------------------------------------------------
def test_un_fallo_del_actuador_se_reintenta_en_la_siguiente_reevaluacion():
    e = montar()
    inicio(e)
    e.estado.estados.update(FRIO)
    ok = e.act.climate_heat

    async def falla(*a):
        raise RuntimeError("sin conexión")
    e.act.climate_heat = falla
    hora(e, "06:15")
    assert [r.action for r in reevaluar(e)] == ["error"]
    assert e.runner.salas_pendientes() == {"dormitorio"}  # no se da por iniciado
    e.act.climate_heat = ok
    hora(e, "06:30")
    assert [r.action for r in reevaluar(e)] == ["on"]


def test_se_puede_reevaluar_una_sola_habitacion():
    def dos_tramos(d):
        d["rooms"][1]["slots"][1]["days"] = [0]  # despacho «mediodía»: lunes 11:30-14:15
    e = montar(cambios=dos_tramos, hora="11:30")
    e.estado.estados["sensor.despacho_temperatura"] = "25"  # despacho: demasiado cálido (< 20)
    asyncio.run(e.runner.handle(PlannedEvent(instante("2026-11-02", "11:30"), "start", "despacho", "mediodia")))
    e.reloj.fijar(instante("2026-11-02", "06:00"))
    inicio(e)  # dormitorio también omitido
    assert e.runner.salas_pendientes() == {"despacho", "dormitorio"}
    e.reloj.fijar(instante("2026-11-02", "11:45"))
    e.estado.estados["sensor.despacho_temperatura"] = "18"
    e.estado.estados.update(FRIO)
    registros = reevaluar(e, "despacho")
    assert [r.room_id for r in registros] == ["despacho"]
    assert e.runner.salas_pendientes() == {"dormitorio"}  # el dormitorio (06:00-07:00) sigue en la lista


def test_en_modo_sombra_la_reevaluacion_solo_simula():
    e = montar(sombra=True)
    inicio(e)
    e.estado.estados.update(FRIO)
    hora(e, "06:20")
    registros = reevaluar(e)
    assert registros[0].simulated and registros[0].code == aj.COD_SIMULACION
    assert e.act.llamadas == [] and e.envio.enviados == []


# --- Configuración ------------------------------------------------------------------------------------------------
def test_el_ajuste_por_defecto_es_cero_y_se_guarda():
    assert Plan.from_dict(copy.deepcopy(DATOS)).config.reevaluate_minutes == 0
    datos = copy.deepcopy(DATOS)
    datos["global"]["reevaluate_minutes"] = 15
    plan = Plan.from_dict(datos)
    assert plan.config.reevaluate_minutes == 15
    assert Plan.from_dict(plan.to_dict()).config.reevaluate_minutes == 15


@pytest.mark.parametrize("valor", [-1, 1441, "15", 1.5, True, None])
def test_valores_no_validos_del_ajuste(valor):
    datos = copy.deepcopy(DATOS)
    datos["global"]["reevaluate_minutes"] = valor
    with pytest.raises(ConfigError, match="reevaluate_minutes"):
        Plan.from_dict(datos)


def test_los_motivos_de_omision_son_claros():
    e = montar()
    assert inicio(e).reason == "Interior 17 °C no es menor que 16 °C"
