"""Supresión de celdas pequeñas en tasas agregadas."""

from __future__ import annotations

import pandas as pd

from pensunet.datos.privacidad import UMBRAL_MIN_INSCRITOS, suprimir_celdas_pequenas


def test_suprimir_oculta_filas_con_n_menor_al_umbral():
    df = pd.DataFrame(
        {
            "id_asignatura": [1, 2, 3],
            "n_inscritos": [5, 10, 40],
            "n_aprobados": [2, 8, 30],
            "tasa_aprobacion": [0.4, 0.8, 0.75],
        }
    )
    salida = suprimir_celdas_pequenas(df, umbral=UMBRAL_MIN_INSCRITOS)
    assert pd.isna(salida.loc[0, "tasa_aprobacion"])
    assert pd.isna(salida.loc[0, "n_aprobados"])
    assert bool(salida.loc[0, "sin_dato_suficiente"]) is True
    assert float(salida.loc[1, "tasa_aprobacion"]) == 0.8
    assert float(salida.loc[2, "tasa_aprobacion"]) == 0.75
    assert bool(salida.loc[1, "sin_dato_suficiente"]) is False


def test_suprimir_no_modifica_el_dataframe_original():
    df = pd.DataFrame(
        {
            "id_asignatura": [1],
            "n_inscritos": [3],
            "n_aprobados": [1],
            "tasa_aprobacion": [0.33],
        }
    )
    original = df.copy()
    _ = suprimir_celdas_pequenas(df, umbral=10)
    pd.testing.assert_frame_equal(df, original)


def test_suprimir_exige_columna_inscritos():
    import pytest

    with pytest.raises(ValueError, match="n_inscritos"):
        suprimir_celdas_pequenas(pd.DataFrame({"tasa_aprobacion": [0.5]}))
