"""Pruebas genéricas parametrizadas por carrera FCMN."""

from __future__ import annotations

import pandas as pd
import pytest

from pensunet.datos.creditos import sumar_creditos_plan
from pensunet.datos.programas import PROGRAMAS, RUTA_TRABAJO_GRADO, obtener_programa
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
def test_trabajo_de_grado_sin_tasa_ni_cero_ni_uno(clave: str):
    """TG queda fuera de tasas; no se inventa p_i = 0 ni 1."""
    programa = obtener_programa(clave)
    simulador = SimuladorPensum.desde_programa(clave)
    simulador.cargar(aplicar_ajustes_documentados=True)
    assert simulador.tasas is not None
    for codigo in programa.ids_trabajo_grado:
        assert simulador.tasa_de(codigo) is None
        assert codigo not in set(simulador.tasas["id_asignatura"])
        assert codigo in set(simulador.pensum["id_asignatura"])

    catalogo = pd.read_csv(RUTA_TRABAJO_GRADO, encoding="utf-8")
    filas = catalogo.loc[catalogo["programa"] == clave]
    assert set(filas["id_asignatura"]) == set(programa.ids_trabajo_grado)
    assert (filas["origen"] == "juicio_experto").all()
    def _vacio(valor: object) -> str:
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            return ""
        return str(valor).strip()

    assert filas["tasa_aprobacion"].map(_vacio).eq("").all()


def test_obtener_programa_desconocido_falla():
    with pytest.raises(KeyError, match="no registrado"):
        obtener_programa("medicina")
