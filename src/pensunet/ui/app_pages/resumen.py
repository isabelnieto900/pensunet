"""Resumen de una carrera (nivel carrera)."""

from __future__ import annotations

import streamlit as st

from pensunet.ui.compartido import clave_carrera, kpis_carrera
from pensunet.ui.estilo import breadcrumb
from pensunet.ui.graficas import barras_frenan, fila_kpis, histograma_tiempos


def mostrar() -> None:
    clave = clave_carrera()
    if clave is None:
        st.info("Elige una carrera en el selector del sidebar.")
        return
    breadcrumb()
    kpis = kpis_carrera(clave)
    st.subheader("Resumen")

    with st.container(border=True):
        fila_kpis(str(kpis["nombre"]), kpis)

    g1, g2 = st.columns(2, gap="medium")
    with g1:
        with st.container(border=True):
            st.markdown("**Distribución simulada del tiempo hasta graduarse**")
            st.caption(
                "Monte Carlo (estudiantes simulados). La línea dorada es la "
                "duración del plan."
            )
            st.altair_chart(
                histograma_tiempos(
                    kpis["tiempos"],  # type: ignore[arg-type]
                    int(kpis["nominal"]),
                    str(kpis["color"]),
                ),
                width="stretch",
            )
    with g2:
        with st.container(border=True):
            st.markdown("**Materias que más frenan**")
            st.caption("Top 5 por criticidad estructural (con semestre).")
            st.altair_chart(barras_frenan(clave), width="stretch")
