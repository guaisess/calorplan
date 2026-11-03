# Versión: 2026.11.2
"""Configuración global: sensores exteriores, canales y políticas."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .. import settings as ajustes
from .errors import ConfigError
from .notify import Channel, NotifyConfig


@dataclass
class Config:
    """Ajustes comunes a todas las habitaciones."""

    outdoor_sensors: list[str] = field(default_factory=list)
    away_mode: bool = ajustes.MODO_AUSENCIA_DEFECTO
    shadow_mode: bool = ajustes.MODO_SOMBRA_DEFECTO
    unavailable_policy: str = ajustes.POLITICA_NO_DISPONIBLE_DEFECTO
    catch_up: str = ajustes.CATCH_UP_DEFECTO
    channels: list[Channel] = field(default_factory=list)
    default_notify: NotifyConfig = field(default_factory=NotifyConfig)
    # Plantillas globales (acción -> texto); se completan con las de `settings`
    templates: dict[str, str] = field(default_factory=dict)

    def canal(self, canal_id: str) -> Channel | None:
        """Devuelve el canal con ese id, o None."""
        return next((c for c in self.channels if c.id == canal_id), None)

    def plantilla(self, accion: str) -> str:
        """Plantilla global para una acción (con valor por defecto)."""
        return self.templates.get(accion) or ajustes.PLANTILLAS_DEFECTO.get(accion, "")

    @classmethod
    def from_dict(cls, datos: dict[str, Any] | None) -> "Config":
        """Crea la configuración global validando sus campos."""
        datos = datos or {}
        if not isinstance(datos, dict):
            raise ConfigError("'global' debe ser un objeto")
        politica = datos.get("unavailable_policy", ajustes.POLITICA_NO_DISPONIBLE_DEFECTO)
        if politica not in ajustes.POLITICAS_NO_DISPONIBLE:
            raise ConfigError(f"Política no válida: {politica}")
        catch_up = datos.get("catch_up", ajustes.CATCH_UP_DEFECTO)
        if catch_up not in ajustes.CATCH_UP_OPCIONES:
            raise ConfigError(f"Valor de catch_up no válido: {catch_up}")
        sensores = datos.get("outdoor_sensors", [])
        if not isinstance(sensores, list):
            raise ConfigError("'outdoor_sensors' debe ser una lista")
        canales = [Channel.from_dict(c) for c in datos.get("channels", [])]
        ids = [c.id for c in canales]
        if len(ids) != len(set(ids)):
            raise ConfigError("Ids de canal repetidos")
        plantillas = datos.get("templates") or {}
        if not isinstance(plantillas, dict):
            raise ConfigError("'templates' debe ser un objeto")
        aviso = NotifyConfig.from_dict(datos.get("default_notify")) or NotifyConfig()
        return cls(
            outdoor_sensors=[str(s) for s in sensores],
            away_mode=bool(datos.get("away_mode", ajustes.MODO_AUSENCIA_DEFECTO)),
            shadow_mode=bool(datos.get("shadow_mode", ajustes.MODO_SOMBRA_DEFECTO)),
            unavailable_policy=politica,
            catch_up=catch_up,
            channels=canales,
            default_notify=aviso,
            templates={str(k): str(v) for k, v in plantillas.items()},
        )

    def to_dict(self) -> dict[str, Any]:
        """Serializa la configuración global."""
        return {
            "outdoor_sensors": list(self.outdoor_sensors),
            "away_mode": self.away_mode,
            "shadow_mode": self.shadow_mode,
            "unavailable_policy": self.unavailable_policy,
            "catch_up": self.catch_up,
            "channels": [c.to_dict() for c in self.channels],
            "default_notify": self.default_notify.to_dict(),
            "templates": dict(self.templates),
        }
