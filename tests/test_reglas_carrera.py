"""Contrato de reglas por programa (extensible a toda la UD)."""

import pytest

from pensunet.datos.fabrica import FabricaLectores
from pensunet.dominio.reglas import FabricaReglas, ReglasSoloExtracto
from pensunet.dominio.reglas_fisica import ReglasFisica
from pensunet.facade import SimuladorPensum


def test_la_fabrica_conoce_fisica_y_extracto():
    """Otras carreras se registran cuando haya revisión experta."""
    assert isinstance(FabricaReglas.crear("fisica"), ReglasFisica)
    assert isinstance(FabricaReglas.crear("extracto"), ReglasSoloExtracto)
    with pytest.raises(ValueError, match="revisión experta"):
        FabricaReglas.crear("matematicas")


def test_reglas_solo_extracto_no_corrigen(simulador_crudo, rutas_datos):
    """Sin reglas locales el grafo coincide con el CSV."""
    lector = FabricaLectores.crear("csv", **rutas_datos)
    modelo = SimuladorPensum(lector, reglas=ReglasSoloExtracto("biologia"))
    red = modelo.cargar(aplicar_reglas=True)
    assert red.grafo.number_of_nodes() == simulador_crudo.red.grafo.number_of_nodes()
    assert red.grafo.number_of_edges() == simulador_crudo.red.grafo.number_of_edges()
    assert any(
        "extracto" in nota.lower() or "biologia" in nota for nota in red.reglas_aplicadas
    )


def test_por_defecto_la_fachada_usa_reglas_de_fisica(simulador):
    """La v1 documenta Física; el default sigue siendo ReglasFisica."""
    notas = simulador.red.reglas_aplicadas
    assert any("Física" in nota or "fisica" in nota.lower() for nota in notas)
    assert simulador.red.grafo.has_edge(25140, 25145)
