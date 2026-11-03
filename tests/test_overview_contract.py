# Versión: 2026.11.5
"""El fixture del frontend debe coincidir con lo que genera el núcleo."""
from __future__ import annotations

import json

from frontend.generar_fixture import FIXTURE, construir


def test_el_fixture_del_frontend_esta_actualizado():
    esperado = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert construir() == esperado, (
        "El formato del resumen cambió: ejecuta `python tests/frontend/generar_fixture.py`")
