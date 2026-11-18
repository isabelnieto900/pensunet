"""Gráficas y filas KPI reutilizadas por el dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pensunet.datos.programas import PROGRAMAS
from pensunet.ui.compartido import (
    complejidad_cacheada,
    firma_sim,
    kpis_carrera,
    pensum_agregado,
    simulador_actual,
    tasas_agregadas,
)
from pensunet.ui.estilo import COLORES_CARRERA, PALETA_CATEGORICA, tarjeta_kpi


def fila_kpis(titulo: str, kpis: dict, *, es_facultad: bool = False) -> None:
    st.markdown(f"**{titulo}**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        tarjeta_kpi(
            "Semestres esperados",
            f"{float(kpis['ex']):.2f}",
            ayuda=(
                "E(X): promedio del tiempo hasta el grado en la simulación "
                "Monte Carlo (no es un promedio histórico de egresados reales)."
            ),
        )
    with c2:
        tarjeta_kpi(
            "Graduados a tiempo (+2)",
            f"{100 * float(kpis['pct_nominal_mas_2']):.0f}%",
            ayuda=(
                "Porcentaje con X ≤ N+2, donde N es la duración "
                "nominal del plan en semestres."
            ),
        )
    with c3:
        etiqueta = "Materias / créditos Σ" if es_facultad else "Materias / créditos"
        tarjeta_kpi(etiqueta, f"{kpis['materias']} / {kpis['creditos']}")
    with c4:
        tp = kpis["tasa_ponderada"]
        tarjeta_kpi(
            "% aprobación",
            "—" if tp is None else f"{100 * float(tp):.0f}%",
            ayuda="Promedio real de aprobación OATI, ponderado por inscritos.",
        )


def histograma_tiempos(tiempos: tuple[int, ...], nominal: int, color: str):
    import altair as alt

    df = pd.DataFrame({"semestres": list(tiempos)})
    conteo = df.value_counts().reset_index(name="estudiantes_simulados")
    base = (
        alt.Chart(conteo)
        .mark_bar(color=color, cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X("semestres:O", title="Semestres hasta graduarse"),
            y=alt.Y("estudiantes_simulados:Q", title="Estudiantes simulados"),
            tooltip=["semestres", "estudiantes_simulados"],
        )
    )
    linea = (
        alt.Chart(pd.DataFrame({"nominal": [nominal]}))
        .mark_rule(color="#FDB400", strokeWidth=2.5)
        .encode(x="nominal:O")
    )
    return (base + linea).properties(height=300)


def barras_frenan(clave: str):
    import altair as alt

    modelo = simulador_actual()
    assert modelo.red is not None
    comp = complejidad_cacheada(
        clave,
        modelo.red.grafo.number_of_nodes(),
        modelo.red.grafo.number_of_edges(),
        firma_sim(),
    )
    filas = []
    for codigo, h in sorted(
        comp.complejidad_estructural.items(),
        key=lambda par: (-par[1], par[0]),
    )[:5]:
        datos = modelo.red.grafo.nodes[codigo]
        semestre = datos.get("semestre")
        nombre = datos.get("nombre", "")
        filas.append(
            {
                "materia": f"S{semestre} · {nombre}",
                "semestre": int(semestre) if semestre is not None else None,
                "criticidad": int(h),
            }
        )
    df = pd.DataFrame(filas)
    return (
        alt.Chart(df)
        .mark_bar(color=COLORES_CARRERA[clave], cornerRadiusEnd=4)
        .encode(
            y=alt.Y("materia:N", sort="-x", title=None),
            x=alt.X("criticidad:Q", title="Criticidad en el plan"),
            tooltip=["materia", "semestre", "criticidad"],
        )
        .properties(height=300)
    )


def comparacion_carreras():
    """Barras de E(X), % a tiempo y criticidad total por carrera."""
    import altair as alt

    filas = []
    for clave in sorted(PROGRAMAS):
        kpis = kpis_carrera(clave)
        filas.append(
            {
                "programa": kpis["nombre"],
                "clave": clave,
                "Semestres esperados": float(kpis["ex"]),
                "% a tiempo (+2)": 100 * float(kpis["pct_nominal_mas_2"]),
                "Criticidad total": float(kpis.get("criticidad_total") or 0),
            }
        )
    df = pd.DataFrame(filas)
    color = alt.Color(
        "clave:N",
        scale=alt.Scale(
            domain=list(COLORES_CARRERA),
            range=list(COLORES_CARRERA.values()),
        ),
        legend=None,
    )
    chart_ex = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=42)
        .encode(
            x=alt.X("programa:N", title=None, sort=sorted(df["programa"])),
            y=alt.Y("Semestres esperados:Q", title="Semestres"),
            color=color,
            tooltip=["programa", "Semestres esperados"],
        )
        .properties(height=260, title="Semestres esperados")
    )
    chart_pct = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=42)
        .encode(
            x=alt.X("programa:N", title=None, sort=sorted(df["programa"])),
            y=alt.Y("% a tiempo (+2):Q", title="%"),
            color=color,
            tooltip=["programa", "% a tiempo (+2)"],
        )
        .properties(height=260, title="% a tiempo (+2)")
    )
    chart_crit = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=42)
        .encode(
            x=alt.X("programa:N", title=None, sort=sorted(df["programa"])),
            y=alt.Y("Criticidad total:Q", title="Criticidad"),
            color=color,
            tooltip=["programa", "Criticidad total"],
        )
        .properties(height=260, title="Criticidad total del plan")
    )
    return chart_ex, chart_pct, chart_crit


def creditos_por_semestre(pensum: pd.DataFrame):
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


def histograma_tasas(tasas: pd.DataFrame, color: str):
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


def top_menor_tasa(tasas: pd.DataFrame, color: str, n: int = 10):
    import altair as alt

    validas = tasas.loc[~tasas["sin_dato_suficiente"]].dropna(subset=["tasa_aprobacion"])
    top = validas.nsmallest(n, "tasa_aprobacion").copy()
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


def barras_media_por_carrera():
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


def histograma_tiempos_contraste(
    tiempos_base: tuple[int, ...],
    tiempos_escenario: tuple[int, ...],
    nominal: int,
):
    """Histogramas superpuestos base vs escenario (Altair)."""
    import altair as alt

    filas = [{"semestres": s, "escenario": "Base"} for s in tiempos_base]
    filas.extend(
        {"semestres": s, "escenario": "Escenario"} for s in tiempos_escenario
    )
    df = pd.DataFrame(filas)
    conteo = (
        df.groupby(["semestres", "escenario"], as_index=False)
        .size()
        .rename(columns={"size": "estudiantes"})
    )
    barras = (
        alt.Chart(conteo)
        .mark_bar(opacity=0.65, cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X("semestres:O", title="Semestres hasta graduarse"),
            y=alt.Y("estudiantes:Q", title="Estudiantes simulados"),
            color=alt.Color(
                "escenario:N",
                scale=alt.Scale(
                    domain=["Base", "Escenario"],
                    range=["#98999A", "#8C1919"],
                ),
                title=None,
            ),
            xOffset="escenario:N",
            tooltip=["semestres", "escenario", "estudiantes"],
        )
    )
    linea = (
        alt.Chart(pd.DataFrame({"nominal": [nominal]}))
        .mark_rule(color="#FDB400", strokeWidth=2.5)
        .encode(x="nominal:O")
    )
    return (barras + linea).properties(height=320)


def pensum_de(clave: str) -> pd.DataFrame:
    return pensum_agregado(clave)
