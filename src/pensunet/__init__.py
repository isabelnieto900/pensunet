"""Pensunet: red de prerrequisitos de los pensum FCMN.

Grafo del pensum, indicadores topológicos y simulación Monte Carlo
del tiempo de grado para Física, Química, Biología y Matemáticas.
"""

__version__ = "0.1.1"

from pensunet.facade import SimuladorPensum

__all__ = ["SimuladorPensum", "__version__"]
