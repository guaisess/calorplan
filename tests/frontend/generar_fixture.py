# Versión: 2026.11.5
"""Genera `overview.fixture.json` con el código real del núcleo.

Uso:  python tests/frontend/generar_fixture.py
El test `test_overview_contract.py` falla si el formato de la API cambia y este
fichero no se ha regenerado, así el frontend se prueba siempre contra datos reales.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "tests"))

import conftest  # noqa: E402,F401  (carga el núcleo como `calorplan_core`)
from calorplan_core.engine.overview import OverviewBuilder  # noqa: E402
from calorplan_core.models import Plan  # noqa: E402
from fakes import FakeState, instante  # noqa: E402

FIXTURE = Path(__file__).with_name("overview.fixture.json")

ESTADOS = {
    "sensor.temperatura_exterior": "8", "sensor.temperatura_porche": "9",
    "sensor.dormitorio_temperatura": "15", "sensor.dormitorio_temperatura_2": "17",
    "climate.calefaccion_dormitorio": "off", "switch.calefaccion_despacho_enchufe": "off",
    "switch.toallero_bano": "on", "sensor.despacho_temperatura": "18",
    "sensor.bano_temperatura": "18",
}
ULTIMOS = {"dormitorio": {
    "time": "2026-11-02T06:00:00+01:00", "room_id": "dormitorio", "room": "Dormitorio",
    "slot_id": "madrugada", "slot": "Madrugada", "event": "start", "action": "on",
    "code": "dry_run", "reason": "Modo sombra: habría hecho «on» (Condiciones cumplidas)",
    "setpoint": 20.0, "outdoor": 8.0, "indoor": 15.0, "simulated": True}}


def construir() -> dict:
    """Resumen del plan de ejemplo un lunes a las 06:30."""
    datos = json.loads((RAIZ / "examples" / "config_ejemplo.json").read_text(encoding="utf-8"))
    return OverviewBuilder(Plan.from_dict(datos), FakeState(ESTADOS)).build(
        instante("2026-11-02", "06:30"), ULTIMOS)


if __name__ == "__main__":
    FIXTURE.write_text(json.dumps(construir(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Escrito {FIXTURE}")
