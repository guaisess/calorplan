# Versión: 2026.11.2
"""Errores del modelo de datos."""
from __future__ import annotations


class ConfigError(ValueError):
    """Configuración inválida (se lanza al validar o cargar datos)."""
