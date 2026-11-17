"""Complejidad curricular (Heileman et al., 2018) sobre redes pequeñas y FCMN."""

import networkx as nx
from tests.figuras import curriculo_figura_1

from pensunet.dominio.complejidad import calcular_complejidad, factor_retraso


def test_retraso_de_la_figura_1():
    """A→B→D y A→C: el camino más largo por A, B y D tiene 3 vértices; por C, 2."""
    assert factor_retraso(curriculo_figura_1()) == {1: 3, 2: 3, 3: 2, 4: 3}


def test_complejidad_de_la_figura_1():
    """h = d + b: A 6, B 4, C 2, D 3; total 15."""
    complejidad = calcular_complejidad(curriculo_figura_1())
    assert complejidad.bloqueo == {1: 3, 2: 1, 3: 0, 4: 0}
    assert complejidad.complejidad_estructural == {1: 6, 2: 4, 3: 2, 4: 3}
    assert complejidad.complejidad_total == 15
    assert complejidad.ranking(2) == [(1, 6), (2, 4)]


def test_la_complejidad_es_coherente_en_cada_carrera(simulador_programa):
    """En cualquier plan: d(v) ≥ 1, d(v) ≤ camino más largo y total = suma de h."""
    red = simulador_programa.red
    complejidad = calcular_complejidad(red)
    largo = len(nx.dag_longest_path(red.grafo))
    assert set(complejidad.retraso) == {int(n) for n in red.grafo}
    assert all(1 <= d <= largo for d in complejidad.retraso.values())
    assert max(complejidad.retraso.values()) == largo
    assert complejidad.complejidad_total == sum(complejidad.complejidad_estructural.values())


def test_la_fachada_expone_la_complejidad(simulador):
    """``SimuladorPensum.complejidad`` delega en el dominio."""
    complejidad = simulador.complejidad()
    assert complejidad.complejidad_total > 0
