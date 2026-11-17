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
