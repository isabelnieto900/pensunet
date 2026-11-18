"""KPIs y agregaciones del dashboard."""

from __future__ import annotations

import pandas as pd

from pensunet.ui.compartido import tasa_ponderada


def test_tasa_ponderada_usa_inscritos_como_peso():
    df = pd.DataFrame(
        {
            "tasa_aprobacion": [1.0, 0.0],
            "n_inscritos": [90, 10],
            "sin_dato_suficiente": [False, False],
        }
    )
    assert abs(tasa_ponderada(df) - 0.9) < 1e-9


def test_tasa_ponderada_ignora_celdas_suprimidas():
    df = pd.DataFrame(
        {
            "tasa_aprobacion": [0.5, 1.0],
            "n_inscritos": [5, 20],
            "sin_dato_suficiente": [True, False],
        }
    )
    assert tasa_ponderada(df) == 1.0


def test_tasa_ponderada_vacia_devuelve_none():
    df = pd.DataFrame(
        {
            "tasa_aprobacion": [pd.NA],
            "n_inscritos": [0],
            "sin_dato_suficiente": [True],
        }
    )
    assert tasa_ponderada(df) is None
