"""Contrato de reglas por programa académico.

Pensunet está pensado para toda la Universidad Distrital. El núcleo
(sección II.A de Molontay et al., 2020) confía en el extracto de
prerrequisitos. Las correcciones locales —materias no ofrecidas, aristas
que el SIU no cargó, slots genéricos— son propias de cada carrera y las
valida quien conoce ese plan. No son reglas universales.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TablasAnalisis:
    """Pensum, prerrequisitos y tasas listos para el análisis / simulación."""

    pensum: pd.DataFrame
    prerrequisitos: pd.DataFrame
    tasas: pd.DataFrame
    notas: tuple[str, ...]
    excluidos: frozenset[int]


class ReglasCarrera(ABC):
    """Estrategia de preparación del grafo para un programa concreto.

    Cada implementación documenta qué corrige y por qué. Otras carreras
    (p. ej. matemáticas, biología, química) pueden empezar con
    ``ReglasSoloExtracto`` hasta tener revisión experta, varios planes o
    reglas de homologación propias.
    """

    @property
    @abstractmethod
    def codigo_programa(self) -> str:
        """Identificador corto del programa (p. ej. ``fisica``)."""

    @abstractmethod
    def preparar(
        self,
        pensum: pd.DataFrame,
        prerrequisitos: pd.DataFrame,
        tasas: pd.DataFrame,
    ) -> TablasAnalisis:
        """Devuelve tablas de análisis sin mutar los DataFrames de entrada."""


class ReglasSoloExtracto(ReglasCarrera):
    """No corrige el extracto: el grafo es el CSV tal cual.

    Sirve como valor por defecto institucional cuando no hay quien valide
    reglas locales, o para auditar el dato crudo.
    """

    def __init__(self, codigo_programa: str = "extracto") -> None:
        self._codigo = codigo_programa

    @property
    def codigo_programa(self) -> str:
        return self._codigo

    def preparar(
        self,
        pensum: pd.DataFrame,
        prerrequisitos: pd.DataFrame,
        tasas: pd.DataFrame,
    ) -> TablasAnalisis:
        notas = (
            f"Programa {self._codigo}: se confía en el extracto de "
            "prerrequisitos sin correcciones locales.",
        )
        return TablasAnalisis(
            pensum=pensum.copy().reset_index(drop=True),
            prerrequisitos=prerrequisitos.copy().reset_index(drop=True),
            tasas=tasas.copy().reset_index(drop=True),
            notas=notas,
            excluidos=frozenset(),
        )


class FabricaReglas:
    """Elige la estrategia de reglas sin acoplar la fachada a Física."""

    @staticmethod
    def crear(programa: str) -> ReglasCarrera:
        """Devuelve reglas para ``fisica`` o ``extracto`` (y aliases)."""
        clave = programa.strip().lower()
        if clave in {"fisica", "física"}:
            from pensunet.dominio.reglas_fisica import ReglasFisica

            return ReglasFisica()
        if clave in {"extracto", "csv", "solo_extracto"}:
            return ReglasSoloExtracto()
        raise ValueError(
            f"No hay reglas registradas para el programa {programa!r}. "
            "Use 'fisica' o 'extracto'. Otras carreras de Ciencias "
            "(matemáticas, biología, química) se registran cuando exista "
            "revisión experta de su plan."
        )
