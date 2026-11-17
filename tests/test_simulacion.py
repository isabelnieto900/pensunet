"""Monte Carlo del tiempo de grado (sección III.B)."""

from __future__ import annotations

import pandas as pd
import pytest

from pensunet.dominio.escenario import Escenario
from pensunet.ui.placeholder import ejecutar


def _tasas_completas(simulador) -> pd.DataFrame:
    """Rellena huecos solo para la prueba (no es juicio experto de producción)."""
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


def test_simular_estima_tiempos_de_grado(simulador):
    """Ecuaciones (3) y (4): la muestra de X tiene media finita."""
    resultado = simulador.simular(
        Escenario(n_estudiantes=200, semilla=7),
        tasas=_tasas_completas(simulador),
    )
    assert len(resultado.tiempos) == 200
    assert all(tiempo >= 10 for tiempo in resultado.tiempos)
    assert resultado.media >= 10
    assert resultado.desviacion >= 0


def test_simular_es_reproducible_con_la_misma_semilla(simulador):
    """Misma semilla → misma muestra de X."""
    escenario = Escenario(n_estudiantes=50, semilla=123)
    tasas = _tasas_completas(simulador)
    uno = simulador.simular(escenario, tasas=tasas)
    dos = simulador.simular(escenario, tasas=tasas)
    assert uno.tiempos == dos.tiempos
    assert uno.media == dos.media


def test_el_escenario_no_acepta_una_muestra_vacia():
    """Ecuaciones (3) y (4): sin estudiantes no hay distribución de X."""
    with pytest.raises(ValueError, match="estudiante"):
        Escenario(n_estudiantes=0)


def test_falta_de_tasa_impide_simular(simulador):
    """Sin p_i para un nodo del grafo no se puede correr el Monte Carlo."""
    tasas = _tasas_completas(simulador)
    tasas = tasas.loc[tasas["id_asignatura"] != 25102].reset_index(drop=True)
    with pytest.raises(ValueError, match="faltan tasas"):
        simulador.simular(
            Escenario(n_estudiantes=5, semilla=1),
            tasas=tasas,
        )


def test_tope_bajo_censura_sin_abortar(simulador):
    """Con max_semestres bajo la muestra termina; hay trayectorias censuradas."""
    resultado = simulador.simular(
        Escenario(n_estudiantes=80, semilla=3, max_semestres=12),
        tasas=_tasas_completas(simulador),
    )
    assert len(resultado.tiempos) == 80
    assert resultado.tope_semestres == 12
    assert all(t <= 12 for t in resultado.tiempos)
    assert resultado.n_censurados > 0


def test_ejecutar_avisa_si_falta_streamlit(monkeypatch):
    """Sin el extra ui, ejecutar explica cómo instalarlo."""
    monkeypatch.setattr("pensunet.ui.placeholder.shutil.which", lambda _nombre: None)
    monkeypatch.setattr("pensunet.ui.placeholder._streamlit_importable", lambda: False)
    with pytest.raises(ModuleNotFoundError, match="Streamlit"):
        ejecutar()


def test_sin_tope_de_creditos_la_muestra_no_cambia(simulador):
    """``max_creditos_semestre=None`` reproduce exactamente el Monte Carlo previo."""
    tasas = _tasas_completas(simulador)
    base = simulador.simular(Escenario(n_estudiantes=60, semilla=5), tasas=tasas)
    explicito = simulador.simular(
        Escenario(n_estudiantes=60, semilla=5, max_creditos_semestre=None), tasas=tasas
    )
    assert base.tiempos == explicito.tiempos


def test_el_tope_de_creditos_no_acorta_el_grado(simulador):
    """Con un tope de créditos estricto, E(X) no puede bajar."""
    tasas = _tasas_completas(simulador)
    libre = simulador.simular(Escenario(n_estudiantes=150, semilla=11), tasas=tasas)
    con_tope = simulador.simular(
        Escenario(n_estudiantes=150, semilla=11, max_creditos_semestre=12), tasas=tasas
    )
    assert con_tope.media >= libre.media


def test_el_escenario_rechaza_un_tope_de_creditos_no_positivo():
    with pytest.raises(ValueError):
        Escenario(max_creditos_semestre=0)


def test_resultado_reporta_reprobaciones_y_tasa_de_grado(simulador):
    """Las reprobaciones caen en asignaturas con p_i < 1 y la tasa de grado es monótona."""
    tasas = _tasas_completas(simulador)
    resultado = simulador.simular(Escenario(n_estudiantes=120, semilla=3), tasas=tasas)
    assert len(resultado.censurados) == len(resultado.tiempos)
    frenan = resultado.asignaturas_que_frenan(5)
    assert frenan and all(media > 0 for _, media in frenan)
    p = {int(f["id_asignatura"]): float(f["tasa_aprobacion"]) for _, f in tasas.iterrows()}
    assert all(p[codigo] < 1.0 for codigo, _ in frenan)
    assert all(
        resultado.inscripciones[c] >= resultado.reprobaciones[c] for c in resultado.reprobaciones
    )
    t = simulador.red.duracion_nominal
    assert 0.0 <= resultado.tasa_grado_en(t) <= resultado.tasa_grado_en(t + 4) <= 1.0
    assert resultado.tasa_grado_en(10_000) == pytest.approx(
        1 - resultado.n_censurados / len(resultado.tiempos)
    )


def test_tasa_de_grado_en_un_resultado_fabricado():
    from pensunet.simulacion.estrategia import ResultadoSimulacion

    resultado = ResultadoSimulacion(
        tiempos=(10, 11, 12, 40),
        media=18.25,
        desviacion=0.0,
        n_censurados=1,
        censurados=(False, False, False, True),
        reprobaciones={1: 4, 2: 2},
    )
    assert resultado.tasa_grado_en(11) == pytest.approx(0.5)
    assert resultado.tasa_grado_en(40) == pytest.approx(0.75)
    assert resultado.asignaturas_que_frenan(1) == [(1, 1.0)]
