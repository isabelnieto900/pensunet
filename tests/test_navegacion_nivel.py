"""Nivel de navegación, clave_carrera y agregaciones de facultad."""

from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("streamlit")

from pensunet.datos.privacidad import UMBRAL_MIN_INSCRITOS
from pensunet.ui.compartido import (
    CLAVE_FACULTAD,
    clave_carrera,
    materias_compartidas,
    nivel,
    top_menor_aprobacion_facultad,
)


def test_nivel_y_clave_en_facultad(monkeypatch):
    monkeypatch.setitem(
        __import__("streamlit").session_state,
        "selector_programa",
        CLAVE_FACULTAD,
    )
    # session_state en bare mode puede no persistir; usamos un stub simple.
    import streamlit as st

    st.session_state.clear()
    st.session_state["selector_programa"] = CLAVE_FACULTAD
    assert nivel() == "facultad"
    assert clave_carrera() is None


def test_nivel_y_clave_en_carrera():
    import streamlit as st

    st.session_state.clear()
    st.session_state["selector_programa"] = "fisica"
    assert nivel() == "carrera"
    assert clave_carrera() == "fisica"


def test_top_menor_aprobacion_facultad_respeta_supresion():
    top = top_menor_aprobacion_facultad(15)
    assert len(top) <= 15
    assert not top.empty
    assert (top["n_inscritos"] >= UMBRAL_MIN_INSCRITOS).all()
    assert top["tasa_aprobacion"].notna().all()
    assert set(top["clave"]).issubset({"fisica", "quimica", "biologia", "matematicas"})


def test_materias_compartidas_tienen_al_menos_dos_carreras():
    df = materias_compartidas()
    assert not df.empty
    assert (df["n_carreras"] >= 2).all()
    # Si hay tasa, debe cumplir el umbral de inscritos.
    con_tasa = df.loc[df["tasa_agregada"].notna()]
    if not con_tasa.empty:
        assert (con_tasa["n_inscritos"] >= UMBRAL_MIN_INSCRITOS).all()
    assert isinstance(df, pd.DataFrame)
