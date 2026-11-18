"""Supresión de celdas pequeñas en datos agregados (OATI)."""

from __future__ import annotations

import pandas as pd

UMBRAL_MIN_INSCRITOS = 10


def suprimir_celdas_pequenas(
    df: pd.DataFrame,
    umbral: int = UMBRAL_MIN_INSCRITOS,
) -> pd.DataFrame:
    """Oculta tasas con pocos inscritos sin modificar el DataFrame original.

    Cuando ``n_inscritos < umbral``, pone ``tasa_aprobacion`` y ``n_aprobados``
    en NaN y añade ``sin_dato_suficiente=True``. El resto queda intacto.
    """
    if "n_inscritos" not in df.columns:
        raise ValueError("La tabla debe tener la columna n_inscritos.")
    salida = df.copy()
    inscritos = pd.to_numeric(salida["n_inscritos"], errors="coerce")
    mascara = inscritos.isna() | (inscritos < int(umbral))
    if "tasa_aprobacion" in salida.columns:
        salida.loc[mascara, "tasa_aprobacion"] = pd.NA
    if "n_aprobados" in salida.columns:
        salida.loc[mascara, "n_aprobados"] = pd.NA
    salida["sin_dato_suficiente"] = mascara.fillna(True).astype(bool)
    return salida
