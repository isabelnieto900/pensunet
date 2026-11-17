"""Tablas auxiliares de la interfaz (sin abrir Streamlit)."""

import pandas as pd
import pytest

from pensunet.dominio.escenario import Escenario
from pensunet.ui.tablas import (
    tabla_indicadores,
    tabla_resumen_red,
    tabla_tasas_del_grafo,
    tabla_tiempos,
    tasas_desde_editor,
)


def _tasas_completas(simulador) -> pd.DataFrame:
    assert simulador.red is not None and simulador.tasas is not None
    tasas = simulador.tasas.copy()
    ids = {int(v) for v in tasas["id_asignatura"]}
    nuevas = []
    for nodo in simulador.red.grafo.nodes:
        codigo = int(nodo)
        if codigo in ids:
            continue
        nuevas.append(
            {
                "id_asignatura": codigo,
                "nombre": simulador.red.grafo.nodes[nodo].get("nombre", ""),
                "n_inscritos": 0,
                "n_aprobados": 0,
                "tasa_aprobacion": 1.0,
                "n_bajo": True,
            }
        )
    if nuevas:
        tasas = pd.concat([tasas, pd.DataFrame(nuevas)], ignore_index=True)
    return tasas


def test_tabla_resumen_coincide_con_la_red(simulador):
    resumen = tabla_resumen_red(simulador.red)
    assert resumen["asignaturas"] == simulador.red.grafo.number_of_nodes()
    assert resumen["aristas"] == simulador.red.grafo.number_of_edges()
    assert resumen["duracion_nominal"] == simulador.red.duracion_nominal
    assert resumen["reglas_aplicadas"] == len(simulador.red.reglas_aplicadas)


def test_tabla_indicadores_incluye_cuellos(simulador):
    indicadores = simulador.indicadores()
    tabla = tabla_indicadores(simulador.red, indicadores)
    assert len(tabla) == simulador.red.grafo.number_of_nodes()
    assert set(tabla["id"]) == set(simulador.red.grafo.nodes)
    assert tabla["bloqueo"].is_monotonic_decreasing or len(tabla) == 1


def test_tabla_tiempos_suma_la_muestra(simulador):
    resultado = simulador.simular(
        Escenario(n_estudiantes=80, semilla=2),
        tasas=_tasas_completas(simulador),
    )
    frecuencias = tabla_tiempos(resultado)
    assert frecuencias["estudiantes"].sum() == 80
    assert abs(frecuencias["proporcion"].sum() - 1.0) < 1e-9


def test_tasas_editadas_se_aplican_en_la_simulacion(simulador):
    """Cambiar p_i en el editor altera la tabla que recibe el Monte Carlo."""
    editor = tabla_tasas_del_grafo(simulador.red, simulador.tasas)
    assert len(editor) == simulador.red.grafo.number_of_nodes()
    codigo = int(editor.iloc[0]["id"])
    editor = editor.copy()
    editor.loc[editor["id"] == codigo, "tasa_aprobacion"] = 0.5
    fusion = tasas_desde_editor(simulador.tasas, editor)
    fila = fusion.loc[fusion["id_asignatura"] == codigo].iloc[0]
    assert float(fila["tasa_aprobacion"]) == 0.5


def test_tabla_indicadores_agrega_complejidad(simulador):
    from pensunet.dominio.complejidad import calcular_complejidad

    complejidad = calcular_complejidad(simulador.red)
    tabla = tabla_indicadores(simulador.red, simulador.indicadores(), complejidad)
    assert {"retraso", "complejidad"} <= set(tabla.columns)
    assert int(tabla["complejidad"].sum()) == complejidad.complejidad_total


def test_tasa_media_ignora_asignaturas_sin_historico(simulador_crudo):
    from pensunet.ui.tablas import tasa_media, tasas_por_asignatura

    por_id = tasas_por_asignatura(simulador_crudo.red, simulador_crudo.tasas)
    conocidas = [v for v in por_id.values() if v is not None]
    assert any(v is None for v in por_id.values())
    assert tasa_media(simulador_crudo.red, simulador_crudo.tasas) == pytest.approx(
        sum(conocidas) / len(conocidas)
    )
