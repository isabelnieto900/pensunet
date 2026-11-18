"""Pruebas genéricas parametrizadas por carrera FCMN."""

from __future__ import annotations

import pandas as pd
import pytest

from pensunet.datos.creditos import sumar_creditos_plan
from pensunet.datos.programas import (
    PROGRAMAS,
    RUTA_JUICIO_EXPERTO,
    RUTA_TRABAJO_GRADO,
    obtener_programa,
)
from pensunet.dominio.red import validar_aciclicidad
from pensunet.facade import SimuladorPensum


@pytest.mark.parametrize("clave", sorted(PROGRAMAS))
def test_ids_de_asignatura_son_unicos(clave: str):
    pensum = pd.read_csv(PROGRAMAS[clave].ruta_pensum, encoding="utf-8")
    ids = list(pensum["id_asignatura"])
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("clave", sorted(PROGRAMAS))
def test_la_red_con_ajustes_es_aciclica(clave: str):
    simulador = SimuladorPensum.desde_programa(clave)
    red = simulador.cargar(aplicar_ajustes_documentados=True)
    assert red.es_aciclico()
    assert validar_aciclicidad(red.grafo)


@pytest.mark.parametrize("clave", sorted(PROGRAMAS))
def test_codigos_de_prerrequisito_estan_en_pensum_o_reportados(clave: str):
    """Todo extremo de arista está en el pensum, o queda en inconsistencias."""
    simulador = SimuladorPensum.desde_programa(clave)
    red = simulador.cargar(aplicar_ajustes_documentados=True)
    assert simulador.pensum is not None
    assert simulador.prerequisitos is not None
    ids_pensum = set(int(v) for v in simulador.pensum["id_asignatura"])
    ids_grafo = set(red.grafo.nodes)
    huerfanos = ids_grafo - ids_pensum
    if huerfanos:
        texto = " ".join(red.inconsistencias)
        for identificador in huerfanos:
            assert str(identificador) in texto
    for fila in simulador.prerequisitos.to_dict(orient="records"):
        for campo in ("id_asignatura", "id_prerequisito"):
            codigo = int(fila[campo])
            assert codigo in ids_grafo


@pytest.mark.parametrize(
    ("clave", "creditos"),
    [(clave, prog.creditos_plan) for clave, prog in sorted(PROGRAMAS.items())],
)
def test_suma_de_creditos_del_plan(clave: str, creditos: int):
    simulador = SimuladorPensum.desde_programa(clave)
    simulador.cargar(aplicar_ajustes_documentados=False)
    assert simulador.pensum is not None
    assert sumar_creditos_plan(simulador.pensum, programa=clave) == creditos


@pytest.mark.parametrize("clave", sorted(PROGRAMAS))
def test_trabajo_de_grado_usa_p_1_por_juicio_experto(clave: str):
    """TG: p = 1 documentado en trabajo_de_grado.csv; el CSV de tasas no se toca."""
    programa = obtener_programa(clave)
    simulador = SimuladorPensum.desde_programa(clave)
    simulador.cargar(aplicar_ajustes_documentados=True)
    for codigo in programa.ids_trabajo_grado:
        assert simulador.tasa_de(codigo) == 1.0
        assert codigo in set(simulador.pensum["id_asignatura"])
    assert any("juicio experto" in nota for nota in simulador.ajustes_aplicados)

    crudo = SimuladorPensum.desde_programa(clave)
    crudo.cargar(aplicar_ajustes_documentados=False)
    for codigo in programa.ids_trabajo_grado:
        assert crudo.tasa_de(codigo) is None

    catalogo = pd.read_csv(RUTA_TRABAJO_GRADO, encoding="utf-8")
    filas = catalogo.loc[catalogo["programa"] == clave]
    assert set(filas["id_asignatura"]) == set(programa.ids_trabajo_grado)
    assert (filas["origen"] == "juicio_experto").all()
    assert (filas["tasa_aprobacion"] == 1.0).all()
    assert filas["justificacion"].str.len().gt(20).all()




def test_quimica_25234_usa_p_1_por_juicio_experto():
    """Profundización I: p = 1 documentado; el histórico (0/119) no se toca."""
    simulador = SimuladorPensum.desde_programa("quimica")
    simulador.cargar(aplicar_ajustes_documentados=True)
    assert simulador.tasa_de(25234) == 1.0
    assert any("25234" in nota and "juicio experto" in nota for nota in simulador.ajustes_aplicados)

    crudo = SimuladorPensum.desde_programa("quimica")
    crudo.cargar(aplicar_ajustes_documentados=False)
    assert crudo.tasa_de(25234) == 0.0
    historico = pd.read_csv(PROGRAMAS["quimica"].ruta_tasas, encoding="utf-8")
    fila = historico.loc[historico["id_asignatura"] == 25234].iloc[0]
    assert int(fila["n_inscritos"]) == 119
    assert int(fila["n_aprobados"]) == 0
    assert float(fila["tasa_aprobacion"]) == 0.0


def test_matematicas_19927_usa_p_1_por_juicio_experto():
    """Electiva en el Área de TG: p = 1 documentado; el histórico no la trae."""
    simulador = SimuladorPensum.desde_programa("matematicas")
    simulador.cargar(aplicar_ajustes_documentados=True)
    assert simulador.tasa_de(19927) == 1.0
    assert any("19927" in nota and "juicio experto" in nota for nota in simulador.ajustes_aplicados)

    crudo = SimuladorPensum.desde_programa("matematicas")
    crudo.cargar(aplicar_ajustes_documentados=False)
    assert crudo.tasa_de(19927) is None
    historico = pd.read_csv(PROGRAMAS["matematicas"].ruta_tasas, encoding="utf-8")
    assert 19927 not in set(historico["id_asignatura"].astype(int))


def test_catalogo_juicio_experto_documenta_25234_y_19927():
    catalogo = pd.read_csv(RUTA_JUICIO_EXPERTO, encoding="utf-8")
    esperado = {("quimica", 25234), ("matematicas", 19927)}
    hallado = set(zip(catalogo["programa"], catalogo["id_asignatura"].astype(int)))
    assert hallado == esperado
    assert (catalogo["origen"] == "juicio_experto").all()
    assert (catalogo["tasa_aprobacion"] == 1.0).all()
    assert catalogo["justificacion"].str.len().gt(20).all()


def test_quimica_y_matematicas_producen_graduados_con_el_cupo_del_plan():
    """Con p = 1 por juicio experto, ambas carreras dejan de quedar bloqueadas."""
    from pensunet.dominio.escenario import Escenario
    from pensunet.simulacion.montecarlo import creditos_electivos_del_plan

    for clave in ("quimica", "matematicas"):
        simulador = SimuladorPensum.desde_programa(clave)
        simulador.cargar(aplicar_ajustes_documentados=True)
        cupo = creditos_electivos_del_plan(simulador.red)
        resultado = simulador.simular(
            Escenario(n_estudiantes=40, semilla=1, creditos_electivas_minimos=cupo)
        )
        assert resultado.n_censurados < 40, clave
        assert resultado.media < resultado.tope_semestres, clave
        assert resultado.tasa_grado_en(resultado.tope_semestres) > 0, clave

def test_obtener_programa_desconocido_falla():
    with pytest.raises(KeyError, match="no registrado"):
        obtener_programa("medicina")
