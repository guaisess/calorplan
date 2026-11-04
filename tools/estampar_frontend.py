# Versión: 2026.11.10
"""Estampa `?v=<versión>` en los imports relativos del panel (evita módulos viejos en la caché).

Home Assistant sirve los ficheros del panel sin `Cache-Control`, y el navegador reutiliza los
módulos antiguos tras una actualización. Con la versión en cada import, un módulo nuevo es una
URL nueva. Ejecutar tras cambiar la versión:  python tools/estampar_frontend.py
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FRONTEND = RAIZ / "custom_components" / "calorplan" / "frontend"
SETTINGS = RAIZ / "custom_components" / "calorplan" / "core" / "settings.py"
IMPORT_RELATIVO = re.compile(r"""(\b(?:from|import)\s+)(["'])(\./[A-Za-z0-9_\-]+\.js)(?:\?v=[^"']*)?\2""")


def version() -> str:
    """Versión de la aplicación (VERSION en settings.py)."""
    return re.search(r'^VERSION = "([^"]+)"', SETTINGS.read_text(encoding="utf-8"), re.M).group(1)


def estampar(texto: str, ver: str) -> str:
    """Devuelve el texto con todos los imports relativos versionados."""
    return IMPORT_RELATIVO.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}?v={ver}{m.group(2)}", texto)


def main() -> None:
    ver = version()
    cambiados = 0
    for fichero in sorted(FRONTEND.glob("*.js")):
        original = fichero.read_text(encoding="utf-8")
        nuevo = estampar(original, ver)
        if nuevo != original:
            fichero.write_text(nuevo, encoding="utf-8")
            cambiados += 1
    print(f"Versión {ver}: {cambiados} fichero(s) actualizados")


if __name__ == "__main__":
    main()
