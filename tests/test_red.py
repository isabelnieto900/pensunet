"""Construcción del DAG, aciclicidad y semestre mínimo."""

import networkx as nx
import pandas as pd
import pytest
from tests.figuras import curriculo_figura_1

from pensunet.dominio.red import construir_red, validar_aciclicidad


def test_el_grafo_de_fisica_es_un_dag_estricto(simulador):
    """Sección II.A: 95 asignaturas y solo las 46 aristas estrictas."""
    red = simulador.red
    assert red.es_aciclico()
    assert validar_aciclicidad(red.grafo)
    assert red.grafo.number_of_nodes() == 95
    assert red.grafo.number_of_edges() == 46
    assert red.duracion_nominal == 10
    assert red.grafo.has_edge(25102, 25106)
    assert not red.grafo.has_edge(25106, 25102)
    assert not red.grafo.has_edge(25145, 25176)
    assert (25145, 25176) in red.prerrequisitos_debiles_excluidos
    assert len(red.prerrequisitos_debiles_excluidos) == 7


def test_la_inversion_de_semestres_queda_anotada_y_no_se_corrige(simulador):
    """Sección II.A: 25176 está en el semestre 7 y su prerrequisito débil en el 9."""
    textos = " ".join(simulador.red.inconsistencias)
    assert "25176" in textos
    assert "25145" in textos
    assert len(simulador.red.inconsistencias) == 1
    nombre = simulador.red.grafo.nodes[4719]["nombre"]
    assert nombre == "ECUACIONES DIFERENCIALES"


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
    assert niveles[25154] == 1
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
