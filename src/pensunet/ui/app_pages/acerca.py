"""Acerca de Pensunet (visible en Facultad y carrera)."""

from __future__ import annotations

import streamlit as st

from pensunet import __version__
from pensunet.datos.privacidad import UMBRAL_MIN_INSCRITOS
from pensunet.ui.estilo import breadcrumb


def mostrar() -> None:
    breadcrumb()
    st.subheader("Acerca de")

    with st.container(border=True):
        st.markdown("**Modelo**")
        st.write(
            "Pensunet simula el flujo de estudiantes por un pensum modelado "
            "como red de prerrequisitos (DAG), con tasas de aprobación por "
            "materia, Monte Carlo del tiempo hasta el grado y detección de "
            "cuellos de botella estructurales."
        )

    with st.container(border=True):
        st.markdown("**Datos**")
        st.write(
            "Datos de la Facultad de Ciencias Matemáticas y Naturales "
            "(FCMN): tasas por asignatura desde 2023 hasta 2025."
        )
        st.write(
            f"Celdas con menos de {UMBRAL_MIN_INSCRITOS} inscritos se "
            "marcan como sin dato suficiente."
        )

    with st.container(border=True):
        st.markdown("**Juicio experto**")
        st.write(
            "Algunas materias sin histórico usable (p. ej. Trabajo de Grado) "
            "llevan tasa documentada p = 1 u otros juicios en "
            "`data/reference/juicio_experto.csv` y "
            "`trabajo_de_grado.csv`. Los ajustes de aristas viven en "
            "`ajustes_prerrequisitos.csv`."
        )

    with st.container(border=True):
        st.markdown("**Documentación y código**")
        st.markdown(
            "- Documentación: "
            "[isabelnieto900.github.io/pensunet]"
            "(https://isabelnieto900.github.io/pensunet/)\n"
            "- Repositorio: "
            "[github.com/IsabelNieto900/pensunet]"
            "(https://github.com/IsabelNieto900/pensunet)\n"
            f"- Versión: Pensunet {__version__}"
        )
        st.caption(
            "El código del repositorio sigue su licencia publicada. "
            "No se muestra el escudo ni el logo de la Universidad Distrital."
        )
