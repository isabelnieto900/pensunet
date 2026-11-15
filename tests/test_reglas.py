"""Reglas confirmadas aplicadas al grafo de análisis."""

from pensunet.dominio.reglas_pensum import (
    IDIOMAS_MODELO,
    NO_OFRECIDAS,
    SLOTS_GENERICOS_LINEA,
    preparar_tablas_analisis,
)


def test_el_grafo_de_analisis_aplica_las_reglas_confirmadas(simulador):
    """Un idioma, sin cupos genéricos, sin 25176, con aristas de cuántica y TG."""
    red = simulador.red
    assert red.reglas_aplicadas
    assert red.es_aciclico()
    assert red.duracion_nominal == 10

    for codigo in SLOTS_GENERICOS_LINEA | NO_OFRECIDAS:
        assert codigo not in red.grafo

    for codigo in IDIOMAS_MODELO:
        assert codigo in red.grafo
    assert 9904 not in red.grafo
    assert 9913 not in red.grafo

    assert red.grafo.has_edge(25140, 25145)
    assert red.grafo.has_edge(25149, 25154)
    assert red.grafo.has_edge(25141, 25146)
    assert red.grafo.has_edge(25146, 25151)
    assert red.grafo.has_edge(25142, 25148)
    assert red.grafo.has_edge(25148, 25153)
    assert 25163 not in red.grafo  # electiva sin tasa
    assert (25145, 25176) not in red.prerrequisitos_debiles_excluidos


def test_trabajo_de_grado_y_cuantica_avanzada_tienen_nivel_por_cadena(simulador):
    """Las aristas nuevas mueven el nivel topológico; el semestre del plan sigue."""
    niveles = simulador.red.niveles()
    assert niveles[25140] >= 1
    assert niveles[25145] == niveles[25140] + 1
    assert niveles[25149] == 1
    assert niveles[25154] == 2
    assert niveles[25146] == niveles[25141] + 1
    assert niveles[25151] == niveles[25146] + 1
    assert niveles[25148] == niveles[25142] + 1
    assert niveles[25153] == niveles[25148] + 1
    assert simulador.red.grafo.nodes[25154]["semestre"] == 10
    assert simulador.red.grafo.nodes[25145]["semestre"] == 9


def test_preparar_tablas_deja_bitacora_y_no_muta_el_pensum_crudo(
    simulador_crudo,
):
    """Los CSV crudos no se reescriben: la preparación opera sobre copias."""
    pensum = simulador_crudo.pensum
    prerrequisitos = simulador_crudo.prerequisitos
    tasas = simulador_crudo.tasas
    assert pensum is not None and prerrequisitos is not None and tasas is not None
    n_antes = len(pensum)
    tablas = preparar_tablas_analisis(pensum, prerrequisitos, tasas)
    assert len(pensum) == n_antes
    assert len(tablas.pensum) < n_antes
    assert tablas.excluidos
    assert any("25140 → 25145" in nota for nota in tablas.notas)
    assert any("25149 → 25154" in nota for nota in tablas.notas)
    assert any("25141 → 25146" in nota for nota in tablas.notas)
    assert any("25148 → 25153" in nota for nota in tablas.notas)
