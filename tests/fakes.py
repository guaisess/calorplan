# Versión: 2026.11.2
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


class FakeActuator(ActuatorPort):
    """Registra las órdenes y, opcionalmente, actualiza el estado como un dispositivo real."""

    def __init__(self, state: FakeState) -> None:
        self.state = state
        self.llamadas: list[tuple] = []
        self.ignorar_apagado = False  # simula un dispositivo que no obedece
        self.fallos_apagado = 0  # nº de excepciones antes de funcionar

    async def climate_heat(self, entity_id, hvac_mode, temperature):
        self.llamadas.append(("heat", entity_id, hvac_mode, temperature))
        self.state.estados[entity_id] = hvac_mode

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
