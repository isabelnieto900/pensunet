"""Página Indicadores: tablas y rankings (sin repetir el mapa D3)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pensunet.ui.compartido import (
    camino_actual,
    clave_carrera,
    complejidad_cacheada,
    firma_sim,
    indicadores_cacheados,
    simulador_actual,
)
from pensunet.ui.estilo import COLORES_CARRERA, PALETA_CATEGORICA
from pensunet.ui.tablas import tabla_indicadores, tabla_resumen_red


def _barras_por_semestre(clave: str, tabla: pd.DataFrame):
    import altair as alt

    agg = (
        tabla.groupby("semestre", as_index=False)[["bloqueo", "retraso", "complejidad"]]
        .mean(numeric_only=True)
        .melt(id_vars="semestre", var_name="métrica", value_name="valor")
    )
    return (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X("semestre:O", title="Semestre"),
            y=alt.Y("valor:Q", title="Media"),
            color=alt.Color(
                "métrica:N",
                scale=alt.Scale(range=list(PALETA_CATEGORICA[:3])),
                title=None,
            ),
            tooltip=["semestre", "métrica", "valor"],
        )
        .properties(height=280)
    )


def mostrar() -> None:
    clave = clave_carrera()
    simulador = simulador_actual()
    assert simulador.red is not None
    assert simulador.programa is not None
    resumen = tabla_resumen_red(simulador.red)
    indicadores = indicadores_cacheados(
        clave,
        int(resumen["asignaturas"]),
        int(resumen["aristas"]),
        firma_sim(),
    )
    complejidad = complejidad_cacheada(
        clave,
        int(resumen["asignaturas"]),
        int(resumen["aristas"]),
        firma_sim(),
    )
    tabla = tabla_indicadores(simulador.red, indicadores, complejidad)
    camino = camino_actual(simulador)
    cuellos = list(indicadores.cuellos_de_botella)

    st.subheader("Indicadores")
    st.caption(f"{simulador.programa.nombre} · cifras del grafo (no es el mapa interactivo)")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Criticidad total", complejidad.complejidad_total, border=True)
    m2.metric("Cuellos de botella", len(cuellos), border=True)
    m3.metric("Largo del camino", len(camino), border=True)
    m4.metric("Materias", resumen["asignaturas"], border=True)

    izq, der = st.columns(2, gap="medium")
    with izq:
        with st.container(border=True):
            st.markdown("**Cuellos de botella**")
            if not cuellos:
                st.write("Ninguno según los umbrales actuales.")
            else:
                filas = []
                for c in cuellos:
                    datos = simulador.red.grafo.nodes[c]
                    filas.append(
                        {
                            "código": c,
                            "materia": datos.get("nombre", ""),
                            "semestre": datos.get("semestre"),
                            "bloqueo": indicadores.factor_bloqueo.get(c),
                        }
                    )
                st.dataframe(
                    pd.DataFrame(filas),
                    width="stretch",
                    hide_index=True,
                    alt="Cuellos de botella",
                )
    with der:
        with st.container(border=True):
            st.markdown("**Camino más largo**")
            pasos = [
                {
                    "orden": i + 1,
                    "código": c,
                    "materia": simulador.red.grafo.nodes[c].get("nombre", ""),
                    "semestre": simulador.red.grafo.nodes[c].get("semestre"),
                }
                for i, c in enumerate(camino)
            ]
            st.dataframe(
                pd.DataFrame(pasos),
                width="stretch",
                hide_index=True,
                height=260,
                alt="Camino más largo",
            )

    with st.container(border=True):
        st.markdown("**Promedio por semestre**")
        st.altair_chart(_barras_por_semestre(clave, tabla), width="stretch")

    with st.container(border=True):
        st.markdown("**Tabla por materia**")
        vista = tabla.rename(
            columns={
                "id": "código",
                "nombre": "materia",
                "clasificacion": "tipo",
                "posponimiento": "posposición",
                "intermediacion": "intermediación",
                "cuello_de_botella": "cuello",
                "complejidad": "criticidad",
            }
        )
        st.dataframe(
            vista,
            width="stretch",
            hide_index=True,
            height=420,
            alt="Indicadores por materia",
        )

    del COLORES_CARRERA  # import kept for possible future sparkline colors
