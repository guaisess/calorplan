# Versión: 2026.11.10
"""Todos los imports relativos del panel deben llevar la versión actual (evita la caché del navegador)."""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import estampar_frontend as est  # noqa: E402

IMPORT_CUALQUIERA = est.re.compile(r"""\b(?:from|import)\s+["'](\./[^"']+)["']""")


def test_los_imports_del_panel_llevan_la_version_actual():
    ver = est.version()
    sin_version = []
    for fichero in sorted(est.FRONTEND.glob("*.js")):
        for destino in IMPORT_CUALQUIERA.findall(fichero.read_text(encoding="utf-8")):
            if not destino.endswith(f".js?v={ver}"):
                sin_version.append(f"{fichero.name}: {destino}")
    assert not sin_version, (
        f"Imports sin la versión {ver}: {sin_version}. Ejecuta `python tools/estampar_frontend.py`")


def test_estampar_es_idempotente_y_reemplaza_versiones_viejas():
    base = 'import { a } from "./a.js";\nimport "./b.js?v=1.2.3";\nconst x = "./no-es-import.js";'
    una = est.estampar(base, "9.9.9")
    assert 'from "./a.js?v=9.9.9"' in una and 'import "./b.js?v=9.9.9"' in una
    assert 'const x = "./no-es-import.js";' in una  # no toca cadenas que no son imports
    assert est.estampar(una, "9.9.9") == una


def test_la_version_de_settings_y_del_manifest_coinciden():
    import json
    manifiesto = json.loads((est.FRONTEND.parent / "manifest.json").read_text(encoding="utf-8"))
    assert manifiesto["version"] == est.version()
