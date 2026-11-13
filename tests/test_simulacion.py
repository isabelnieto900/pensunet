"""El Monte Carlo y la interfaz siguen siendo un esqueleto."""

import pytest

from pensunet.dominio.escenario import Escenario
from pensunet.ui.placeholder import ejecutar


def test_simular_avisa_que_el_monte_carlo_no_esta(simulador):
    """Ecuaciones (3) y (4), sección III.B: la estrategia todavía no corre."""
    with pytest.raises(NotImplementedError, match="etapa 3"):
        simulador.simular(Escenario(n_estudiantes=10, semilla=1))


def test_el_escenario_no_acepta_una_muestra_vacia():
    """Ecuaciones (3) y (4): sin estudiantes no hay distribución de X."""
    with pytest.raises(ValueError, match="estudiante"):
        Escenario(n_estudiantes=0)


def test_la_interfaz_no_esta_implementada():
    """La fachada de las secciones II.A y II.B se usa desde Python."""
    with pytest.raises(NotImplementedError, match="etapa 1"):
        ejecutar()
