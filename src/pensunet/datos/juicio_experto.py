"""Tasas fijadas por juicio experto (p. ej. Trabajo de Grado).

Algunas asignaturas no tienen nota en el histórico agregado: la de
Trabajo de Grado la ponen director y evaluador fuera del SGA. Su p_i no
se inventa en el código: sale de ``data/reference/trabajo_de_grado.csv``,
con columna ``origen = juicio_experto`` y una justificación por fila.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pensunet.datos.programas import RUTA_TRABAJO_GRADO


def tasas_juicio_experto(programa: str, ruta: str | Path | None = None) -> pd.DataFrame:
    """Filas de tasas (esquema interno) fijadas por juicio experto.

    Devuelve ``id_asignatura``, ``nombre``, ``n_inscritos``,
    ``n_aprobados``, ``tasa_aprobacion`` y ``n_bajo``. Las filas sin tasa
    en el catálogo se omiten: no se completan con 0 ni con 1.
    """
    path = Path(ruta) if ruta is not None else RUTA_TRABAJO_GRADO
    columnas = [
        "id_asignatura",
        "nombre",
        "n_inscritos",
        "n_aprobados",
        "tasa_aprobacion",
        "n_bajo",
    ]
    if not path.is_file():
        return pd.DataFrame(columns=columnas)
    catalogo = pd.read_csv(path, encoding="utf-8")
    filas = catalogo.loc[
        (catalogo["programa"].map(lambda valor: str(valor).strip().lower()) == programa.lower())
        & catalogo["tasa_aprobacion"].notna()
    ]
    tasas = [float(valor) for valor in filas["tasa_aprobacion"]]
    if any(not 0.0 <= valor <= 1.0 for valor in tasas):
        raise ValueError(f"Tasa de juicio experto fuera de [0, 1] en {path}.")
    return pd.DataFrame(
        {
            "id_asignatura": filas["id_asignatura"].astype(int).to_list(),
            "nombre": filas["ds_nombre_asignatura"].astype(str).to_list(),
            "n_inscritos": 0,
            "n_aprobados": 0,
            "tasa_aprobacion": tasas,
            "n_bajo": True,
        },
        columns=columnas,
    )


def combinar_tasas(tasas: pd.DataFrame, expertas: pd.DataFrame) -> pd.DataFrame:
    """Agrega o reemplaza en ``tasas`` las filas fijadas por juicio experto."""
    if expertas.empty:
        return tasas.copy()
    ids = set(expertas["id_asignatura"].astype(int))
    base = tasas.loc[~tasas["id_asignatura"].astype(int).isin(ids)]
    return pd.concat([base, expertas], ignore_index=True)
