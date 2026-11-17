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

    ``n_censurados`` cuenta trayectorias que no se graduaron dentro del
    tope ``max_semestres`` (o agotaron electivas): su tiempo queda en el
    tope o en el semestre de corte, para que la simulación no falle.
    """

    tiempos: tuple[int, ...]
    media: float
    desviacion: float
    n_censurados: int = 0
    tope_semestres: int | None = None


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
