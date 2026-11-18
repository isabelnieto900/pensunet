"""Plan de estudios: red D3 interactiva + créditos por semestre."""

from __future__ import annotations

import streamlit as st

from pensunet.dominio.visualizacion import ESCALAS_COLOR
from pensunet.ui.compartido import (
    camino_actual,
    clave_carrera,
    firma_sim,
    html_red_cacheado,
    indicadores_cacheados,
    pensum_agregado,
    simulador_actual,
)
from pensunet.ui.graficas import creditos_por_semestre
from pensunet.ui.navegacion import breadcrumb
from pensunet.ui.tablas import tabla_resumen_red

_MODOS_COLOR = {
    "area": "Área del plan",
    "tasa": "% aprobación",
    "complejidad": "Criticidad",
}


def _leyenda_color(modo: str, simulador) -> None:
    if modo == "area":
        return
    paradas = ", ".join(ESCALAS_COLOR[modo])
    if modo == "tasa":
        izquierda, derecha = "p = 0", "p = 1"
        nota = "Gris: sin histórico suficiente (no se completa con 0 ni 1)."
    else:
        valores = list(simulador.complejidad().complejidad_estructural.values())
        izquierda, derecha = f"h = {min(valores)}", f"h = {max(valores)}"
        nota = "h(v) = retraso + bloqueo (Curricular Analytics)."
    # Altura/ancho en línea: la barra debe verse aunque falle el CSS global.
    st.html(
        f'<div class="pensunet-leyenda" style="display:flex;align-items:center;'
        f'gap:0.75rem;margin:0.35rem 0 0.15rem 0;font-size:0.88rem;font-weight:600">'
        f"<span>{izquierda}</span>"
        f'<div class="pensunet-degradado" style="flex:1 1 auto;min-width:12rem;'
        f"height:14px;border-radius:7px;border:1px solid #98999A;"
        f'background:linear-gradient(90deg,{paradas})"></div>'
        f"<span>{derecha}</span></div>"
        f'<p class="pensunet-nota" style="margin:0 0 0.55rem 0;font-size:0.8rem;'
        f'opacity:0.85">{nota}</p>'
    )


def mostrar() -> None:
    clave = clave_carrera()
    if clave is None:
        st.info("Elige una carrera en el selector del sidebar.")
        return

    breadcrumb()
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
    cuellos = tuple(int(c) for c in indicadores.cuellos_de_botella)
    camino = camino_actual(simulador)

    st.subheader("Plan de estudios")
    st.caption(
        f"{simulador.programa.nombre} · {resumen['asignaturas']} materias · "
        f"{resumen['aristas']} prerrequisitos. "
        "Clic en una materia para fijar el detalle; rueda o +/− para zoom; "
        "arrastra el fondo para desplazar."
    )

    barra = st.container(horizontal=True, gap="medium", vertical_alignment="center")
    with barra:
        modo_color = (
            st.segmented_control(
                "Color de las cajas",
                options=list(_MODOS_COLOR),
                format_func=lambda k: _MODOS_COLOR[k],
                default="area",
                key="red_modo_color",
            )
            or "area"
        )
        ver_cuellos = st.toggle("Cuellos de botella", value=False, key="red_toggle_cuellos")
        ver_camino = st.toggle("Camino más largo", value=False, key="red_toggle_camino")
        oscuro = st.toggle("Fondo oscuro de la red", key="modo_oscuro")

    _leyenda_color(modo_color, simulador)

    if ver_cuellos and cuellos:
        nombres = []
        for codigo in cuellos:
            nombre = simulador.red.grafo.nodes[codigo].get("nombre", "")
            nombres.append(f"**{codigo}** · {nombre}")
        st.info("Cuellos de botella: " + " · ".join(nombres))
    if ver_camino and camino:
        nombres_camino = [
            f"{codigo} ({simulador.red.grafo.nodes[codigo].get('nombre', '')})"
            for codigo in camino
        ]
        st.caption("Camino más largo: " + " → ".join(nombres_camino))

    with st.container(border=True):
        html = html_red_cacheado(
            clave,
            int(resumen["asignaturas"]),
            int(resumen["aristas"]),
            oscuro,
            cuellos if ver_cuellos else (),
            camino if ver_camino else (),
            True,
            modo_color=modo_color,
            _firma=firma_sim(),
        )
        st.iframe(
            html,
            height=820,
            alt="Red interactiva de prerrequisitos del plan de estudios",
        )

    with st.container(border=True):
        st.markdown("**Créditos por semestre**")
        pensum = pensum_agregado(clave)
        st.altair_chart(creditos_por_semestre(pensum), width="stretch")

    if simulador.red.reglas_aplicadas:
        with st.expander("Ajustes documentados del plan", expanded=False):
            for nota in simulador.red.reglas_aplicadas:
                st.markdown(f"- {nota}")
    if simulador.red.inconsistencias:
        with st.expander("Inconsistencias del extracto", expanded=False):
            for nota in simulador.red.inconsistencias:
                st.markdown(f"- {nota}")
