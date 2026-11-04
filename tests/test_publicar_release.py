# Versión: 2026.11.18
"""Tests de las partes puras de tools/publicar_release.py."""
from __future__ import annotations

import importlib.util

from fakes import RAIZ

_spec = importlib.util.spec_from_file_location("publicar_release", RAIZ / "tools" / "publicar_release.py")
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)

TEXTO = "# Registro\n\n## 2026.11.2\n\n- Dos\n- Más\n\n## 2026.11.1\n\n- Uno\n"


def test_extrae_las_notas_de_su_seccion():
    assert pr.notas_changelog(TEXTO, "2026.11.2") == "- Dos\n- Más\n"
    assert pr.notas_changelog(TEXTO, "2026.11.1") == "- Uno\n"


def test_version_inexistente_o_vacia():
    assert pr.notas_changelog(TEXTO, "2026.11.9") is None
    assert pr.notas_changelog("## 2026.11.3\n\n## 2026.11.2\n- x\n", "2026.11.3") is None


def test_el_punto_de_la_version_no_es_comodin():
    assert pr.notas_changelog("## 2026x11.2\n- x\n", "2026.11.2") is None


def test_las_versiones_del_proyecto_coinciden():
    assert pr.version_codigo() == pr.version_manifiesto()
    assert pr.notas_changelog(pr.CHANGELOG.read_text(encoding="utf-8"), pr.version_codigo())
