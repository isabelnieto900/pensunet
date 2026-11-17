"""Monte Carlo del tiempo de grado (sección III.B)."""

import pytest

from pensunet.dominio.escenario import Escenario
from pensunet.ui.placeholder import ejecutar


def test_simular_estima_tiempos_de_grado(simulador):
    """Ecuaciones (3) y (4): la muestra de X tiene media finita."""
    resultado = simulador.simular(Escenario(n_estudiantes=200, semilla=7))
    assert len(resultado.tiempos) == 200
    assert all(tiempo >= 10 for tiempo in resultado.tiempos)
    assert resultado.media >= 10
    assert resultado.desviacion >= 0


def test_simular_es_reproducible_con_la_misma_semilla(simulador):
    """Misma semilla → misma muestra de X."""
    escenario = Escenario(n_estudiantes=50, semilla=123)
    uno = simulador.simular(escenario)
    dos = simulador.simular(escenario)
    assert uno.tiempos == dos.tiempos
    assert uno.media == dos.media


def test_el_escenario_no_acepta_una_muestra_vacia():
    """Ecuaciones (3) y (4): sin estudiantes no hay distribución de X."""
    with pytest.raises(ValueError, match="estudiante"):
        Escenario(n_estudiantes=0)


def test_falta_de_tasa_impide_simular(simulador):
    """Sin p_i para un nodo del grafo no se puede correr el Monte Carlo."""
    tasas = simulador.tasas.copy()
    tasas = tasas.loc[tasas["id_asignatura"] != 25102].reset_index(drop=True)
    with pytest.raises(ValueError, match="faltan tasas"):
        simulador._estrategia.simular(simulador.red, tasas, Escenario(n_estudiantes=5, semilla=1))


def test_la_interfaz_no_esta_implementada():
    """La fachada de las secciones II.A y II.B se usa desde Python."""
    with pytest.raises(NotImplementedError, match="etapa 1"):
        ejecutar()
