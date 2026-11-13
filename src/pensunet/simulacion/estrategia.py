"""Interfaz intercambiable de la simulación del tiempo de grado."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd

from pensunet.dominio.escenario import Escenario
from pensunet.dominio.red import RedPrerrequisitos


@dataclass(frozen=True)
class ResultadoSimulacion:
    """Muestra del tiempo de grado y sus resúmenes.

    Ecuaciones (3) y (4) de Molontay et al. (2020): ``tiempos`` permite
    estimar p(x) = P(X = x) por frecuencias, y ``media`` estima E(X).
    """

    tiempos: tuple[int, ...]
    media: float
    desviacion: float


class EstrategiaSimulacion(ABC):
    """Algoritmo que aproxima la distribución del tiempo de grado.

    Ecuaciones (3) y (4) de Molontay et al. (2020). La fachada depende de
    esta interfaz, no de un algoritmo concreto, para poder sustituir el
    Monte Carlo de la sección III.B sin reescribir el resto.
    """

    @abstractmethod
    def simular(
        self,
        red: RedPrerrequisitos,
        tasas: pd.DataFrame,
        escenario: Escenario,
    ) -> ResultadoSimulacion:
        """Estima la distribución de X bajo los supuestos del escenario.

        Ecuaciones (3) y (4). ``tasas`` aporta la estimación de p_i de
        la ecuación (7).
        """
