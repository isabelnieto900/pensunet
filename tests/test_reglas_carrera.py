"""Contrato de reglas por programa (extensible a toda la UD)."""

import pytest

from pensunet.datos.fabrica import FabricaLectores
from pensunet.datos.programas import PROGRAMAS
from pensunet.dominio.reglas import (
    FabricaReglas,
    ReglasCarrera,
    ReglasDocumentadas,
    ReglasSoloExtracto,
)
from pensunet.dominio.reglas_fisica import ReglasFisica
from pensunet.facade import SimuladorPensum


def test_la_fabrica_conoce_las_carreras_fcmn_y_el_extracto():
    assert isinstance(FabricaReglas.crear("fisica"), ReglasFisica)
    for clave in PROGRAMAS:
        reglas = FabricaReglas.crear(clave)
        assert isinstance(reglas, ReglasDocumentadas)
        assert reglas.codigo_programa == clave
    assert isinstance(FabricaReglas.crear("extracto"), ReglasSoloExtracto)
    with pytest.raises(ValueError, match="No hay reglas"):
        FabricaReglas.crear("ingenieria")


def test_reglas_solo_extracto_no_corrigen(simulador_crudo, rutas_datos):
    """Sin reglas locales el grafo coincide con el CSV."""
    lector = FabricaLectores.crear("csv", **rutas_datos)
    modelo = SimuladorPensum(lector, reglas=ReglasSoloExtracto("fisica"))
    red = modelo.cargar(aplicar_reglas=True)
    assert red.grafo.number_of_nodes() == simulador_crudo.red.grafo.number_of_nodes()
    assert red.grafo.number_of_edges() == simulador_crudo.red.grafo.number_of_edges()
    assert any("extracto" in nota.lower() for nota in red.reglas_aplicadas)


def test_desde_programa_usa_las_reglas_documentadas(simulador):
    assert isinstance(simulador.reglas, ReglasCarrera)
    assert simulador.reglas.codigo_programa == "fisica"
    assert simulador.red.grafo.has_edge(25140, 25145)
    assert simulador.red.reglas_aplicadas


def test_las_reglas_no_mutan_las_tablas_de_entrada(simulador_crudo):
    pensum = simulador_crudo.pensum
    n_antes = len(pensum)
    tablas = ReglasFisica().preparar(
        pensum, simulador_crudo.prerequisitos, simulador_crudo.tasas
    )
    assert len(pensum) == n_antes
    assert tablas.excluidos
    assert len(tablas.pensum) == n_antes - len(tablas.excluidos)
