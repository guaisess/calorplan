# Versión: 2026.11.2
"""Tests del ejecutor (inicio, fin, reintento, verificación, sombra, ausencia)."""
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


def montar(datos=None, hora="06:00", sombra=False, estados=None, reloj=None):
    """Monta el motor con puertos falsos. Por defecto: frío fuera y dentro."""
    datos = copy.deepcopy(datos or DATOS)
    datos["global"]["shadow_mode"] = sombra
    plan = Plan.from_dict(datos)
    estado = FakeState({EXT[0]: "8", EXT[1]: "9", INT[0]: "15", INT[1]: "17",
                        "sensor.bano_temperatura": "18", CLIMA: "off", BLOQUEO: "off",
                        TOALLERO: "off", "sensor.despacho_temperatura": "18",
                        "switch.calefaccion_despacho_enchufe": "off", **(estados or {})})
    reloj = reloj or FakeClock(instante("2026-11-02", hora))
    envio, eventos = FakeNotify(), FakeEvents()
    actuador = FakeActuator(estado)
    runner = Runner(plan, estado, actuador, Notifier(plan, envio, reloj), reloj, eventos)
    return SimpleNamespace(plan=plan, estado=estado, actuador=actuador, envio=envio,
                           eventos=eventos, reloj=reloj, runner=runner)


def ev(tipo, sala="dormitorio", tramo="madrugada"):
    return PlannedEvent(instante("2026-11-02", "06:00"), tipo, sala, tramo)


def correr(e, evento, **kw):
    return asyncio.run(e.runner.handle(evento, **kw))


# --- Inicio -------------------------------------------------------------------
def test_inicio_enciende_climate_con_temperatura_objetivo_bloqueo_y_aviso():
    e = montar()
    reg = correr(e, ev("start"))
    assert reg.action == "on" and reg.code == aj.COD_OK
    assert e.actuador.llamadas == [("heat", CLIMA, "heat", 20.0), ("switch", BLOQUEO, True)]
    assert len(e.envio.enviados) == 1 and "ACTIVADA" in e.envio.enviados[0][2]
    assert e.eventos.eventos[0][0] == aj.EVENTO_ACCION
    assert e.eventos.registros[0]["action"] == "on"


def test_inicio_de_switch():
    e = montar(hora="05:50")
    reg = correr(e, ev("start", "toallero", "manana"))
    assert reg.action == "on"
    assert e.actuador.llamadas == [("switch", TOALLERO, True)]


def test_bloqueo_infantil_al_encender_configurable():
    for accion, esperado in [("unlock", [("heat", CLIMA, "heat", 20.0), ("switch", BLOQUEO, False)]),
                             ("none", [("heat", CLIMA, "heat", 20.0)])]:
        datos = copy.deepcopy(DATOS)
        datos["rooms"][0]["actuator"]["child_lock_on_start"] = accion
        e = montar(datos)
        correr(e, ev("start"))
        assert e.actuador.llamadas == esperado


def test_inicio_omitido_por_condicion_no_avisa_por_defecto():
    e = montar(estados={EXT[0]: "17", EXT[1]: "18"})
    reg = correr(e, ev("start"))
    assert (reg.action, reg.code, reg.reason) == ("skip", aj.COD_EXTERIOR_ALTO, "Exterior 17 ≥ 10")
    assert e.actuador.llamadas == [] and e.envio.enviados == []
    assert len(e.eventos.registros) == 1  # pero queda registrado


def test_inicio_omitido_avisa_si_notify_on_skip():
    e = montar(estados={INT[0]: "20", INT[1]: "20"})
    e.plan.room("dormitorio").slot("madrugada").notify_on_skip = True
    correr(e, ev("start"))
    assert len(e.envio.enviados) == 1 and "No se enciende" in e.envio.enviados[0][2]


def test_sensor_sin_datos_es_un_error_con_aviso_siempre():
    e = montar(estados={EXT[0]: "unavailable", EXT[1]: "unavailable"})
    reg = correr(e, ev("start"))
    assert (reg.action, reg.code) == ("error", aj.COD_EXTERIOR_NO_DISPONIBLE)
    assert e.actuador.llamadas == [] and len(e.envio.enviados) == 1


def test_modo_ausencia_omite_inicios():
    e = montar()
    e.plan.config.away_mode = True
    reg = correr(e, ev("start"))
    assert (reg.action, reg.code) == ("skip", aj.COD_AUSENCIA)
    assert e.actuador.llamadas == []


def test_habitacion_o_tramo_deshabilitado_omite():
    e = montar()
    e.plan.room("dormitorio").enabled = False
    assert correr(e, ev("start")).code == aj.COD_HABITACION_DESHABILITADA
    e.plan.room("dormitorio").enabled = True
    e.plan.room("dormitorio").slot("madrugada").enabled = False
    assert correr(e, ev("start")).code == aj.COD_TRAMO_DESHABILITADO
    assert e.actuador.llamadas == []


def test_inicio_forzado_ignora_condiciones_ausencia_y_deshabilitado():
    e = montar(estados={EXT[0]: "30", EXT[1]: "30"})
    e.plan.config.away_mode = True
    e.plan.room("dormitorio").enabled = False
    reg = correr(e, ev("start"), forzar=True)
    assert (reg.action, reg.code) == ("on", aj.COD_FORZADO)
    assert e.actuador.llamadas[0][0] == "heat"


def test_fallo_del_actuador_al_encender_es_un_error():
    e = montar()

    async def falla(*a):
        raise RuntimeError("sin conexión")
    e.actuador.climate_heat = falla
    reg = correr(e, ev("start"))
    assert reg.action == "error" and "sin conexión" in reg.reason
    assert len(e.envio.enviados) == 1


# --- Fin y reintento -----------------------------------------------------------
def test_fin_apaga_verifica_y_avisa():
    e = montar(hora="07:00", estados={CLIMA: "heat"})
    reg = correr(e, ev("end"))
    assert reg.action == "off" and e.estado.estados[CLIMA] == "off"
    assert e.actuador.llamadas == [("climate_off", CLIMA)]  # bloqueo al apagar: nada
    assert e.reloj.esperas == [aj.VERIFICAR_ESPERA_SEGUNDOS]
    assert len(e.envio.enviados) == 1 and "DESACTIVADA" in e.envio.enviados[0][2]


def test_bloqueo_infantil_al_apagar_configurable():
    datos = copy.deepcopy(DATOS)
    datos["rooms"][0]["actuator"]["child_lock_on_end"] = "unlock"
    e = montar(datos, hora="07:00", estados={CLIMA: "heat", BLOQUEO: "on"})
    correr(e, ev("end"))
    assert e.actuador.llamadas == [("climate_off", CLIMA), ("switch", BLOQUEO, False)]


def test_fin_si_ya_esta_apagado_no_hace_nada_ni_avisa():
    e = montar(hora="07:00", estados={CLIMA: "off"})
    assert correr(e, ev("end")) is None
    assert e.actuador.llamadas == [] and e.envio.enviados == [] and e.eventos.registros == []


def test_fin_sin_off_only_if_heating_apaga_igualmente():
    datos = copy.deepcopy(DATOS)
    datos["rooms"][0]["actuator"]["off_only_if_heating"] = False
    e = montar(datos, hora="07:00", estados={CLIMA: "off"})
    assert correr(e, ev("end")).action == "off"
    assert e.actuador.llamadas == [("climate_off", CLIMA)]


def test_fin_de_switch():
    e = montar(hora="07:35", estados={TOALLERO: "on"})
    reg = correr(e, ev("end", "toallero", "manana"))
    assert reg.action == "off" and e.estado.estados[TOALLERO] == "off"


def test_apagado_no_verificado_reintenta_y_da_error_con_aviso():
    e = montar(hora="07:00", estados={CLIMA: "heat"})
    e.actuador.ignorar_apagado = True
    reg = correr(e, ev("end"))
    assert reg.action == "error" and reg.code == aj.COD_APAGADO_NO_VERIFICADO
    assert [c for c in e.actuador.llamadas if c[0] == "climate_off"] == [("climate_off", CLIMA)] * 3
    assert len(e.envio.enviados) == 1 and "Problema" in e.envio.enviados[0][2]


def test_excepcion_al_apagar_cuenta_como_intento_y_se_recupera():
    e = montar(hora="07:00", estados={CLIMA: "heat"})
    e.actuador.fallos_apagado = 1
    reg = correr(e, ev("end"))
    assert reg.action == "off"
    assert len([c for c in e.actuador.llamadas if c[0] == "climate_off"]) == 2


def test_espera_a_que_el_actuador_este_disponible():
    class RelojQueRecupera(FakeClock):
        async def sleep(self, seconds):
            await super().sleep(seconds)
            if len(self.esperas) == 3:
                e.estado.estados[CLIMA] = "heat"  # vuelve a estar disponible
    e = montar(hora="07:00", estados={CLIMA: "unavailable"},
               reloj=RelojQueRecupera(instante("2026-11-02", "07:00")))
    # «unavailable» no cuenta como apagado: se espera, se apaga y se verifica
    reg = correr(e, ev("end"))
    assert reg.action == "off"
    assert e.reloj.esperas[:3] == [aj.DISPONIBILIDAD_SONDEO_SEGUNDOS] * 3


def test_actuador_que_nunca_vuelve_da_error_sin_ordenes():
    e = montar(hora="07:00", estados={CLIMA: "unavailable"})
    reg = correr(e, ev("end"))
    assert reg.action == "error" and e.actuador.llamadas == []
    sondeos = aj.DISPONIBILIDAD_TIMEOUT_SEGUNDOS // aj.DISPONIBILIDAD_SONDEO_SEGUNDOS
    assert len(e.reloj.esperas) == sondeos * 3  # 3 intentos esperando
    assert len(e.envio.enviados) == 1


def test_reintento_no_hace_nada_si_ya_esta_apagado():
    e = montar(hora="07:05", estados={CLIMA: "off"})
    assert correr(e, ev("retry")) is None and e.envio.enviados == []


def test_reintento_apaga_si_el_dispositivo_sigue_encendido():
    e = montar(hora="07:05", estados={CLIMA: "heat"})
    reg = correr(e, ev("retry"))
    assert reg.action == "off" and reg.kind == "retry"


def test_reintento_se_ignora_si_hay_otro_tramo_activo():
    datos = {"global": DATOS["global"], "rooms": [{
        "id": "h", "name": "H", "actuator": {"type": "switch", "entity_id": "switch.h"},
        "slots": [{"id": "a", "start": "08:00", "end": "09:00", "days": [0]},
                  {"id": "b", "start": "09:00", "end": "10:00", "days": [0]}]}]}
    e = montar(datos, hora="09:05", estados={"switch.h": "on"})
    assert correr(e, PlannedEvent(e.reloj.now(), "retry", "h", "a")) is None
    assert e.estado.estados["switch.h"] == "on"


def test_el_fin_actua_aunque_haya_modo_ausencia():
    e = montar(hora="07:00", estados={CLIMA: "heat"})
    e.plan.config.away_mode = True
    assert correr(e, ev("end")).action == "off"


# --- Modo sombra -----------------------------------------------------------------
def test_modo_sombra_no_actua_ni_avisa_pero_registra():
    e = montar(sombra=True)
    reg = correr(e, ev("start"))
    assert reg.simulated and reg.code == aj.COD_SIMULACION and reg.action == "on"
    assert "Modo sombra" in reg.reason
    assert e.actuador.llamadas == [] and e.envio.enviados == []
    tipo, datos = e.eventos.eventos[0]
    assert tipo == aj.EVENTO_ACCION and datos["code"] == aj.COD_SIMULACION


def test_modo_sombra_en_el_fin_y_en_omisiones():
    e = montar(hora="07:00", sombra=True, estados={CLIMA: "heat"})
    reg = correr(e, ev("end"))
    assert reg.simulated and reg.action == "off" and e.estado.estados[CLIMA] == "heat"
    e2 = montar(sombra=True, estados={EXT[0]: "30", EXT[1]: "30"})
    reg = correr(e2, ev("start"))
    assert reg.action == "skip" and reg.code == aj.COD_SIMULACION
    assert e.actuador.llamadas == [] and e2.envio.enviados == []


# --- Evento desconocido y catch-up --------------------------------------------------
def test_evento_de_tramo_inexistente_se_ignora():
    e = montar()
    assert correr(e, ev("start", "fantasma", "x")) is None
    assert correr(e, ev("start", "dormitorio", "x")) is None


def test_catch_up_evalua_el_tramo_activo():
    datos = copy.deepcopy(DATOS)
    datos["global"]["catch_up"] = "evaluate"
    e = montar(datos, hora="06:30")
    registros = asyncio.run(e.runner.catch_up())
    # A las 06:30 están activos el tramo del dormitorio y el del toallero (05:50-07:35)
    assert sorted((r.room_id, r.slot_id, r.action) for r in registros) == [
        ("dormitorio", "madrugada", "on"), ("toallero", "manana", "on")]
    assert ("heat", CLIMA, "heat", 20.0) in e.actuador.llamadas


def test_catch_up_ninguno_por_defecto():
    e = montar(hora="06:30")
    assert asyncio.run(e.runner.catch_up()) == []
    assert e.actuador.llamadas == []
