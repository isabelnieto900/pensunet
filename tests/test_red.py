"""Construcción del DAG, aciclicidad y semestre mínimo."""

import networkx as nx
import pandas as pd
import pytest
from tests.figuras import curriculo_figura_1

from pensunet.dominio.red import construir_red, validar_aciclicidad


def test_el_grafo_crudo_de_fisica_es_un_dag_estricto(simulador_crudo):
    """Sección II.A: extracto Condor de Física sin ajustes (91+huérfano, 46 estrictas)."""
    red = simulador_crudo.red
    assert red.es_aciclico()
    assert validar_aciclicidad(red.grafo)
    assert red.grafo.number_of_nodes() == 92
    assert red.grafo.number_of_edges() == 46
    assert red.duracion_nominal == 10
    assert red.grafo.has_edge(25102, 25106)
    assert not red.grafo.has_edge(25106, 25102)
    assert not red.grafo.has_edge(25145, 25176)
    assert (25145, 25176) in red.prerrequisitos_debiles_excluidos
    assert (25132, 25139) in red.prerrequisitos_debiles_excluidos
    assert len(red.prerrequisitos_debiles_excluidos) == 2


def test_la_inversion_de_semestres_queda_anotada_en_el_extracto_crudo(simulador_crudo):
    """Sección II.A: 25176 está en el semestre 7 y su prerrequisito débil en el 9."""
    textos = " ".join(simulador_crudo.red.inconsistencias)
    assert "25176" in textos
    assert "25145" in textos
    assert "25139" in textos
    assert len(simulador_crudo.red.inconsistencias) == 2
    nombre = simulador_crudo.red.grafo.nodes[4719]["nombre"]
    assert "Ecuaciones Diferenciales" in nombre


def test_fisica_con_ajustes_es_dag_sin_biosistemas(simulador):
    """Tras ajustes: 67 nodos, 53 aristas estrictas, sin inconsistencias residuales.

    Reglas de Física de la etapa 2: solo inglés, sin electivas no ofrecidas y
    cinco aristas confirmadas (materiales, gestión y cátedras).
    """
    red = simulador.red
    assert red.es_aciclico()
    assert red.grafo.number_of_nodes() == 67
    assert red.grafo.number_of_edges() == 53
    confirmadas = ((25141, 25146), (25146, 25151), (25142, 25148), (25148, 25153), (4, 12))
    for previo, siguiente in confirmadas:
        assert red.grafo.has_edge(previo, siguiente)
    assert not any(codigo in red.grafo for codigo in (9904, 9910, 9915, 25162, 25174))
    assert 25176 not in red.grafo
    assert red.grafo.has_edge(25140, 25145)
    assert red.grafo.has_edge(25149, 25154)
    assert red.prerrequisitos_debiles_excluidos == []
    assert red.inconsistencias == []


def test_los_niveles_siguen_la_cadena_de_prerrequisitos(simulador):
    """Sección II.A: el semestre mínimo es el largo de la cadena, no el del plan."""
    niveles = simulador.red.niveles()
    assert niveles[25102] == 1
    assert niveles[25106] == 2
    assert niveles[25111] == 3
    assert niveles[25112] == 3
    assert niveles[25117] == 4
    assert niveles[9901] == 1
    assert niveles[9902] == 2
    assert niveles[9903] == 3
    assert niveles[25154] == 2
    assert simulador.red.grafo.nodes[25154]["semestre"] == 10


def test_el_segundo_curriculo_de_la_figura_1_tiene_estos_niveles():
    """Sección II.A, figura 1: A en el primer semestre y D en el tercero."""
    niveles = curriculo_figura_1().niveles()
    assert niveles == {1: 1, 2: 2, 3: 2, 4: 3}


def test_un_ciclo_no_se_acepta_como_pensum():
    """Sección II.A: un ciclo haría que dos asignaturas se exigieran mutuamente."""
    pensum = pd.DataFrame(
        [
            {"id_asignatura": 1, "nombre": "A", "semestre": 1},
            {"id_asignatura": 2, "nombre": "B", "semestre": 1},
        ]
    )
    prerrequisitos = pd.DataFrame(
        [
            {"id_asignatura": 2, "id_prerequisito": 1, "debe_aprobado": True},
            {"id_asignatura": 1, "id_prerequisito": 2, "debe_aprobado": True},
        ]
    )
    with pytest.raises(ValueError, match="ciclo"):
        construir_red(pensum, prerrequisitos)

    ciclico = nx.DiGraph([(1, 2), (2, 1)])
    assert validar_aciclicidad(ciclico) is False
