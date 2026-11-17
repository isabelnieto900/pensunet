"""Pensunet: red de prerrequisitos de los pensum FCMN.

Implementación original de Molontay et al. (2020). La sección II
(grafo del pensum e indicadores topológicos) está operativa para
Física, Química, Biología y Matemáticas. La simulación Monte Carlo
de la sección III.B queda esbozada.
"""

__version__ = "0.1.0"

from pensunet.facade import SimuladorPensum

__all__ = ["SimuladorPensum", "__version__"]
