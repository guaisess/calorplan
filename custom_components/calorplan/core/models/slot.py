# Versión: 2026.11.2
"""Tramo horario de una habitación."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any

from .. import settings as ajustes
from .errors import ConfigError
from .notify import NotifyConfig


def _numero_opcional(valor: Any, nombre: str) -> float | None:
    """Convierte un valor opcional a número o lanza ConfigError."""
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ConfigError(f"'{nombre}' debe ser un número")
    return float(valor)


def _entero(valor: Any, nombre: str, minimo: int, maximo: int) -> int:
    """Valida un entero dentro de un rango."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ConfigError(f"'{nombre}' debe ser un entero")
    if not minimo <= valor <= maximo:
        raise ConfigError(f"'{nombre}' debe estar entre {minimo} y {maximo}")
    return valor


def parsear_hora(texto: Any, nombre: str) -> time:
    """Convierte «HH:MM» en `time` o lanza ConfigError."""
    try:
        return datetime.strptime(str(texto), ajustes.FORMATO_HORA).time()
    except ValueError as err:
        raise ConfigError(f"'{nombre}' debe tener formato HH:MM") from err


@dataclass
class Slot:
    """Tramo: días, hora de inicio, fin (o duración), consigna y condiciones."""

    id: str
    name: str
    start: time
    days: list[int]
    setpoint: float | None = None
    end: time | None = None
    duration_minutes: int | None = None
    enabled: bool = True
    retry_off_minutes: int = ajustes.REINTENTO_APAGADO_MINUTOS_DEFECTO
    outdoor_below: float | None = None
    indoor_below: float | None = None
    notify: NotifyConfig | None = None
    notify_on_skip: bool = False

    @property
    def inicio_minutos(self) -> int:
        """Minutos desde las 00:00 hasta el inicio."""
        return self.start.hour * 60 + self.start.minute

    @property
    def duracion_minutos(self) -> int:
        """Duración efectiva en minutos (fin <= inicio cruza la medianoche)."""
        if self.duration_minutes is not None:
            return self.duration_minutes
        assert self.end is not None  # garantizado por la validación
        fin = self.end.hour * 60 + self.end.minute
        diferencia = fin - self.inicio_minutos
        if diferencia <= 0:
            diferencia += ajustes.MINUTOS_DIA
        return diferencia

    def intervalos_semana(self) -> list[tuple[int, int]]:
        """Intervalos (inicio, duración) en minutos de la semana."""
        return [(d * ajustes.MINUTOS_DIA + self.inicio_minutos, self.duracion_minutos)
                for d in sorted(set(self.days))]

    def solapa_con(self, otro: "Slot") -> bool:
        """Indica si dos tramos coinciden en algún instante de la semana."""
        semana = ajustes.MINUTOS_SEMANA
        for a, la in self.intervalos_semana():
            for b, lb in otro.intervalos_semana():
                if (b - a) % semana < la or (a - b) % semana < lb:
                    return True
        return False

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "Slot":
        """Crea el tramo desde un diccionario validando sus campos."""
        if not isinstance(datos, dict):
            raise ConfigError("Un tramo debe ser un objeto")
        id_ = str(datos.get("id", "")).strip()
        if not id_:
            raise ConfigError("Un tramo necesita 'id'")
        dias = datos.get("days", list(ajustes.DIAS_SEMANA))
        if (not isinstance(dias, list) or not dias
                or any(isinstance(d, bool) or d not in ajustes.DIAS_SEMANA for d in dias)):
            raise ConfigError(f"Tramo '{id_}': 'days' debe ser una lista de días 0-6")
        tiene_fin = datos.get("end") is not None
        tiene_duracion = datos.get("duration_minutes") is not None
        if tiene_fin == tiene_duracion:
            raise ConfigError(f"Tramo '{id_}': indique 'end' o 'duration_minutes', pero no ambos")
        duracion = None
        if tiene_duracion:
            duracion = _entero(datos["duration_minutes"], "duration_minutes",
                               1, ajustes.MINUTOS_MAX_DURACION)
        condiciones = datos.get("conditions") or {}
        if not isinstance(condiciones, dict):
            raise ConfigError(f"Tramo '{id_}': 'conditions' debe ser un objeto")
        return cls(
            id=id_,
            name=str(datos.get("name", id_)),
            start=parsear_hora(datos.get("start"), "start"),
            days=sorted(set(dias)),
            setpoint=_numero_opcional(datos.get("setpoint"), "setpoint"),
            end=parsear_hora(datos["end"], "end") if tiene_fin else None,
            duration_minutes=duracion,
            enabled=bool(datos.get("enabled", True)),
            retry_off_minutes=_entero(
                datos.get("retry_off_minutes", ajustes.REINTENTO_APAGADO_MINUTOS_DEFECTO),
                "retry_off_minutes", 0, ajustes.MINUTOS_MAX_REINTENTO),
            outdoor_below=_numero_opcional(condiciones.get("outdoor_below"), "outdoor_below"),
            indoor_below=_numero_opcional(condiciones.get("indoor_below"), "indoor_below"),
            notify=NotifyConfig.from_dict(datos.get("notify")),
            notify_on_skip=bool(datos.get("notify_on_skip", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serializa el tramo."""
        datos: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "days": list(self.days),
            "start": self.start.strftime(ajustes.FORMATO_HORA),
            "setpoint": self.setpoint,
            "retry_off_minutes": self.retry_off_minutes,
            "conditions": {"outdoor_below": self.outdoor_below,
                           "indoor_below": self.indoor_below},
            "notify": self.notify.to_dict() if self.notify else None,
            "notify_on_skip": self.notify_on_skip,
        }
        if self.end is not None:
            datos["end"] = self.end.strftime(ajustes.FORMATO_HORA)
        else:
            datos["duration_minutes"] = self.duration_minutes
        return datos
