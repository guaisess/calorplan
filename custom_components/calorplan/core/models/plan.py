# Versión: 2026.11.2
"""Plan completo: configuración global y habitaciones."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .. import settings as ajustes
from .config import Config
from .errors import ConfigError
from .notify import NotifyConfig
from .room import Room


@dataclass
class Plan:
    """Raíz del modelo de datos (lo que se guarda en el almacén)."""

    config: Config = field(default_factory=Config)
    rooms: list[Room] = field(default_factory=list)

    def room(self, room_id: str) -> Room | None:
        """Devuelve la habitación con ese id, o None."""
        return next((r for r in self.rooms if r.id == room_id), None)

    def _comprobar_canales(self, aviso: NotifyConfig | None, donde: str) -> None:
        """Verifica que los canales referenciados existen."""
        if aviso is None:
            return
        for canal in aviso.channels:
            if self.config.canal(canal) is None:
                raise ConfigError(f"{donde}: el canal '{canal}' no existe")

    def validar(self) -> None:
        """Validación global: ids únicos y canales referenciados existentes."""
        ids = [r.id for r in self.rooms]
        if len(ids) != len(set(ids)):
            raise ConfigError("Ids de habitación repetidos")
        self._comprobar_canales(self.config.default_notify, "Aviso por defecto")
        for sala in self.rooms:
            sala.validar()
            self._comprobar_canales(sala.notify, f"Habitación '{sala.id}'")
            for tramo in sala.slots:
                self._comprobar_canales(tramo.notify, f"Tramo '{sala.id}/{tramo.id}'")

    @classmethod
    def from_dict(cls, datos: dict[str, Any] | None) -> "Plan":
        """Crea el plan desde un diccionario y lo valida."""
        if datos is None:
            return cls()
        if not isinstance(datos, dict):
            raise ConfigError("La configuración debe ser un objeto")
        version = datos.get("version", ajustes.SCHEMA_VERSION)
        if version != ajustes.SCHEMA_VERSION:
            raise ConfigError(f"Versión de esquema no soportada: {version}")
        plan = cls(
            config=Config.from_dict(datos.get("global")),
            rooms=[Room.from_dict(r) for r in datos.get("rooms", [])],
        )
        plan.validar()
        return plan

    def to_dict(self) -> dict[str, Any]:
        """Serializa el plan completo."""
        return {
            "version": ajustes.SCHEMA_VERSION,
            "global": self.config.to_dict(),
            "rooms": [r.to_dict() for r in self.rooms],
        }
