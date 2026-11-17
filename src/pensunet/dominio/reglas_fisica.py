"""Reglas locales del programa de Física (validación experta).

Las correcciones están en ``data/reference/ajustes_prerrequisitos.csv``
(filas ``fisica``); esta clase solo fija el programa. Los CSV del SGA se
conservan sin cambios.
"""

from __future__ import annotations

import pandas as pd

from pensunet.dominio.reglas import ReglasDocumentadas, TablasAnalisis


class ReglasFisica(ReglasDocumentadas):
    """Correcciones del plan de Física documentadas por quien cursa el programa."""

    def __init__(self) -> None:
        super().__init__("fisica")


def preparar_tablas_analisis(
    pensum: pd.DataFrame,
    prerrequisitos: pd.DataFrame,
    tasas: pd.DataFrame,
) -> TablasAnalisis:
    """Atajo compatible con la etapa 2: aplica ``ReglasFisica``."""
    return ReglasFisica().preparar(pensum, prerrequisitos, tasas)
