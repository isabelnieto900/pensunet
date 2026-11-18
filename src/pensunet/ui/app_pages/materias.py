"""Materias de una carrera: aprobación, estructura e indicadores."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pensunet.ui.compartido import (
    camino_actual,
    clave_carrera,
    complejidad_cacheada,
    firma_sim,
    indicadores_cacheados,
    pensum_agregado,
    simulador_actual,
    tasas_agregadas,
)
from pensunet.ui.estilo import COLORES_CARRERA, PALETA_CATEGORICA, breadcrumb
from pensunet.ui.graficas import histograma_tasas, top_menor_tasa
from pensunet.ui.tablas import tabla_indicadores, tabla_resumen_red


def _prereqs_por_materia(simulador) -> pd.DataFrame:
    assert simulador.red is not None
    filas = []
    for nodo, datos in simulador.red.grafo.nodes(data=True):
        filas.append(
            {
                "código": int(nodo),
                "materia": datos.get("nombre", ""),
                "semestre": datos.get("semestre"),
                "nº prerrequisitos": int(simulador.red.grafo.in_degree(nodo)),
            }
        )
    return pd.DataFrame(filas).sort_values("nº prerrequisitos", ascending=False)


def _estructura_por_semestre(clave: str, tabla: pd.DataFrame):
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
        .properties(height=260)
    )


def mostrar() -> None:
    clave = clave_carrera()
    if clave is None:
        st.info("Elige una carrera en el selector del sidebar.")
        return
    breadcrumb()
    color = COLORES_CARRERA[clave]
    pensum = pensum_agregado(clave)
    tasas = tasas_agregadas(clave)
    modelo = simulador_actual()
    assert modelo.red is not None and modelo.programa is not None
    resumen = tabla_resumen_red(modelo.red)
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
    tabla_ind = tabla_indicadores(modelo.red, indicadores, complejidad)
    camino = camino_actual(modelo)
    cuellos = list(indicadores.cuellos_de_botella)

    st.subheader("Materias")
    st.caption(modelo.programa.nombre)

    with st.container(border=True):
        st.markdown("**Aprobación**")
        b1, b2 = st.columns(2)
        with b1:
            st.altair_chart(histograma_tasas(tasas, color), width="stretch")
        with b2:
            st.altair_chart(top_menor_tasa(tasas, color, n=10), width="stretch")

    with st.container(border=True):
        st.markdown("**Materias con más prerrequisitos**")
        st.dataframe(
            _prereqs_por_materia(modelo).head(12),
            width="stretch",
            hide_index=True,
            height=280,
            alt="Materias con más prerrequisitos",
        )

    with st.container(border=True):
        st.markdown("**Bloqueo, retraso y criticidad por semestre**")
        st.altair_chart(_estructura_por_semestre(clave, tabla_ind), width="stretch")

    izq, der = st.columns(2, gap="medium")
    with izq:
        with st.container(border=True):
            st.markdown("**Camino más largo**")
            pasos = [
                {
                    "orden": i + 1,
                    "código": c,
                    "materia": modelo.red.grafo.nodes[c].get("nombre", ""),
                    "semestre": modelo.red.grafo.nodes[c].get("semestre"),
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
    with der:
        with st.container(border=True):
            st.markdown("**Cuellos de botella**")
            if not cuellos:
                st.write("Ninguno según los umbrales actuales.")
            else:
                filas = []
                for c in cuellos:
                    datos = modelo.red.grafo.nodes[c]
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

    with st.container(border=True):
        st.markdown("**Tabla filtrable**")
        semestres = sorted({int(s) for s in pensum["semestre"].dropna().tolist()})
        f1, f2 = st.columns(2)
        with f1:
            filtro_sem = st.multiselect("Semestre", options=semestres, default=semestres)
        with f2:
            clases = sorted({str(c) for c in pensum["clasificacion"].dropna().unique()})
            filtro_cls = st.multiselect("Tipo", options=clases, default=clases)
        ids_ok = set(
            pensum.loc[
                pensum["semestre"].isin(filtro_sem)
                & pensum["clasificacion"].isin(filtro_cls),
                "id_asignatura",
            ].astype(int)
        )
        vista = tasas.loc[tasas["id_asignatura"].astype(int).isin(ids_ok)].copy()
        vista = vista.rename(
            columns={
                "id_asignatura": "código",
                "nombre": "materia",
                "n_inscritos": "inscritos",
                "n_aprobados": "aprobados",
                "tasa_aprobacion": "% aprobación",
                "sin_dato_suficiente": "sin dato suficiente",
            }
        )
        st.dataframe(
            vista,
            width="stretch",
            hide_index=True,
            height=360,
            column_config={
                "% aprobación": st.column_config.ProgressColumn(
                    "% aprobación",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.0f%%",
                ),
                "inscritos": st.column_config.NumberColumn("inscritos", format="%d"),
                "aprobados": st.column_config.NumberColumn("aprobados", format="%d"),
            },
            alt="Tabla de aprobación con celdas pequeñas suprimidas",
        )
        st.download_button(
            "Descargar CSV",
            data=vista.to_csv(index=False).encode("utf-8"),
            file_name=f"aprobacion_{clave}.csv",
            mime="text/csv",
            icon=":material/download:",
        )
