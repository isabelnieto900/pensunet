"""Datos de Física compartidos por las pruebas."""

from pathlib import Path

import pytest

from pensunet.datos.fabrica import FabricaLectores
from pensunet.facade import SimuladorPensum

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def rutas_datos() -> dict[str, Path]:
    """Rutas de los tres CSV que sí pueden estar en el repositorio."""
    return {
        "ruta_pensum": RAIZ / "data" / "reference" / "pensum_fisica.csv",
        "ruta_prerequisitos": RAIZ / "data" / "reference" / "prerequisitos_fisica.csv",
        "ruta_tasas": RAIZ / "data" / "processed" / "tasas_aprobacion_fisica.csv",
    }


@pytest.fixture(scope="session")
def simulador_crudo(rutas_datos: dict[str, Path]) -> SimuladorPensum:
    """Extracto CSV sin reglas del programa. Sección II.A y ecuación (7)."""
    lector = FabricaLectores.crear("csv", **rutas_datos)
    modelo = SimuladorPensum(lector)
    modelo.cargar(aplicar_reglas=False)
    return modelo


@pytest.fixture(scope="session")
def simulador(rutas_datos: dict[str, Path]) -> SimuladorPensum:
    """Grafo de análisis con reglas confirmadas. Sección II.A y ecuación (7)."""
    lector = FabricaLectores.crear("csv", **rutas_datos)
    modelo = SimuladorPensum(lector)
    modelo.cargar(aplicar_reglas=True)
    return modelo
