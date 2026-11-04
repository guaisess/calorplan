# Versión: 2026.11.18
"""Publica una release de GitHub con las notas de su sección del CHANGELOG.

Uso:  python tools/publicar_release.py [--dry-run] [--version AAAA.MM.V]

Comprueba antes de publicar que: la versión coincide en `settings.py` y `manifest.json`, existe su
sección en el CHANGELOG, el árbol git está limpio, el commit está subido a `origin/main` y la release
no existe ya. La release se crea sobre el commit actual y queda marcada como la última.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# --- Configuración (sin valores fijos en el código) ---------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
SETTINGS = RAIZ / "custom_components" / "calorplan" / "core" / "settings.py"
MANIFIESTO = RAIZ / "custom_components" / "calorplan" / "manifest.json"
CHANGELOG = RAIZ / "CHANGELOG.md"
REPOSITORIO = "guaisess/calorplan"
RAMA = "main"
REMOTO = "origin"
TITULO = "Calorplan {version}"
SECCION = r"^## {version}\n(.*?)(?=^## |\Z)"


def version_codigo() -> str:
    """Versión de la aplicación (VERSION en settings.py)."""
    return re.search(r'^VERSION = "([^"]+)"', SETTINGS.read_text(encoding="utf-8"), re.M).group(1)


def version_manifiesto() -> str:
    """Versión declarada en manifest.json."""
    return json.loads(MANIFIESTO.read_text(encoding="utf-8"))["version"]


def notas_changelog(texto: str, version: str) -> str | None:
    """Notas de la sección `## <versión>` del CHANGELOG (None si no existe o está vacía)."""
    m = re.search(SECCION.format(version=re.escape(version)), texto, re.S | re.M)
    notas = m.group(1).strip() if m else ""
    return notas + "\n" if notas else None


def _git(*args: str) -> str:
    """Ejecuta git en la raíz del proyecto y devuelve su salida."""
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def _gh(*args: str) -> subprocess.CompletedProcess:
    """Ejecuta gh y devuelve el resultado completo."""
    return subprocess.run(["gh", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8")


def comprobar(version: str) -> list[str]:
    """Devuelve la lista de problemas que impiden publicar (vacía si todo está bien)."""
    problemas = []
    if version_codigo() != version or version_manifiesto() != version:
        problemas.append(f"La versión no coincide: settings={version_codigo()}, manifest={version_manifiesto()}, pedida={version}")
    if notas_changelog(CHANGELOG.read_text(encoding="utf-8"), version) is None:
        problemas.append(f"El CHANGELOG no tiene sección «## {version}» con contenido")
    if _git("status", "--porcelain"):
        problemas.append("Hay cambios sin confirmar en git")
    _git("fetch", REMOTO, RAMA)
    if _git("rev-parse", "HEAD") != _git("rev-parse", f"{REMOTO}/{RAMA}"):
        problemas.append(f"HEAD no coincide con {REMOTO}/{RAMA} (falta subir o actualizar)")
    if _gh("release", "view", version, "--repo", REPOSITORIO).returncode == 0:
        problemas.append(f"La release {version} ya existe")
    return problemas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", default=None, help="versión a publicar (por defecto la del código)")
    parser.add_argument("--dry-run", action="store_true", help="solo comprobar y mostrar las notas")
    args = parser.parse_args()
    version = args.version or version_codigo()
    problemas = comprobar(version)
    if problemas:
        print("No se publica:\n- " + "\n- ".join(problemas))
        return 1
    notas = notas_changelog(CHANGELOG.read_text(encoding="utf-8"), version)
    if args.dry_run:
        print(f"Todo correcto para {version}. Notas:\n\n{notas}")
        return 0
    with tempfile.TemporaryDirectory() as carpeta:
        fichero = Path(carpeta) / "notas.md"
        fichero.write_text(notas, encoding="utf-8")
        r = _gh("release", "create", version, "--repo", REPOSITORIO, "--target", _git("rev-parse", "HEAD"),
                "--title", TITULO.format(version=version), "--notes-file", str(fichero), "--latest")
    print((r.stdout + r.stderr).strip())
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
