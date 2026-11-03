# Versión: 2026.11.2
"""Configuración de avisos: canales y modo de aviso."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .. import settings as ajustes
from .errors import ConfigError


@dataclass
class Channel:
    """Canal de aviso (por ahora, un servicio `notify.*`)."""

    id: str
    service: str
    type: str = ajustes.CANAL_TIPO_NOTIFY
    # Plantillas propias del canal (acción -> texto); opcionales
    templates: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "Channel":
        """Crea el canal desde un diccionario validando sus campos."""
        if not isinstance(datos, dict):
            raise ConfigError("Un canal debe ser un objeto")
        id_ = str(datos.get("id", "")).strip()
        servicio = str(datos.get("service", "")).strip()
        tipo = datos.get("type", ajustes.CANAL_TIPO_NOTIFY)
        if not id_:
            raise ConfigError("Un canal necesita 'id'")
        if tipo not in ajustes.CANAL_TIPOS:
            raise ConfigError(f"Tipo de canal no válido: {tipo}")
        if not servicio:
            raise ConfigError(f"El canal '{id_}' necesita 'service'")
        plantillas = datos.get("templates") or {}
        if not isinstance(plantillas, dict):
            raise ConfigError(f"Las plantillas del canal '{id_}' deben ser un objeto")
        return cls(id=id_, service=servicio, type=tipo,
                   templates={str(k): str(v) for k, v in plantillas.items()})

    def to_dict(self) -> dict[str, Any]:
        """Serializa el canal."""
        datos: dict[str, Any] = {"id": self.id, "type": self.type, "service": self.service}
        if self.templates:
            datos["templates"] = dict(self.templates)
        return datos


@dataclass
class NotifyConfig:
    """Modo de aviso (ninguno/encendido/apagado/ambos) y canales elegidos."""

    mode: str = ajustes.AVISO_DEFECTO
    channels: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, datos: dict[str, Any] | None) -> "NotifyConfig | None":
        """Crea la configuración; `None` significa «heredar»."""
        if datos is None:
            return None
        if not isinstance(datos, dict):
            raise ConfigError("'notify' debe ser un objeto o null")
        modo = datos.get("mode", ajustes.AVISO_DEFECTO)
        if modo not in ajustes.MODOS_AVISO:
            raise ConfigError(f"Modo de aviso no válido: {modo}")
        canales = datos.get("channels", [])
        if not isinstance(canales, list):
            raise ConfigError("'channels' debe ser una lista")
        return cls(mode=modo, channels=[str(c) for c in canales])

    def to_dict(self) -> dict[str, Any]:
        """Serializa la configuración."""
        return {"mode": self.mode, "channels": list(self.channels)}
