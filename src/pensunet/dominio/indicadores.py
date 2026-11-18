"""Indicadores topológicos de la red de prerrequisitos."""

from dataclasses import dataclass

import networkx as nx

from pensunet.dominio.red import RedPrerrequisitos

# Umbrales por defecto: grado de entrada, de salida y total.
UMBRAL_ENTRADA_CUELLO = 2
UMBRAL_SALIDA_CUELLO = 2
UMBRAL_TOTAL_CUELLO = 4


@dataclass(frozen=True)
class IndicadoresTopologicos:
    """Bloqueo, posponimiento, intermediación y cuellos de botella.

    Indicadores topológicos de bloqueo y posponimiento.
    ``repeticiones_sin_retraso`` es la k de la definición del factor de
    posponimiento: se puede reprobar la asignatura k veces sin alargar
    el grado, y el factor es 1/(k + 1).
    ``cuellos_de_botella`` son los nodos que superan los umbrales de
    grado de entrada/salida/total.
    ``camino_mas_largo`` es una cadena máxima de prerrequisitos en el DAG
    (el camino crítico topológico).
    """

    factor_bloqueo: dict[int, int]
    factor_posponimiento: dict[int, float]
    intermediacion: dict[int, float]
    repeticiones_sin_retraso: dict[int, int]
    duracion_nominal: int
    cuellos_de_botella: tuple[int, ...]
    camino_mas_largo: tuple[int, ...]


def factor_bloqueo(red: RedPrerrequisitos) -> dict[int, int]:
    """Cuenta los descendientes de cada asignatura.

    *Blocking factor*: el factor
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

    *Deferment factor*. k es el
    máximo de reprobaciones que todavía permiten graduarse en la duración
    nominal del plan. A la reprobación k + 1 el grado se alarga al menos
    un semestre. Un factor 1/3 significa que
    se puede reprobar dos veces y a la tercera el grado aumenta.

    En esta red::

        s(v) = max(semestre del plan, nivel por prerrequisitos)
        d(v) = aristas del camino más largo que sale de v
        k(v) = max(0, T - s(v) - d(v))
        factor(v) = 1 / (k(v) + 1)

    T es la duración nominal. Cada arista hacia un descendiente exige un
    semestre adicional después de aprobar v. No se puede intentar v antes
    de s(v): el escenario base no permite cursar una asignatura antes
    del semestre recomendado ni antes de sus prerrequisitos.
    """
    _, holgura = _holgura(red, duracion)
    return {nodo: 1.0 / (k + 1) for nodo, k in holgura.items()}


def intermediacion(red: RedPrerrequisitos, normalizada: bool = False) -> dict[int, float]:
    """Calcula la intermediación de cada asignatura.

    Intermediación sobre caminos más cortos entre pares de nodos::

        b_v = suma_{s ≠ v, t ≠ v} de sigma_st(v) / sigma_st

    ``sigma_st`` es el número de caminos más cortos de s a t y
    ``sigma_st(v)`` cuántos de ellos pasan por v. Con ``normalizada``
    en falso se devuelve esa suma. Con ``normalizada`` verdadero se
    divide por (n - 1)(n - 2) en un grafo dirigido (valores típicos
    del orden de 10^-3).
    """
    cruda = nx.betweenness_centrality(red.grafo, normalized=normalizada)
    return {int(nodo): float(valor) for nodo, valor in cruda.items()}


def cuellos_de_botella(
    red: RedPrerrequisitos,
    umbral_entrada: int = UMBRAL_ENTRADA_CUELLO,
    umbral_salida: int = UMBRAL_SALIDA_CUELLO,
    umbral_total: int = UMBRAL_TOTAL_CUELLO,
) -> tuple[int, ...]:
    """Identifica cuellos de botella por grado de entrada/salida/total.

    Una asignatura es cuello de
    botella si su grado de entrada supera ``umbral_entrada``, su grado
    de salida supera ``umbral_salida`` o la suma de ambos supera
    ``umbral_total``. Los umbrales por defecto (2, 2, 4) siguen el
    valores típicos de referencia; se pueden ajustar al comparar planes.
    """
    seleccionados: list[int] = []
    for nodo in red.grafo:
        entrada = int(red.grafo.in_degree(nodo))
        salida = int(red.grafo.out_degree(nodo))
        if (
            entrada > umbral_entrada
            or salida > umbral_salida
            or entrada + salida > umbral_total
        ):
            seleccionados.append(int(nodo))
    return tuple(sorted(seleccionados))


def camino_mas_largo(red: RedPrerrequisitos) -> tuple[int, ...]:
    """Una cadena máxima de prerrequisitos en el DAG.

    En un grafo acíclico el camino más largo mide la profundidad crítica
    del pensum (cuántas asignaturas hay que encadenar en serie). Si hay
    varios, NetworkX devuelve uno.
    """
    if red.grafo.number_of_nodes() == 0:
        return ()
    return tuple(int(nodo) for nodo in nx.dag_longest_path(red.grafo))


def calcular_indicadores(
    red: RedPrerrequisitos,
    duracion: int | None = None,
    umbral_entrada: int = UMBRAL_ENTRADA_CUELLO,
    umbral_salida: int = UMBRAL_SALIDA_CUELLO,
    umbral_total: int = UMBRAL_TOTAL_CUELLO,
) -> IndicadoresTopologicos:
    """Reúne bloqueo, posponimiento, intermediación y cuellos de botella.

    Indicadores topológicos de bloqueo y posponimiento.
    """
    duracion_nominal, holgura = _holgura(red, duracion)
    return IndicadoresTopologicos(
        factor_bloqueo=factor_bloqueo(red),
        factor_posponimiento={nodo: 1.0 / (k + 1) for nodo, k in holgura.items()},
        intermediacion=intermediacion(red),
        repeticiones_sin_retraso=holgura,
        duracion_nominal=duracion_nominal,
        cuellos_de_botella=cuellos_de_botella(
            red,
            umbral_entrada=umbral_entrada,
            umbral_salida=umbral_salida,
            umbral_total=umbral_total,
        ),
        camino_mas_largo=camino_mas_largo(red),
    )


def _holgura(
    red: RedPrerrequisitos,
    duracion: int | None,
) -> tuple[int, dict[int, int]]:
    """Devuelve T y la k de cada asignatura."""
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

    Esos semestres adicionales hay que reservarlos para los
    descendientes antes de cerrar la duración nominal.
    """
    profundidad = {int(nodo): 0 for nodo in grafo}
    for nodo in reversed(list(nx.topological_sort(grafo))):
        sucesores = list(grafo.successors(nodo))
        if sucesores:
            profundidad[int(nodo)] = 1 + max(profundidad[int(sucesor)] for sucesor in sucesores)
    return profundidad
