"""Indicadores topológicos de la red de prerrequisitos."""

from dataclasses import dataclass

import networkx as nx

from pensunet.dominio.red import RedPrerrequisitos


@dataclass(frozen=True)
class IndicadoresTopologicos:
    """Bloqueo, posponimiento e intermediación de cada asignatura.

    Sección II.B y ecuación (1) de Molontay et al. (2020).
    ``repeticiones_sin_retraso`` es la k de la definición del factor de
    posponimiento: se puede reprobar la asignatura k veces sin alargar
    el grado, y el factor es 1/(k + 1).
    """

    factor_bloqueo: dict[int, int]
    factor_posponimiento: dict[int, float]
    intermediacion: dict[int, float]
    repeticiones_sin_retraso: dict[int, int]
    duracion_nominal: int


def factor_bloqueo(red: RedPrerrequisitos) -> dict[int, int]:
    """Cuenta los descendientes de cada asignatura.

    Sección II.B de Molontay et al. (2020), *blocking factor*: el factor
    de bloqueo es n si la asignatura tiene exactamente n descendientes.
    No es el grado de salida: también entran los descendientes indirectos.
    La propia asignatura no se cuenta.
    """
    return {int(nodo): len(nx.descendants(red.grafo, nodo)) for nodo in red.grafo}


def factor_posponimiento(
    red: RedPrerrequisitos,
    duracion: int | None = None,
) -> dict[int, float]:
    """Calcula el factor de posponimiento 1/(k + 1).

    Sección II.B de Molontay et al. (2020), *deferment factor*. k es el
    máximo de reprobaciones que todavía permiten graduarse en la duración
    nominal del plan. A la reprobación k + 1 el grado se alarga al menos
    un semestre. En el ejemplo del artículo, un factor 1/3 significa que
    se puede reprobar dos veces y a la tercera el grado aumenta.

    En esta red::

        s(v) = max(semestre del plan, nivel por prerrequisitos)
        d(v) = aristas del camino más largo que sale de v
        k(v) = max(0, T - s(v) - d(v))
        factor(v) = 1 / (k(v) + 1)

    T es la duración nominal. Cada arista hacia un descendiente exige un
    semestre adicional después de aprobar v. No se puede intentar v antes
    de s(v): el artículo, sección III, no permite cursar una asignatura
    antes del semestre recomendado ni antes de sus prerrequisitos.
    """
    _, holgura = _holgura(red, duracion)
    return {nodo: 1.0 / (k + 1) for nodo, k in holgura.items()}


def intermediacion(red: RedPrerrequisitos, normalizada: bool = False) -> dict[int, float]:
    """Calcula la intermediación de cada asignatura.

    Ecuación (1) de Molontay et al. (2020), sección II.B::

        b_v = suma_{s ≠ v, t ≠ v} de sigma_st(v) / sigma_st

    ``sigma_st`` es el número de caminos más cortos de s a t y
    ``sigma_st(v)`` cuántos de ellos pasan por v. Con ``normalizada``
    en falso se devuelve esa suma. La tabla III del artículo publica
    valores del orden de 10^-3, coherentes con dividir la ecuación (1)
    por (n - 1)(n - 2) en un grafo dirigido; ese es el resultado cuando
    ``normalizada`` es verdadero.
    """
    cruda = nx.betweenness_centrality(red.grafo, normalized=normalizada)
    return {int(nodo): float(valor) for nodo, valor in cruda.items()}


def calcular_indicadores(
    red: RedPrerrequisitos,
    duracion: int | None = None,
) -> IndicadoresTopologicos:
    """Reúne bloqueo, posponimiento e intermediación.

    Sección II.B y ecuación (1) de Molontay et al. (2020).
    """
    duracion_nominal, holgura = _holgura(red, duracion)
    return IndicadoresTopologicos(
        factor_bloqueo=factor_bloqueo(red),
        factor_posponimiento={nodo: 1.0 / (k + 1) for nodo, k in holgura.items()},
        intermediacion=intermediacion(red),
        repeticiones_sin_retraso=holgura,
        duracion_nominal=duracion_nominal,
    )


def _holgura(
    red: RedPrerrequisitos,
    duracion: int | None,
) -> tuple[int, dict[int, int]]:
    """Devuelve T y la k de cada asignatura. Sección II.B."""
    duracion_nominal = red.duracion_nominal if duracion is None else duracion
    profundidad = _profundidad_posterior(red.grafo)
    holgura: dict[int, int] = {}
    for nodo in red.grafo:
        nivel = int(red.grafo.nodes[nodo]["nivel"])
        semestre = red.grafo.nodes[nodo].get("semestre")
        inicio = nivel if semestre is None else max(int(semestre), nivel)
        holgura[int(nodo)] = max(0, duracion_nominal - inicio - profundidad[nodo])
    return duracion_nominal, holgura


def _profundidad_posterior(grafo: nx.DiGraph) -> dict[int, int]:
    """Aristas del camino más largo que sale de cada nodo.

    Sección II.B: esos semestres adicionales hay que reservarlos para
    los descendientes antes de cerrar la duración nominal.
    """
    profundidad = {int(nodo): 0 for nodo in grafo}
    for nodo in reversed(list(nx.topological_sort(grafo))):
        sucesores = list(grafo.successors(nodo))
        if sucesores:
            profundidad[int(nodo)] = 1 + max(profundidad[int(sucesor)] for sucesor in sucesores)
    return profundidad
