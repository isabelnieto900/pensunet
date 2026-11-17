"""Datos FCMN compartidos por las pruebas."""

from pathlib import Path

import pytest

from pensunet.datos.programas import PROGRAMAS, Programa
from pensunet.facade import SimuladorPensum


@pytest.fixture(scope="session")
def rutas_datos() -> dict[str, Path]:
    """Rutas de los tres CSV de Física."""
    return PROGRAMAS["fisica"].rutas()


@pytest.fixture(scope="session")
def programa_fisica() -> Programa:
    return PROGRAMAS["fisica"]


@pytest.fixture(scope="session")
def simulador_crudo() -> SimuladorPensum:
    """Extracto CSV de Física sin ajustes documentados."""
    modelo = SimuladorPensum.desde_programa("fisica")
    modelo.cargar(aplicar_ajustes_documentados=False)
    return modelo


@pytest.fixture(scope="session")
def simulador() -> SimuladorPensum:
    """Física con ajustes_prerrequisitos.csv aplicados."""
    modelo = SimuladorPensum.desde_programa("fisica")
    modelo.cargar(aplicar_ajustes_documentados=True)
    return modelo


@pytest.fixture(params=sorted(PROGRAMAS))
def clave_programa(request: pytest.FixtureRequest) -> str:
    return str(request.param)


@pytest.fixture
def simulador_programa(clave_programa: str) -> SimuladorPensum:
    """Simulador con ajustes para cada carrera FCMN."""
    modelo = SimuladorPensum.desde_programa(clave_programa)
    modelo.cargar(aplicar_ajustes_documentados=True)
    return modelo
