"""Panorama de la Facultad de Ciencias Matemáticas y Naturales (FCMN)."""

from __future__ import annotations

import streamlit as st

from pensunet.datos.programas import PROGRAMAS
from pensunet.ui.compartido import definir_selector, kpis_carrera, kpis_facultad
from pensunet.ui.estilo import COLORES_CARRERA, breadcrumb, tarjeta_kpi
from pensunet.ui.graficas import comparacion_carreras, fila_kpis


def _tarjeta_carrera(clave: str) -> None:
    kpis = kpis_carrera(clave)
    color = COLORES_CARRERA[clave]
    # Combinaciones permitidas: blanco sobre rojo; negro sobre dorado/otros.
    texto = "#FFFFFF" if clave == "fisica" else "#000000"
    with st.container(border=True):
        st.markdown(
            f'<p style="font-family:Titillium Web,Hind,sans-serif;font-size:1.15rem;'
            f'font-weight:700;color:{color};margin:0 0 .4rem 0">{kpis["nombre"]}</p>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            tarjeta_kpi(
                "Semestres esperados",
                f"{float(kpis['ex']):.2f}",
                ayuda="E(X): promedio del tiempo hasta el grado en la simulación.",
            )
        with c2:
            tarjeta_kpi(
                "Graduados a tiempo (+2)",
                f"{100 * float(kpis['pct_nominal_mas_2']):.0f}%",
                ayuda=(
                    "Porcentaje con X ≤ N+2, donde N es la duración "
                    "nominal del plan."
                ),
            )
        st.caption(f"{kpis['materias']} materias · {kpis['creditos']} créditos")
        if st.button(
            "Ver carrera",
            key=f"ver_{clave}",
            type="primary",
            width="stretch",
            icon=":material/arrow_forward:",
        ):
            definir_selector(clave)
            st.rerun()
        del texto  # tipografía de marca ya aplicada en el título


def mostrar() -> None:
    breadcrumb()
    st.subheader("Panorama")
    fac = kpis_facultad()

    with st.container(border=True):
        fila_kpis(
            "Facultad de Ciencias Matemáticas y Naturales",
            fac,
            es_facultad=True,
        )

    st.markdown("**Carreras**")
    cols = st.columns(2, gap="medium")
    for i, clave in enumerate(sorted(PROGRAMAS)):
        with cols[i % 2]:
            _tarjeta_carrera(clave)

    with st.container(border=True):
        st.markdown("**Comparación entre programas**")
        c_ex, c_pct, c_crit = comparacion_carreras()
        a, b, c = st.columns(3, gap="medium")
        with a:
            st.altair_chart(c_ex, width="stretch")
        with b:
            st.altair_chart(c_pct, width="stretch")
        with c:
            st.altair_chart(c_crit, width="stretch")
