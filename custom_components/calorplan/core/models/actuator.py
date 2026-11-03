# Versión: 2026.11.2
"""Actuador de una habitación: un `climate` o un `switch`."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .. import settings as ajustes
from .errors import ConfigError


@dataclass
class Actuator:
    """Dispositivo que enciende y apaga la calefacción de una habitación."""

    type: str
    entity_id: str
    child_lock_switch: str | None = None
    child_lock_on_start: str = ajustes.BLOQUEO_AL_ENCENDER_DEFECTO
    child_lock_on_end: str = ajustes.BLOQUEO_AL_APAGAR_DEFECTO
    off_only_if_heating: bool = ajustes.APAGAR_SOLO_SI_ENCENDIDO_DEFECTO
    verify_attempts: int = ajustes.VERIFICAR_INTENTOS_DEFECTO
    hvac_mode_on: str = ajustes.HVAC_MODO_ENCENDIDO

    @property
    def estado_encendido(self) -> str:
        """Estado que indica «calentando» según el tipo de actuador."""
        if self.type == ajustes.TIPO_CLIMATE:
            return self.hvac_mode_on
        return ajustes.ESTADO_SWITCH_ENCENDIDO

    @property
    def estado_apagado(self) -> str:
        """Estado que indica «apagado» según el tipo de actuador."""
        if self.type == ajustes.TIPO_CLIMATE:
            return ajustes.HVAC_MODO_APAGADO
        return ajustes.ESTADO_SWITCH_APAGADO

    @property
    def tiene_bloqueo(self) -> bool:
        """Indica si se puede gestionar el bloqueo infantil."""
        return self.type == ajustes.TIPO_CLIMATE and bool(self.child_lock_switch)

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "Actuator":
        """Crea el actuador desde un diccionario validando sus campos."""
        if not isinstance(datos, dict):
            raise ConfigError("'actuator' debe ser un objeto")
        tipo = datos.get("type")
        if tipo not in ajustes.TIPOS_ACTUADOR:
            raise ConfigError(f"Tipo de actuador no válido: {tipo}")
        entidad = str(datos.get("entity_id", "")).strip()
        if not entidad.startswith(f"{tipo}."):
            raise ConfigError(f"La entidad '{entidad}' debe ser del dominio '{tipo}'")
        bloqueo = datos.get("child_lock_switch") or None
        if bloqueo is not None and not str(bloqueo).startswith("switch."):
            raise ConfigError(f"El bloqueo infantil '{bloqueo}' debe ser un switch")
        al_encender = datos.get("child_lock_on_start", ajustes.BLOQUEO_AL_ENCENDER_DEFECTO)
        al_apagar = datos.get("child_lock_on_end", ajustes.BLOQUEO_AL_APAGAR_DEFECTO)
        for valor in (al_encender, al_apagar):
            if valor not in ajustes.ACCIONES_BLOQUEO:
                raise ConfigError(f"Acción de bloqueo no válida: {valor}")
        intentos = datos.get("verify_attempts", ajustes.VERIFICAR_INTENTOS_DEFECTO)
        if not isinstance(intentos, int) or isinstance(intentos, bool) or intentos < 1:
            raise ConfigError("'verify_attempts' debe ser un entero >= 1")
        return cls(
            type=tipo,
            entity_id=entidad,
            child_lock_switch=str(bloqueo) if bloqueo else None,
            child_lock_on_start=al_encender,
            child_lock_on_end=al_apagar,
            off_only_if_heating=bool(
                datos.get("off_only_if_heating", ajustes.APAGAR_SOLO_SI_ENCENDIDO_DEFECTO)),
            verify_attempts=intentos,
            hvac_mode_on=str(datos.get("hvac_mode_on", ajustes.HVAC_MODO_ENCENDIDO)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serializa el actuador."""
        return {
            "type": self.type,
            "entity_id": self.entity_id,
            "child_lock_switch": self.child_lock_switch,
            "child_lock_on_start": self.child_lock_on_start,
            "child_lock_on_end": self.child_lock_on_end,
            "off_only_if_heating": self.off_only_if_heating,
            "verify_attempts": self.verify_attempts,
            "hvac_mode_on": self.hvac_mode_on,
        }
