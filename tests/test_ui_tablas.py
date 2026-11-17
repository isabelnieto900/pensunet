"""Tablas auxiliares de la interfaz (sin abrir Streamlit)."""

from pensunet.dominio.escenario import Escenario
from pensunet.ui.tablas import (
    tabla_indicadores,
    tabla_resumen_red,
    tabla_tasas_del_grafo,
    tabla_tiempos,
    tasas_desde_editor,
)


def test_tabla_resumen_coincide_con_la_red(simulador):
    resumen = tabla_resumen_red(simulador.red)
    assert resumen["asignaturas"] == simulador.red.grafo.number_of_nodes()
    assert resumen["aristas"] == simulador.red.grafo.number_of_edges()
    assert resumen["duracion_nominal"] == simulador.red.duracion_nominal


def test_tabla_indicadores_incluye_cuellos(simulador):
    indicadores = simulador.indicadores()
    tabla = tabla_indicadores(simulador.red, indicadores)
    assert len(tabla) == simulador.red.grafo.number_of_nodes()
    assert set(tabla["id"]) == set(simulador.red.grafo.nodes)
    assert tabla["bloqueo"].is_monotonic_decreasing or len(tabla) == 1


def test_tabla_tiempos_suma_la_muestra(simulador):
    resultado = simulador.simular(Escenario(n_estudiantes=80, semilla=2))
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
