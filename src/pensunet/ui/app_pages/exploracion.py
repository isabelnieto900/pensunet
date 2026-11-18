"""Página Exploración de datos (agregados; celdas pequeñas suprimidas)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pensunet.datos.programas import PROGRAMAS
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
from pensunet.ui.estilo import COLORES_CARRERA, PALETA_CATEGORICA


def _creditos_por_semestre(pensum: pd.DataFrame):
    import altair as alt

    df = pensum.copy()
    df["clasificacion"] = df["clasificacion"].fillna("Sin clasificar")
    agg = df.groupby(["semestre", "clasificacion"], as_index=False)["creditos"].sum()
    return (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X("semestre:O", title="Semestre"),
            y=alt.Y("creditos:Q", title="Créditos", stack="zero"),
            color=alt.Color(
                "clasificacion:N",
                scale=alt.Scale(range=list(PALETA_CATEGORICA)),
            ),
            tooltip=["semestre", "clasificacion", "creditos"],
        )
        .properties(height=260)
    )


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


def _histograma_tasas(tasas: pd.DataFrame, color: str):
    import altair as alt

    validas = tasas.loc[~tasas["sin_dato_suficiente"]].dropna(subset=["tasa_aprobacion"])
    return (
        alt.Chart(validas)
        .mark_bar(color=color)
        .encode(
            x=alt.X(
                "tasa_aprobacion:Q",
                bin=alt.Bin(maxbins=20),
                title="% de aprobación",
            ),
            y=alt.Y("count()", title="Materias"),
            tooltip=["count()"],
        )
        .properties(height=240)
    )


def _top_menor_tasa(tasas: pd.DataFrame, color: str):
    import altair as alt

    validas = tasas.loc[~tasas["sin_dato_suficiente"]].dropna(subset=["tasa_aprobacion"])
    top = validas.nsmallest(10, "tasa_aprobacion").copy()
    top["etiqueta"] = top["id_asignatura"].astype(str) + " · " + top["nombre"].astype(str)
    return (
        alt.Chart(top)
        .mark_bar(color=color, cornerRadiusEnd=3)
        .encode(
            y=alt.Y("etiqueta:N", sort="x", title=None),
            x=alt.X("tasa_aprobacion:Q", title="% de aprobación"),
            tooltip=["etiqueta", "tasa_aprobacion", "n_inscritos"],
        )
        .properties(height=280)
    )


def _barras_media_por_carrera():
    import altair as alt

    filas = []
    for clave in sorted(PROGRAMAS):
        tasas = tasas_agregadas(clave)
        validas = tasas.loc[~tasas["sin_dato_suficiente"]].dropna(
            subset=["tasa_aprobacion"]
        )
        if validas.empty:
            continue
        filas.append(
            {
                "programa": PROGRAMAS[clave].nombre,
                "clave": clave,
                "aprobación media": float(validas["tasa_aprobacion"].mean()),
            }
        )
    df = pd.DataFrame(filas)
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=3, size=28)
        .encode(
            y=alt.Y("programa:N", sort="-x", title=None),
            x=alt.X("aprobación media:Q", title="% de aprobación medio"),
            color=alt.Color(
                "clave:N",
                scale=alt.Scale(
                    domain=list(COLORES_CARRERA),
                    range=list(COLORES_CARRERA.values()),
                ),
                legend=None,
            ),
            tooltip=["programa", "aprobación media"],
        )
        .properties(height=220)
    )


def _estructura_por_semestre(clave: str):
    import altair as alt

    modelo = simulador_actual()
    assert modelo.red is not None
    ind = indicadores_cacheados(
        clave,
        modelo.red.grafo.number_of_nodes(),
        modelo.red.grafo.number_of_edges(),
        firma_sim(),
    )
    comp = complejidad_cacheada(
        clave,
        modelo.red.grafo.number_of_nodes(),
        modelo.red.grafo.number_of_edges(),
        firma_sim(),
    )
    filas = []
    for nodo, datos in modelo.red.grafo.nodes(data=True):
        codigo = int(nodo)
        filas.append(
            {
                "semestre": int(datos.get("semestre") or 0),
                "bloqueo": ind.factor_bloqueo.get(codigo, 0),
                "retraso": comp.retraso.get(codigo, 0),
                "criticidad": comp.complejidad_estructural.get(codigo, 0),
            }
        )
    df = pd.DataFrame(filas)
    agg = df.groupby("semestre", as_index=False)[
        ["bloqueo", "retraso", "criticidad"]
    ].mean()
    largo = agg.melt(id_vars="semestre", var_name="métrica", value_name="valor")
    return (
        alt.Chart(largo)
        .mark_bar()
        .encode(
            x=alt.X("semestre:O", title="Semestre"),
            y=alt.Y("valor:Q", title="Media"),
            color=alt.Color(
                "métrica:N",
                scale=alt.Scale(range=list(PALETA_CATEGORICA[:3])),
            ),
            tooltip=["semestre", "métrica", "valor"],
        )
        .properties(height=260)
    )


def mostrar() -> None:
    clave = clave_carrera()
    color = COLORES_CARRERA[clave]
    pensum = pensum_agregado(clave)
    tasas = tasas_agregadas(clave)
    modelo = simulador_actual()
    assert modelo.programa is not None

    st.subheader("Exploración de datos")
    st.caption(modelo.programa.nombre)

    with st.container(border=True):
        st.markdown("**Plan de estudios**")
        a1, a2 = st.columns(2)
        with a1:
            st.altair_chart(_creditos_por_semestre(pensum), width="stretch")
        with a2:
            st.dataframe(
                _prereqs_por_materia(modelo).head(12),
                width="stretch",
                hide_index=True,
                height=280,
                alt="Materias con más prerrequisitos",
            )

    with st.container(border=True):
        st.markdown("**Aprobación de materias**")
        b1, b2 = st.columns(2)
        with b1:
            st.altair_chart(_histograma_tasas(tasas, color), width="stretch")
        with b2:
            st.altair_chart(_top_menor_tasa(tasas, color), width="stretch")
        st.altair_chart(_barras_media_por_carrera(), width="stretch")

    with st.container(border=True):
        st.markdown("**Estructura del plan**")
        st.altair_chart(_estructura_por_semestre(clave), width="stretch")
        camino = camino_actual(modelo)
        assert modelo.red is not None
        nombres = [
            f"{c} ({modelo.red.grafo.nodes[c].get('nombre', '')})" for c in camino
        ]
        st.caption("Secuencia más larga: " + " → ".join(nombres))

    with st.container(border=True):
        st.markdown("**Tabla**")
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
            alt="Tabla de aprobación",
        )
        st.download_button(
            "Descargar CSV",
            data=vista.to_csv(index=False).encode("utf-8"),
            file_name=f"aprobacion_{clave}.csv",
            mime="text/csv",
            icon=":material/download:",
        )
