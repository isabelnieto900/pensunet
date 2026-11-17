"""Reglas de Física de la etapa 2 (PR #2) aplicadas desde ajustes_prerrequisitos.csv."""

from pensunet.dominio.reglas_fisica import CREDITOS_LINEA_APLICACION
from pensunet.dominio.reglas_pensum import (
    ARISTAS_CONFIRMADAS,
    ELECTIVAS_SIN_OFERTA,
    IDIOMAS_MODELO,
    NO_OFRECIDAS,
    SLOTS_GENERICOS_LINEA,
    preparar_tablas_analisis,
)
from pensunet.simulacion.montecarlo_molontay import creditos_electivos_del_plan


def test_el_grafo_de_analisis_aplica_las_reglas_confirmadas(simulador):
    """Un idioma, sin cupos genéricos ni electivas sin oferta, con las cadenas."""
    red = simulador.red
    assert red.reglas_aplicadas
    assert red.es_aciclico()
    assert red.duracion_nominal == 10

    for codigo in SLOTS_GENERICOS_LINEA | NO_OFRECIDAS | ELECTIVAS_SIN_OFERTA:
        assert codigo not in red.grafo
    for codigo in IDIOMAS_MODELO:
        assert codigo in red.grafo
    assert 9904 not in red.grafo
    assert 9913 not in red.grafo

    for prerrequisito, asignatura in ARISTAS_CONFIRMADAS:
        assert red.grafo.has_edge(prerrequisito, asignatura)
    assert not red.grafo.has_edge(12, 25115)  # pendiente de confirmar
    assert red.grafo.has_edge(25120, 25127)  # ya en el CSV


def test_las_cadenas_mueven_el_nivel_topologico(simulador):
    """Las aristas nuevas mueven el nivel; el semestre del plan sigue."""
    niveles = simulador.red.niveles()
    assert niveles[25145] == niveles[25140] + 1
    assert niveles[25154] == niveles[25149] + 1
    assert niveles[25146] == niveles[25141] + 1
    assert niveles[25151] == niveles[25146] + 1
    assert niveles[25148] == niveles[25142] + 1
    assert niveles[25153] == niveles[25148] + 1
    assert simulador.red.grafo.nodes[25154]["semestre"] == 10
    assert simulador.red.grafo.nodes[25145]["semestre"] == 9


def test_el_cupo_de_linea_es_18_creditos(simulador):
    assert creditos_electivos_del_plan(simulador.red) == CREDITOS_LINEA_APLICACION


def test_preparar_tablas_deja_bitacora_y_no_muta_el_pensum_crudo(simulador_crudo):
    """Los CSV crudos no se reescriben: la preparación opera sobre copias."""
    pensum = simulador_crudo.pensum
    n_antes = len(pensum)
    tablas = preparar_tablas_analisis(
        pensum, simulador_crudo.prerequisitos, simulador_crudo.tasas
    )
    assert len(pensum) == n_antes
    assert IDIOMAS_MODELO.isdisjoint(tablas.excluidos)
    assert {9904, 9913} <= tablas.excluidos
    assert ELECTIVAS_SIN_OFERTA <= tablas.excluidos
    texto = " ".join(tablas.notas)
    for prerrequisito, asignatura in ARISTAS_CONFIRMADAS:
        assert str(prerrequisito) in texto and str(asignatura) in texto
