"""Materias a escala Facultad (4 carreras)."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from pensunet.ui.compartido import materias_compartidas, top_menor_aprobacion_facultad
from pensunet.ui.estilo import COLORES_CARRERA, breadcrumb
from pensunet.ui.graficas import barras_media_por_carrera


def _chart_top_facultad(tabla: pd.DataFrame):
    top = tabla.copy()
    top["etiqueta"] = (
        top["carrera"].astype(str)
        + " · "
        + top["id_asignatura"].astype(str)
        + " · "
        + top["nombre"].astype(str)
    )
    return (
        alt.Chart(top)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            y=alt.Y("etiqueta:N", sort="x", title=None),
            x=alt.X("tasa_aprobacion:Q", title="% de aprobación"),
            color=alt.Color(
                "clave:N",
                scale=alt.Scale(
                    domain=list(COLORES_CARRERA),
                    range=list(COLORES_CARRERA.values()),
                ),
                title="Carrera",
            ),
            tooltip=["carrera", "nombre", "tasa_aprobacion", "n_inscritos"],
        )
        .properties(height=420)
    )


def mostrar() -> None:
    breadcrumb()
    st.subheader("Materias de la Facultad")

    with st.container(border=True):
        st.markdown("**Top 15 con menor % de aprobación**")
        top = top_menor_aprobacion_facultad(15)
        st.altair_chart(_chart_top_facultad(top), width="stretch")
        st.dataframe(
            top.rename(
                columns={
                    "id_asignatura": "código",
                    "nombre": "materia",
                    "tasa_aprobacion": "% aprobación",
                    "n_inscritos": "inscritos",
                }
            ).drop(columns=["clave"], errors="ignore"),
            width="stretch",
            hide_index=True,
            alt="Top materias con menor aprobación en la facultad",
        )

    with st.container(border=True):
        st.markdown("**% de aprobación medio por carrera**")
        st.altair_chart(barras_media_por_carrera(), width="stretch")

    with st.container(border=True):
        st.markdown("**Materias compartidas entre carreras**")
        compartidas = materias_compartidas()
        st.dataframe(
            compartidas.rename(
                columns={
                    "id_asignatura": "código",
                    "nombre": "materia",
                    "n_carreras": "nº carreras",
                    "tasa_agregada": "% aprobación agregada",
                    "n_inscritos": "inscritos",
                }
            ),
            width="stretch",
            hide_index=True,
            column_config={
                "% aprobación agregada": st.column_config.ProgressColumn(
                    "% aprobación agregada",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.0f%%",
                ),
            },
            alt="Materias compartidas entre dos o más carreras",
        )
