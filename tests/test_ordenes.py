# Versión: 2026.11.12
"""Órdenes a los dispositivos: no se envía lo ya aplicado, se reintenta con espera y se comprueba el estado."""
from __future__ import annotations

import asyncio
import copy
import json
from types import SimpleNamespace

from calorplan_core import settings as aj
from calorplan_core.engine import Notifier, PlannedEvent, Runner
from calorplan_core.models import Plan
from fakes import (FakeActuator, FakeClock, FakeEvents, FakeNotify, FakeState,
                   RAIZ, instante)

DATOS = json.loads((RAIZ / "examples" / "config_ejemplo.json").read_text(encoding="utf-8"))
CLIMA = "climate.calefaccion_dormitorio"
BLOQUEO = "switch.calefaccion_dormitorio_bloqueo_infantil"
TOALLERO = "switch.toallero_bano"
EXT = ["sensor.temperatura_exterior", "sensor.temperatura_porche"]
INT = ["sensor.dormitorio_temperatura", "sensor.dormitorio_temperatura_2"]


def montar(estados=None, atributos=None, setpoint=None, cambios=None):
    datos = copy.deepcopy(DATOS)
    datos["global"]["shadow_mode"] = False
    if setpoint is not None:
        datos["rooms"][0]["slots"][0]["setpoint"] = setpoint
    if cambios:
        cambios(datos)
    plan = Plan.from_dict(datos)
    estado = FakeState({EXT[0]: "8", EXT[1]: "9", INT[0]: "15", INT[1]: "15", CLIMA: "off", BLOQUEO: "off",
                        TOALLERO: "off", "sensor.bano_temperatura": "18", **(estados or {})})
    estado.atributos.update(atributos or {})
    reloj = FakeClock(instante("2026-11-02", "06:00"))
    envio, eventos = FakeNotify(), FakeEvents()
    act = FakeActuator(estado)
    runner = Runner(plan, estado, act, Notifier(plan, envio, reloj), reloj, eventos)
    return SimpleNamespace(plan=plan, estado=estado, act=act, envio=envio, eventos=eventos, reloj=reloj, runner=runner)


def inicio(e, sala="dormitorio", tramo="madrugada", forzar=False):
    return asyncio.run(e.runner.handle(PlannedEvent(instante("2026-11-02", "06:00"), "start", sala, tramo), forzar=forzar))


def fin(e, hora="07:00"):
    e.reloj.fijar(instante("2026-11-02", hora))
    return asyncio.run(e.runner.handle(PlannedEvent(instante("2026-11-02", hora), "end", "dormitorio", "madrugada")))


def reevaluar(e, hora):
    e.reloj.fijar(instante("2026-11-02", hora))
    return asyncio.run(e.runner.reevaluate("dormitorio"))


def llamadas(e, tipo):
    return [c for c in e.act.llamadas if c[0] == tipo]


# --- Camino normal: una orden por paso, sin esperas ----------------------------------------------------------------
def test_encendido_normal_una_orden_por_paso_y_sin_esperas():
    e = montar()
    assert inicio(e).action == "on"
    assert e.act.llamadas == [("heat", CLIMA, "heat"), ("temp", CLIMA, 20.0), ("switch", BLOQUEO, True)]
    assert e.reloj.esperas == []  # se comprueba al momento: no hay que esperar


def test_si_todo_ya_esta_aplicado_no_se_envia_ninguna_orden():
    e = montar(estados={CLIMA: "heat", BLOQUEO: "on"}, atributos={CLIMA: {"temperature": 20.0}})
    assert inicio(e).action == "on"  # se registra y avisa igualmente
    assert e.act.llamadas == [] and e.reloj.esperas == []


def test_solo_se_envia_lo_que_falta():
    e = montar(estados={CLIMA: "heat", BLOQUEO: "on"}, atributos={CLIMA: {"temperature": 23.0}})  # ya en modo calor, objetivo viejo
    inicio(e)
    assert e.act.llamadas == [("temp", CLIMA, 20.0)]  # ni modo ni bloqueo


def test_lanzar_dos_veces_el_mismo_tramo_no_repite_las_ordenes():
    e = montar()
    inicio(e, forzar=True)
    primeras = list(e.act.llamadas)
    inicio(e, forzar=True)  # segunda vez: todo ya está aplicado
    assert e.act.llamadas == primeras


# --- El caso real de Principal: la nube de Tuya rechaza la temperatura -------------------------------------------
def test_si_falla_la_temperatura_se_reintenta_solo_la_temperatura():
    e = montar(atributos={CLIMA: {"temperature": 23.0}})
    e.act.fallos_temp = 1  # el primer intento es rechazado y no se aplica
    reg = inicio(e)
    assert reg.action == "on"
    assert len(llamadas(e, "heat")) == 1  # el modo no se repite
    assert len(llamadas(e, "temp")) == 2
    assert e.reloj.esperas == [aj.ORDEN_ESPERA_SEGUNDOS]
    assert e.estado.atributos[CLIMA]["temperature"] == 20.0 and e.envio.enviados[0][2].startswith("🔥")


def test_si_el_servicio_da_error_pero_la_orden_se_aplico_no_se_reenvia():
    e = montar(atributos={CLIMA: {"temperature": 23.0}})
    e.act.fallos_temp = 1
    e.act.aplica_pese_al_error = True  # Tuya: error, pero el termostato sí cambió
    assert inicio(e).action == "on"
    assert len(llamadas(e, "temp")) == 1  # tras el error se comprobó el estado y no hizo falta reenviar
    e2 = montar()
    e2.act.fallos_modo = 1
    e2.act.aplica_pese_al_error = True
    assert inicio(e2).action == "on" and len(llamadas(e2, "heat")) == 1


def test_si_nunca_se_aplica_se_agotan_los_intentos_y_es_un_error_con_un_solo_aviso():
    e = montar(atributos={CLIMA: {"temperature": 23.0}})
    e.act.ignorar_temp = True
    reg = inicio(e)
    assert (reg.action, reg.code) == ("error", aj.COD_NO_DISPONIBLE)
    assert f"no se confirmó tras {aj.ORDEN_REINTENTOS} intentos" in reg.reason and "temperatura objetivo" in reg.reason
    assert len(llamadas(e, "temp")) == aj.ORDEN_REINTENTOS and len(llamadas(e, "heat")) == 1
    assert len(e.envio.enviados) == 1 and "Problema" in e.envio.enviados[0][2]
    assert e.runner.salas_pendientes() == {"dormitorio"}  # queda para la siguiente reevaluación


def test_la_reevaluacion_completa_solo_lo_que_falta_sin_repetir_el_modo():
    e = montar(atributos={CLIMA: {"temperature": 23.0}})
    e.act.ignorar_temp = True
    inicio(e)
    e.act.llamadas.clear()
    e.act.ignorar_temp = False  # el dispositivo se recupera
    registros = reevaluar(e, "06:10")
    assert [r.action for r in registros] == ["on"]
    assert e.act.llamadas == [("temp", CLIMA, 20.0), ("switch", BLOQUEO, True)]  # el modo ya estaba en heat
    assert e.runner.salas_pendientes() == set()


def test_los_errores_repetidos_de_la_reevaluacion_no_vuelven_a_avisar():
    e = montar(atributos={CLIMA: {"temperature": 23.0}})
    e.act.ignorar_temp = True
    inicio(e)
    for minuto in ("06:10", "06:20", "06:30"):
        assert [r.action for r in reevaluar(e, minuto)] == ["error"]
    assert len(e.envio.enviados) == 1  # solo el primer error avisó
    assert e.runner.salas_pendientes() == {"dormitorio"}


def test_un_fallo_total_del_modo_no_manda_la_temperatura():
    e = montar()
    e.act.ignorar_modo = True
    assert inicio(e).action == "error"
    assert llamadas(e, "temp") == [] and len(llamadas(e, "heat")) == aj.ORDEN_REINTENTOS


# --- Temperatura: tolerancia y no verificable -----------------------------------------------------------------------
def test_si_el_termostato_redondea_no_se_reenvia():
    e = montar(setpoint=20.5, atributos={CLIMA: {"temperature": 23.0}})
    e.act.redondeo = 1.0  # pide 20,5 y el dispositivo dice 20
    inicio(e)
    assert len(llamadas(e, "temp")) == 1  # 20 está dentro de la tolerancia de 20,5


def test_si_la_temperatura_no_se_puede_verificar_se_envia_una_sola_vez():
    e = montar()  # la entidad no informa del atributo «temperature»
    e.act.ignorar_temp = True  # y la orden no deja rastro
    assert inicio(e).action == "on"
    assert len(llamadas(e, "temp")) == 1 and e.reloj.esperas == []


# --- Bloqueo infantil ---------------------------------------------------------------------------------------------------
def test_el_bloqueo_no_se_manda_si_ya_esta_en_su_sitio():
    e = montar(estados={BLOQUEO: "on"})
    inicio(e)
    assert llamadas(e, "switch") == []


def test_un_fallo_del_bloqueo_no_rompe_el_encendido_ni_inunda_de_ordenes():
    e = montar()
    original = e.act.switch_set

    async def falla(entidad, on):
        e.act.llamadas.append(("switch", entidad, on))
        raise RuntimeError("bloqueo no disponible")
    e.act.switch_set = falla
    assert inicio(e).action == "on"
    assert len(llamadas(e, "switch")) == aj.ORDEN_REINTENTOS  # reintentos acotados, y sigue adelante
    e.act.switch_set = original


# --- Switch (toalleros, enchufes) ---------------------------------------------------------------------------------------
def inicio_toallero(e):
    return asyncio.run(e.runner.handle(PlannedEvent(instante("2026-11-02", "06:00"), "start", "toallero", "manana")))


def test_switch_ya_encendido_no_recibe_orden():
    e = montar(estados={TOALLERO: "on"})
    assert inicio_toallero(e).action == "on" and e.act.llamadas == []


def test_switch_con_un_fallo_se_reintenta_una_vez():
    e = montar()
    e.act.ignorar_modo = False
    original = e.act.switch_set
    intentos = {"n": 0}

    async def primera_falla(entidad, on):
        intentos["n"] += 1
        if intentos["n"] == 1:
            e.act.llamadas.append(("switch", entidad, on))
            raise RuntimeError("fallo puntual")
        await original(entidad, on)
    e.act.switch_set = primera_falla
    assert inicio_toallero(e).action == "on" and intentos["n"] == 2


def test_switch_que_no_responde_es_un_error_tras_los_intentos():
    e = montar()

    async def no_hace_nada(entidad, on):
        e.act.llamadas.append(("switch", entidad, on))
    e.act.switch_set = no_hace_nada
    reg = inicio_toallero(e)
    assert reg.action == "error" and len(llamadas(e, "switch")) == aj.ORDEN_REINTENTOS


# --- Apagado ---------------------------------------------------------------------------------------------------------------
def test_el_apagado_no_reenvia_si_el_error_de_la_nube_si_lo_aplico():
    e = montar(estados={CLIMA: "heat"})

    async def off_con_error(entidad):
        e.act.llamadas.append(("climate_off", entidad))
        e.estado.estados[entidad] = "off"  # se aplica…
        raise RuntimeError("The Tuya cloud rejected the command")  # …pero el servicio da error
    e.act.climate_off = off_con_error
    reg = fin(e)
    assert reg.action == "off"
    assert llamadas(e, "climate_off") == [("climate_off", CLIMA)]  # una sola orden: el reintento comprobó antes


def test_apagar_igualmente_envia_la_primera_orden_aunque_conste_apagado():
    def sin_solo_si_encendido(d):
        d["rooms"][0]["actuator"]["off_only_if_heating"] = False
    e = montar(cambios=sin_solo_si_encendido)  # CLIMA ya está en off
    assert fin(e).action == "off"
    assert llamadas(e, "climate_off") == [("climate_off", CLIMA)]


def test_ciclo_completo_cuenta_las_ordenes_justas():
    e = montar()
    inicio(e)
    fin(e)
    # encender: modo + temperatura + bloqueo; apagar: una orden
    assert [c[0] for c in e.act.llamadas] == ["heat", "temp", "switch", "climate_off"]
