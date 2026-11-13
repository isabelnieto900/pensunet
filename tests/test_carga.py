"""Carga CSV, adaptador de columnas y fábrica de lectores."""

import pandas as pd
import pytest

from pensunet.datos.adaptador_ud import AdaptadorUD
from pensunet.datos.fabrica import FabricaLectores
from pensunet.datos.lector_redshift import LectorRedshift


def test_el_csv_llega_con_nombres_internos(simulador):
    """Sección II.A y ecuación (7): el adaptador renombra, no reescribe cifras."""
    pensum = simulador.pensum
    prerrequisitos = simulador.prerequisitos
    assert list(pensum["id_asignatura"]).count(4) == 1
    catedra = pensum.loc[pensum["id_asignatura"] == 4].iloc[0]
    assert catedra["nombre"] == "CÁTEDRA FRANCISCO JOSÉ DE CALDAS"
    assert catedra["semestre"] == 1
    assert catedra["creditos"] == 1
    assert catedra["grupo_slot"] is None

    ingles = pensum.loc[pensum["id_asignatura"] == 9901].iloc[0]
    assert ingles["grupo_slot"] == "Segunda Lengua I"
    assert "INGLÉS" in ingles["nombre"]

    ecuaciones = pensum.loc[pensum["id_asignatura"] == 4719].iloc[0]
    assert ecuaciones["nombre"] == "ECUACIONES DIFERENCIALES"
    assert ecuaciones["nombre_pensum"] == "Ecuaciones Diferenciales I"

    assert set(bool(valor) for valor in prerrequisitos["debe_aprobado"]) == {True, False}
    assert len(pensum) == 95
    assert len(prerrequisitos) == 53


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
    """La fábrica solo conoce csv y redshift. Sección II.A y ecuación (7)."""
    lector = FabricaLectores.crear("csv", **rutas_datos)
    assert len(lector.leer_pensum()) == 95
    with pytest.raises(ValueError, match="redshift"):
        FabricaLectores.crear("excel")


def test_redshift_esta_documentado_y_no_conecta():
    """Ecuación (7): el stub no baja microdatos ni abre una sesión."""
    lector = LectorRedshift(host="ejemplo.redshift.amazonaws.com", usuario="solo_lectura")
    with pytest.raises(NotImplementedError, match="Redshift"):
        lector.leer_tasas_aprobacion()
    with pytest.raises(NotImplementedError, match="Redshift"):
        lector.leer_pensum()
