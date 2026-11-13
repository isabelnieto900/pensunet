"""Bloqueo, posponimiento 1/(k + 1) e intermediación."""

import pytest
from tests.figuras import curriculo_figura_1

from pensunet.dominio.indicadores import calcular_indicadores, intermediacion


def test_la_figura_1_recupera_el_posponimiento_del_articulo():
    """Sección II.B: en el segundo currículo, A, B y D valen 1 y C vale 1/2."""
    red = curriculo_figura_1()
    indicadores = calcular_indicadores(red)
    assert indicadores.duracion_nominal == 3
    assert indicadores.factor_bloqueo == {1: 3, 2: 1, 3: 0, 4: 0}
    assert indicadores.repeticiones_sin_retraso == {1: 0, 2: 0, 3: 1, 4: 0}
    assert indicadores.factor_posponimiento[1] == pytest.approx(1.0)
    assert indicadores.factor_posponimiento[2] == pytest.approx(1.0)
    assert indicadores.factor_posponimiento[4] == pytest.approx(1.0)
    assert indicadores.factor_posponimiento[3] == pytest.approx(0.5)
    assert indicadores.intermediacion == {1: 0.0, 2: 1.0, 3: 0.0, 4: 0.0}


def test_bloqueo_y_posponimiento_en_cadenas_conocidas_de_fisica(simulador):
    """Sección II.B sobre el inglés, Física I y dos asignaturas sin descendientes."""
    indicadores = simulador.indicadores()
    bloqueo = indicadores.factor_bloqueo
    posponimiento = indicadores.factor_posponimiento
    assert bloqueo[9901] == 2
    assert bloqueo[9902] == 1
    assert bloqueo[9903] == 0
    assert bloqueo[4] == 0
    assert bloqueo[25154] == 0
    assert bloqueo[25102] > bloqueo[25106] > 0
    assert posponimiento[4] == pytest.approx(0.1)
    assert posponimiento[25102] == pytest.approx(0.25)
    assert posponimiento[25154] == pytest.approx(1.0)
    assert indicadores.repeticiones_sin_retraso[25102] == 3
    assert indicadores.repeticiones_sin_retraso[25154] == 0
    assert all(0 < valor <= 1 for valor in posponimiento.values())
    assert all(valor >= 0 for valor in bloqueo.values())


def test_la_intermediacion_de_la_ecuacion_1_cuenta_el_unico_camino(simulador):
    """Ecuación (1): 9902 es el único puente entre 9901 y 9903."""
    cruda = simulador.indicadores().intermediacion
    assert cruda[9902] == pytest.approx(1.0)
    assert cruda[9901] == pytest.approx(0.0)
    assert cruda[9903] == pytest.approx(0.0)
    ponderada = intermediacion(simulador.red, normalizada=True)
    n = simulador.red.grafo.number_of_nodes()
    assert ponderada[9902] == pytest.approx(1 / ((n - 1) * (n - 2)))
