"""Contrato de reglas por programa académico.

Pensunet está pensado para toda la Universidad Distrital. El núcleo
(sección II.A de Molontay et al., 2020) confía en el extracto de
prerrequisitos. Las correcciones locales —materias no ofrecidas, aristas
que el SGA no cargó, slots genéricos— son propias de cada carrera y las
valida quien conoce ese plan. No son reglas universales.

Las correcciones viven como datos en
``data/reference/ajustes_prerrequisitos.csv`` (una fila por ajuste, con
justificación). ``ReglasCarrera`` es el punto de extensión: la fachada
solo conoce el contrato y ``FabricaReglas`` elige la implementación.
"""

from __future__ import annotations

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

    Cada implementación documenta qué corrige y por qué. Un programa sin
    revisión experta puede usar ``ReglasSoloExtracto``.
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


class ReglasDocumentadas(ReglasCarrera):
    """Aplica las filas de ``ajustes_prerrequisitos.csv`` del programa.

    Cada fila trae acción (agregar, excluir nodo o arista, documentar) y
    justificación; los CSV del SGA no se reescriben.
    """

    def __init__(self, codigo_programa: str) -> None:
        self._codigo = codigo_programa.strip().lower()

    @property
    def codigo_programa(self) -> str:
        return self._codigo

    def preparar(
        self,
        pensum: pd.DataFrame,
        prerrequisitos: pd.DataFrame,
        tasas: pd.DataFrame,
    ) -> TablasAnalisis:
        from pensunet.datos.ajustes import aplicar_ajustes

        resultado = aplicar_ajustes(pensum, prerrequisitos, self._codigo)
        ids_antes = {int(valor) for valor in pensum["id_asignatura"]}
        ids_despues = {int(valor) for valor in resultado.pensum["id_asignatura"]}
        return TablasAnalisis(
            pensum=resultado.pensum.reset_index(drop=True),
            prerrequisitos=resultado.prerrequisitos.reset_index(drop=True),
            tasas=tasas.copy().reset_index(drop=True),
            notas=tuple(resultado.notas),
            excluidos=frozenset(ids_antes - ids_despues),
        )


class FabricaReglas:
    """Elige la estrategia de reglas sin acoplar la fachada a una carrera."""

    @staticmethod
    def crear(programa: str) -> ReglasCarrera:
        """Reglas documentadas para un programa FCMN, o ``extracto``."""
        from pensunet.datos.programas import PROGRAMAS

        clave = programa.strip().lower()
        if clave in {"fisica", "física"}:
            from pensunet.dominio.reglas_fisica import ReglasFisica

            return ReglasFisica()
        if clave in PROGRAMAS:
            return ReglasDocumentadas(clave)
        if clave in {"extracto", "csv", "solo_extracto"}:
            return ReglasSoloExtracto()
        conocidos = ", ".join(sorted(PROGRAMAS))
        raise ValueError(
            f"No hay reglas registradas para el programa {programa!r}. "
            f"Use uno de: {conocidos} o 'extracto'."
        )
