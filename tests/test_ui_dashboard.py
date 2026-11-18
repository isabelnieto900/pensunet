"""Carga de páginas del dashboard con AppTest (dos niveles)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest

from pensunet.datos.programas import PROGRAMAS
from pensunet.ui.compartido import CLAVE_FACULTAD

_APP = str(Path(__file__).resolve().parents[1] / "src" / "pensunet" / "ui" / "app.py")
_TIMEOUT = 180

_PAGINAS_FACULTAD = (
    "facultad",
    "materias_facultad",
    "acerca",
)
_PAGINAS_CARRERA = (
    "resumen",
    "red",
    "materias",
    "tiempo_grado",
)


def _apptest_modulo(modulo: str, selector: str) -> AppTest:
    def _script() -> None:
        import importlib

        import streamlit as st

        from pensunet.ui.estilo import inyectar_estilo

        st.set_page_config(layout="wide")
        inyectar_estilo()
        nombre = st.session_state["_pagina_modulo"]
        mod = importlib.import_module(f"pensunet.ui.app_pages.{nombre}")
        mod.mostrar()

    at = AppTest.from_function(_script, default_timeout=_TIMEOUT)
    at.session_state["selector_programa"] = selector
    at.session_state["modo_oscuro"] = False
    at.session_state["_pagina_modulo"] = modulo
    at.run()
    return at


@pytest.mark.parametrize("modulo", _PAGINAS_FACULTAD)
def test_paginas_facultad_cargan(modulo: str):
    at = _apptest_modulo(modulo, CLAVE_FACULTAD)
    assert not at.exception


@pytest.mark.parametrize("clave", sorted(PROGRAMAS))
@pytest.mark.parametrize("modulo", _PAGINAS_CARRERA)
def test_paginas_carrera_cargan(clave: str, modulo: str):
    at = _apptest_modulo(modulo, clave)
    assert not at.exception


def test_entrypoint_panorama_facultad():
    at = AppTest.from_file(_APP, default_timeout=_TIMEOUT)
    at.session_state["selector_programa"] = CLAVE_FACULTAD
    at.session_state["modo_oscuro"] = False
    at.run()
    assert not at.exception


@pytest.mark.parametrize("clave", sorted(PROGRAMAS))
def test_entrypoint_resumen_por_carrera(clave: str):
    at = AppTest.from_file(_APP, default_timeout=_TIMEOUT)
    at.session_state["selector_programa"] = clave
    at.session_state["modo_oscuro"] = False
    at.run()
    assert not at.exception
