# Versión: 2026.11.2
"""Carga el núcleo como paquete `calorplan_core` sin ejecutar la integración.

El `__init__.py` de la integración importa Home Assistant; el núcleo es puro
Python, así que se carga aparte con `importlib`.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NUCLEO = RAIZ / "custom_components" / "calorplan" / "core"
NOMBRE_PAQUETE = "calorplan_core"


def _cargar_nucleo() -> None:
    """Registra el núcleo en `sys.modules` como paquete de nivel superior."""
    if NOMBRE_PAQUETE in sys.modules:
        return
    spec = importlib.util.spec_from_file_location(
        NOMBRE_PAQUETE, NUCLEO / "__init__.py", submodule_search_locations=[str(NUCLEO)])
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[NOMBRE_PAQUETE] = modulo
    spec.loader.exec_module(modulo)


_cargar_nucleo()
