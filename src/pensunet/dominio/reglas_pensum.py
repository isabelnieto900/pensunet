"""Compatibilidad: reexporta las reglas de Física.

El punto de extensión nuevo es ``ReglasCarrera`` / ``FabricaReglas`` en
``reglas.py``. Este módulo evita romper imports antiguos.
"""

from pensunet.dominio.reglas import TablasAnalisis
from pensunet.dominio.reglas_fisica import (
    ARISTAS_CONFIRMADAS,
    IDIOMAS_MODELO,
    NO_OFRECIDAS,
    SLOTS_GENERICOS_LINEA,
    ReglasFisica,
    preparar_tablas_analisis,
)

__all__ = [
    "ARISTAS_CONFIRMADAS",
    "IDIOMAS_MODELO",
    "NO_OFRECIDAS",
    "SLOTS_GENERICOS_LINEA",
    "ReglasFisica",
    "TablasAnalisis",
    "preparar_tablas_analisis",
]
