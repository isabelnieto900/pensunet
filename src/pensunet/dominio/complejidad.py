"""Complejidad curricular al estilo de Curricular Analytics.

Métricas de Heileman et al. (2018), *Curricular Analytics: A Framework
for Quantifying the Impact of Curricular Reforms and Pedagogical
Innovations* (arXiv:1811.09676), que usa la plataforma
curricularanalytics.org. Complementan los indicadores de Molontay et
al. (2020, sección II.B) y se calculan sobre el mismo DAG:

- factor de bloqueo b(v): asignaturas alcanzables desde v (es el mismo
  *blocking factor* de Molontay; se reutiliza ``factor_bloqueo``);
- factor de retraso d(v): número de asignaturas del camino más largo
  del DAG que pasa por v (cuenta vértices, no aristas);
- complejidad estructural h(v) = d(v) + b(v);
- complejidad curricular del plan: suma de h(v) sobre todas las
  asignaturas.

Cuanto más alta h(v), más semestres y más asignaturas arrastra una
reprobación de v. No usa tasas de aprobación: es una medida puramente
estructural del pensum.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from pensunet.dominio.indicadores import factor_bloqueo
from pensunet.dominio.red import RedPrerrequisitos


@dataclass(frozen=True)
class ComplejidadCurricular:
    """Bloqueo, retraso y complejidad estructural por asignatura."""

    bloqueo: dict[int, int]
    retraso: dict[int, int]
    complejidad_estructural: dict[int, int]
    complejidad_total: int

    def ranking(self, n: int = 10) -> list[tuple[int, int]]:
        """Las ``n`` asignaturas de mayor complejidad estructural.

        Empates por código ascendente, para que el orden sea estable.
        """
        ordenadas = sorted(
            self.complejidad_estructural.items(),
            key=lambda par: (-par[1], par[0]),
        )
        return ordenadas[: max(0, n)]


def factor_retraso(red: RedPrerrequisitos) -> dict[int, int]:
    """Vértices del camino más largo que contiene cada asignatura.

    Heileman et al. (2018), *delay factor*. Para cada v se suma el camino
    más largo que termina en v y el que sale de v, contando v una vez.
    Una asignatura aislada vale 1.
    """
    grafo = red.grafo
    orden = list(nx.topological_sort(grafo))
    hasta: dict[int, int] = {}
    for nodo in orden:
        previos = list(grafo.predecessors(nodo))
        hasta[int(nodo)] = 1 + max((hasta[int(p)] for p in previos), default=0)
    desde: dict[int, int] = {}
    for nodo in reversed(orden):
        siguientes = list(grafo.successors(nodo))
        desde[int(nodo)] = 1 + max((desde[int(s)] for s in siguientes), default=0)
    return {nodo: hasta[nodo] + desde[nodo] - 1 for nodo in hasta}


def calcular_complejidad(red: RedPrerrequisitos) -> ComplejidadCurricular:
    """Reúne bloqueo, retraso y complejidad estructural del plan."""
    bloqueo = factor_bloqueo(red)
    retraso = factor_retraso(red)
    estructural = {nodo: bloqueo[nodo] + retraso[nodo] for nodo in retraso}
    return ComplejidadCurricular(
        bloqueo=bloqueo,
        retraso=retraso,
        complejidad_estructural=estructural,
        complejidad_total=int(sum(estructural.values())),
    )
