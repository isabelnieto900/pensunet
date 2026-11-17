"""Pensunet: red de prerrequisitos del pensum de Física.

Implementación original de Molontay et al. (2020). La sección II
(grafo e indicadores) y el Monte Carlo de la sección III.B están
operativos. La interfaz Streamlit vive en ``pensunet.ui``.
"""

__version__ = "0.1.0"

from pensunet.facade import SimuladorPensum

__all__ = ["SimuladorPensum", "__version__"]
