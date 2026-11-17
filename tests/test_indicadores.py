"""Bloqueo, posponimiento 1/(k + 1), intermediación y cuellos de botella."""

import pytest
from tests.figuras import curriculo_figura_1

from pensunet.dominio.indicadores import (
    calcular_indicadores,
    camino_mas_largo,
    cuellos_de_botella,
    intermediacion,
)


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


def test_la_ecuacion_2_marca_cuellos_por_grado():
    """Ecuación (2): A tiene salida 2 y es cuello con umbral_salida=1."""
    red = curriculo_figura_1()
    assert cuellos_de_botella(red, umbral_entrada=1, umbral_salida=1, umbral_total=3) == (
        1,
    )
    assert calcular_indicadores(
        red,
        umbral_entrada=1,
        umbral_salida=1,
        umbral_total=3,
    ).cuellos_de_botella == (1,)


def test_bloqueo_y_posponimiento_en_cadenas_conocidas_de_fisica(simulador):
    """Sección II.B sobre el inglés, Física I y TG con ajustes documentados."""
    indicadores = simulador.indicadores()
    bloqueo = indicadores.factor_bloqueo
    posponimiento = indicadores.factor_posponimiento
    assert bloqueo[9901] == 2
    assert bloqueo[9902] == 1
    assert bloqueo[9903] == 0
    assert bloqueo[4] == 1  # Caldas → Democracia (regla de Física)
    assert bloqueo[25154] == 0
    assert bloqueo[25149] == 1
    assert bloqueo[25102] > bloqueo[25106] > 0
    assert posponimiento[4] == pytest.approx(1 / 9)
    assert posponimiento[25102] == pytest.approx(1 / 3)
    assert posponimiento[25154] == pytest.approx(1.0)
    assert indicadores.repeticiones_sin_retraso[25102] == 2
    assert indicadores.repeticiones_sin_retraso[25154] == 0
    assert all(0 < valor <= 1 for valor in posponimiento.values())
    assert all(valor >= 0 for valor in bloqueo.values())
    assert isinstance(indicadores.cuellos_de_botella, tuple)
    assert len(indicadores.camino_mas_largo) >= 2
    assert set(indicadores.camino_mas_largo) <= set(simulador.red.grafo.nodes)


def test_camino_mas_largo_en_la_figura_1():
    """En A→B→D el camino más largo es A-B-D (tres nodos)."""
    red = curriculo_figura_1()
    assert camino_mas_largo(red) == (1, 2, 4)
    assert calcular_indicadores(red).camino_mas_largo == (1, 2, 4)


def test_la_intermediacion_de_la_ecuacion_1_cuenta_el_unico_camino(simulador):
    """Ecuación (1): 9902 es el único puente entre 9901 y 9903."""
    cruda = simulador.indicadores().intermediacion
    assert cruda[9902] == pytest.approx(1.0)
    assert cruda[9901] == pytest.approx(0.0)
    assert cruda[9903] == pytest.approx(0.0)
    ponderada = intermediacion(simulador.red, normalizada=True)
    n = simulador.red.grafo.number_of_nodes()
    assert ponderada[9902] == pytest.approx(1 / ((n - 1) * (n - 2)))
