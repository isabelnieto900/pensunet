"""Carga CSV, adaptador de columnas y fábrica de lectores."""

import pandas as pd
import pytest

from pensunet.datos.adaptador_ud import AdaptadorUD
from pensunet.datos.fabrica import FabricaLectores


def test_el_csv_llega_con_nombres_internos(simulador_crudo):
    """Sección II.A y ecuación (7): el adaptador renombra, no reescribe cifras."""
    pensum = simulador_crudo.pensum
    prerrequisitos = simulador_crudo.prerequisitos
    assert list(pensum["id_asignatura"]).count(4) == 1
    catedra = pensum.loc[pensum["id_asignatura"] == 4].iloc[0]
    assert catedra["nombre"] == "Cátedra Francisco José de Caldas"
    assert catedra["semestre"] == 1
    assert catedra["creditos"] == 1
    assert catedra["grupo_slot"] is None

    ingles = pensum.loc[pensum["id_asignatura"] == 9901].iloc[0]
    assert ingles["grupo_slot"] == "Segunda Lengua I"
    assert "Inglés" in ingles["nombre"] or "INGLÉS" in ingles["nombre"].upper()

    ecuaciones = pensum.loc[pensum["id_asignatura"] == 4719].iloc[0]
    assert "Ecuaciones Diferenciales" in ecuaciones["nombre"]
    assert ecuaciones["nombre_pensum"] is not None

    assert set(bool(valor) for valor in prerrequisitos["debe_aprobado"]) == {True, False}
    assert len(pensum) == 91
    assert len(prerrequisitos) == 48


def test_fisica_con_ajustes_excluye_biosistemas_y_suma_aristas(simulador):
    """Los ajustes documentados no reescriben el CSV; cambian el grafo de análisis."""
    assert len(simulador.pensum) == 67
    assert 25176 not in set(simulador.pensum["id_asignatura"])
    assert simulador.red.grafo.has_edge(25140, 25145)
    assert simulador.red.grafo.has_edge(25149, 25154)
    assert simulador.ajustes_aplicados


def test_el_adaptador_rechaza_una_columna_que_falta():
    """Sin las columnas de la universidad no hay nodos para la sección II.A."""
    tabla = pd.DataFrame({"id_asignatura": [1]})
    with pytest.raises(ValueError, match="pensum"):
        AdaptadorUD().adaptar_pensum(tabla)


def test_el_adaptador_interpreta_booleanos_escritos_como_texto():
    """Sección II.A: debe_aprobado distingue el prerrequisito estricto del débil."""
    tabla = pd.DataFrame(
        [
            {
                "id_asignatura": "25176",
                "ds_nombre_asignatura": "Simulación",
                "id_prerequisito": "25145",
                "ds_nombre_prerequisito": "Cuántica",
                "nu_orden": "1",
                "fl_debe_aprobado": "False",
            }
        ]
    )
    adaptada = AdaptadorUD().adaptar_prerequisitos(tabla)
    assert bool(adaptada.loc[0, "debe_aprobado"]) is False
    assert adaptada.loc[0, "id_asignatura"] == 25176


def test_la_fabrica_crea_csv_y_rechaza_un_tipo_desconocido(rutas_datos):
    """La fábrica solo admite csv. Sección II.A y ecuación (7)."""
    lector = FabricaLectores.crear("csv", **rutas_datos)
    assert len(lector.leer_pensum()) == 91
    with pytest.raises(ValueError, match="solo admite 'csv'"):
        FabricaLectores.crear("excel")
