"""Compatibilidad: reexporta las reglas de Física.

El punto de extensión es ``ReglasCarrera`` / ``FabricaReglas`` en
``reglas.py``. Este módulo evita romper imports antiguos.
"""

from pensunet.dominio.reglas import TablasAnalisis
from pensunet.dominio.reglas_fisica import ReglasFisica, preparar_tablas_analisis

__all__ = [
    "ReglasFisica",
    "TablasAnalisis",
    "preparar_tablas_analisis",
]
