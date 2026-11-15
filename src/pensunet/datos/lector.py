"""Contrato de lectura de datos, independiente del origen."""

from abc import ABC, abstractmethod

import pandas as pd


class LectorDatos(ABC):
    """Origen de las tres tablas que alimentan el modelo.

    Sección II.A de Molontay et al. (2020): el pensum aporta los nodos y
    los prerrequisitos aportan las aristas. Ecuación (7): la tasa de una
    asignatura se estima con inscritos y aprobados.
    """

    @abstractmethod
    def leer_pensum(self) -> pd.DataFrame:
        """Devuelve el pensum con los nombres internos de columna.

        Sección II.A: cada fila es un nodo del grafo dirigido.
        """

    @abstractmethod
    def leer_prerequisitos(self) -> pd.DataFrame:
        """Devuelve las aristas de prerrequisito.

        Sección II.A: hay una arista de i a j cuando i es prerrequisito
        de j (M_ij = 1 en la matriz de adyacencia del artículo).
        """

    @abstractmethod
    def leer_tasas_aprobacion(self) -> pd.DataFrame:
        """Devuelve las tasas agregadas por asignatura.

        Ecuación (7): la probabilidad estimada es el cociente entre
        quienes aprueban la asignatura y quienes la inscriben.
        """
