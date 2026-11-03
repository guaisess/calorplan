# Versión: 2026.11.2
"""Alta de la integración: una sola instancia y sin pasos."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .core import settings as ajustes


class CalorplanConfigFlow(ConfigFlow, domain=ajustes.DOMAIN):
    """Flujo de configuración: crea la entrada directamente."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Crea la entrada (la configuración se importa después por servicio)."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self.async_create_entry(title=ajustes.NOMBRE, data={})
