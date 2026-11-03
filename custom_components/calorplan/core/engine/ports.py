# Versión: 2026.11.2
"""Puertos (interfaces abstractas) que el motor necesita del exterior.

Los adaptadores reales viven en `ha/adapters.py`; los tests usan falsos.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class StatePort(ABC):
    """Lectura del estado de las entidades."""

    @abstractmethod
    def get_float(self, entity_id: str) -> float | None:
        """Valor numérico de la entidad, o None si no es numérico/disponible."""

    @abstractmethod
    def get_state(self, entity_id: str) -> str | None:
        """Estado en texto, o None si la entidad no existe."""

    @abstractmethod
    def is_state(self, entity_id: str, state: str) -> bool:
        """Indica si la entidad está exactamente en ese estado."""

    @abstractmethod
    def is_available(self, entity_id: str) -> bool:
        """Indica si la entidad existe y no está «unavailable/unknown»."""


class ActuatorPort(ABC):
    """Órdenes a los dispositivos."""

    @abstractmethod
    async def climate_heat(self, entity_id: str, hvac_mode: str, temperature: float | None) -> None:
        """Pone el climate en modo calor y fija la temperatura objetivo (si hay)."""

    @abstractmethod
    async def climate_off(self, entity_id: str) -> None:
        """Apaga el climate."""

    @abstractmethod
    async def switch_set(self, entity_id: str, on: bool) -> None:
        """Enciende o apaga un switch."""


class NotifyPort(ABC):
    """Envío de avisos."""

    @abstractmethod
    async def send(self, service: str, title: str, message: str) -> None:
        """Envía un mensaje mediante un servicio `notify.*`."""


class ClockPort(ABC):
    """Reloj y esperas (permite simular el tiempo en los tests)."""

    @abstractmethod
    def now(self) -> datetime:
        """Instante actual con zona horaria."""

    @abstractmethod
    async def sleep(self, seconds: float) -> None:
        """Espera sin bloquear."""


class EventPort(ABC):
    """Publicación de eventos y registro de decisiones."""

    @abstractmethod
    def fire(self, event_type: str, data: dict[str, Any]) -> None:
        """Dispara un evento en el bus del sistema."""

    @abstractmethod
    def record(self, data: dict[str, Any]) -> None:
        """Guarda la decisión (para entidades e historial)."""
