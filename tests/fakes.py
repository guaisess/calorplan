# Versión: 2026.11.12
"""Puertos falsos para los tests del motor."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from calorplan_core.engine.ports import (ActuatorPort, ClockPort, EventPort,
                                         NotifyPort, StatePort)
from calorplan_core.models import Plan

ZONA = ZoneInfo("Europe/Madrid")
RAIZ = Path(__file__).resolve().parent.parent


def cargar_plan(ruta: Path) -> Plan:
    """Carga un plan desde un fichero JSON."""
    return Plan.from_dict(json.loads(ruta.read_text(encoding="utf-8")))


def instante(dia: str, hora: str) -> datetime:
    """Construye un instante con zona horaria: instante('2026-11-02', '06:00')."""
    return datetime.fromisoformat(f"{dia}T{hora}:00").replace(tzinfo=ZONA)


class FakeState(StatePort):
    """Estados en un diccionario; `apagar_al_ordenar` simula el dispositivo."""

    def __init__(self, estados: dict[str, str] | None = None) -> None:
        self.estados: dict[str, str] = dict(estados or {})
        self.atributos: dict[str, dict] = {}  # entidad -> atributos (p. ej. temperature)

    def get_state(self, entity_id: str) -> str | None:
        return self.estados.get(entity_id)

    def get_float(self, entity_id: str) -> float | None:
        try:
            return float(self.estados[entity_id])
        except (KeyError, ValueError):
            return None

    def is_state(self, entity_id: str, state: str) -> bool:
        return self.estados.get(entity_id) == state

    def is_available(self, entity_id: str) -> bool:
        return self.estados.get(entity_id) not in (None, "unavailable", "unknown")

    def get_attribute(self, entity_id: str, name: str):
        return self.atributos.get(entity_id, {}).get(name)


class FakeActuator(ActuatorPort):
    """Registra las órdenes y, opcionalmente, actualiza el estado como un dispositivo real."""

    def __init__(self, state: FakeState) -> None:
        self.state = state
        self.llamadas: list[tuple] = []
        self.ignorar_apagado = False  # simula un dispositivo que no obedece
        self.fallos_apagado = 0  # nº de excepciones antes de funcionar
        self.fallos_modo = 0  # excepciones antes de aceptar el cambio de modo
        self.fallos_temp = 0  # excepciones antes de aceptar la temperatura
        self.aplica_pese_al_error = False  # como la nube de Tuya: da error pero la orden sí se aplica
        self.ignorar_modo = False  # la orden de modo no tiene efecto
        self.ignorar_temp = False  # la orden de temperatura no tiene efecto
        self.redondeo = None  # si se indica (p. ej. 1.0), el termostato redondea la temperatura

    async def climate_set_mode(self, entity_id, hvac_mode):
        self.llamadas.append(("heat", entity_id, hvac_mode))
        if self.fallos_modo > 0:
            self.fallos_modo -= 1
            if self.aplica_pese_al_error and not self.ignorar_modo:
                self.state.estados[entity_id] = hvac_mode
            raise RuntimeError("The Tuya cloud rejected the command")
        if not self.ignorar_modo:
            self.state.estados[entity_id] = hvac_mode

    async def climate_set_temperature(self, entity_id, temperature):
        self.llamadas.append(("temp", entity_id, temperature))
        aplicar = not self.ignorar_temp
        valor = round(temperature / self.redondeo) * self.redondeo if self.redondeo else temperature
        if self.fallos_temp > 0:
            self.fallos_temp -= 1
            if self.aplica_pese_al_error and aplicar:
                self.state.atributos.setdefault(entity_id, {})["temperature"] = valor
            raise RuntimeError("The Tuya cloud rejected the command")
        if aplicar:
            self.state.atributos.setdefault(entity_id, {})["temperature"] = valor

    async def climate_off(self, entity_id):
        self.llamadas.append(("climate_off", entity_id))
        await self._apagar(entity_id)

    async def switch_set(self, entity_id, on):
        self.llamadas.append(("switch", entity_id, on))
        if entity_id.startswith("switch.") and not entity_id.endswith("bloqueo_infantil"):
            if on:
                self.state.estados[entity_id] = "on"
            else:
                await self._apagar(entity_id)
        else:
            self.state.estados[entity_id] = "on" if on else "off"

    async def _apagar(self, entity_id):
        if self.fallos_apagado > 0:
            self.fallos_apagado -= 1
            raise RuntimeError("fallo simulado")
        if not self.ignorar_apagado:
            self.state.estados[entity_id] = "off"


class FakeNotify(NotifyPort):
    """Guarda los avisos enviados."""

    def __init__(self) -> None:
        self.enviados: list[tuple[str, str, str]] = []
        self.fallar_en: set[str] = set()

    async def send(self, service, title, message):
        if service in self.fallar_en:
            raise RuntimeError("canal caído")
        self.enviados.append((service, title, message))


class FakeClock(ClockPort):
    """Reloj controlable: `sleep` avanza el tiempo sin esperar."""

    def __init__(self, ahora: datetime) -> None:
        self._ahora = ahora
        self.esperas: list[float] = []

    def now(self) -> datetime:
        return self._ahora

    async def sleep(self, seconds):
        self.esperas.append(seconds)
        self._ahora += timedelta(seconds=seconds)

    def fijar(self, ahora: datetime) -> None:
        self._ahora = ahora


class FakeEvents(EventPort):
    """Guarda eventos y registros."""

    def __init__(self) -> None:
        self.eventos: list[tuple[str, dict]] = []
        self.registros: list[dict] = []

    def fire(self, event_type, data):
        self.eventos.append((event_type, data))

    def record(self, data):
        self.registros.append(data)
