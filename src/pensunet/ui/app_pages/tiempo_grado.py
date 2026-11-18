"""Simulación Monte Carlo: tasas y parámetros editables + contraste con base."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pensunet.dominio.escenario import Escenario
from pensunet.simulacion.montecarlo import creditos_electivos_del_plan
from pensunet.ui.compartido import (
    N_SIM_RESUMEN,
    SEMILLA_BASE,
    clave_carrera,
    firma_sim,
    simulador_actual,
    simular_base,
    tope_semestres_por_plan,
)
from pensunet.ui.estilo import COLORES_CARRERA
from pensunet.ui.graficas import histograma_tiempos, histograma_tiempos_contraste
from pensunet.ui.navegacion import breadcrumb
from pensunet.ui.tablas import (
    tabla_tasas_del_grafo,
    tabla_tiempos,
    tasas_desde_editor,
)


def _asegurar_editor(clave: str, simulador) -> None:
    assert simulador.red is not None and simulador.tasas is not None
    if st.session_state.get("tasas_programa") != clave:
        st.session_state.tasas_programa = clave
        st.session_state.tasas_editor = tabla_tasas_del_grafo(
            simulador.red, simulador.tasas
        )
        st.session_state.tasas_base = st.session_state.tasas_editor.copy()
        st.session_state.pop("editor_tasas_sim", None)
        st.session_state.resultado_sim = None
        st.session_state.escenario_usado = None
        st.session_state.tasas_simuladas = None
        st.session_state.mensaje_sim = None
    if "tasas_editor" not in st.session_state:
        st.session_state.tasas_editor = tabla_tasas_del_grafo(
            simulador.red, simulador.tasas
        )
    if "tasas_base" not in st.session_state:
        st.session_state.tasas_base = st.session_state.tasas_editor.copy()
    if "resultado_sim" not in st.session_state:
        st.session_state.resultado_sim = None
        st.session_state.escenario_usado = None
        st.session_state.tasas_simuladas = None
        st.session_state.mensaje_sim = None


def _firma_tasas(tabla: pd.DataFrame) -> tuple[tuple[int, float | None], ...]:
    filas = []
    for fila in tabla.to_dict(orient="records"):
        valor = fila.get("tasa_aprobacion")
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            filas.append((int(fila["id"]), None))
        else:
            filas.append((int(fila["id"]), float(valor)))
    return tuple(sorted(filas))


def _ids_sin_tasa(tabla: pd.DataFrame) -> list[int]:
    faltan = []
    for fila in tabla.to_dict(orient="records"):
        valor = fila.get("tasa_aprobacion")
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            faltan.append(int(fila["id"]))
    return faltan


def _tabla_frenan(resultado, simulador, n: int = 10) -> pd.DataFrame:
    assert simulador.red is not None
    bloqueo = simulador.indicadores().factor_bloqueo
    filas = []
    for codigo, media in resultado.asignaturas_que_frenan(n):
        filas.append(
            {
                "id": codigo,
                "nombre": simulador.red.grafo.nodes[codigo].get("nombre", ""),
                "reprobaciones_por_estudiante": round(media, 3),
                "p_i": simulador.tasa_de(codigo),
                "bloqueo": bloqueo.get(codigo),
            }
        )
    return pd.DataFrame(filas)


def mostrar() -> None:
    clave = clave_carrera()
    if clave is None:
        st.info("Elige una carrera en el selector del sidebar.")
        return

    breadcrumb()
    simulador = simulador_actual()
    assert simulador.red is not None and simulador.programa is not None
    assert simulador.tasas is not None
    _asegurar_editor(clave, simulador)

    nominal = int(simulador.red.duracion_nominal)
    tope_default = tope_semestres_por_plan(nominal)
    color = COLORES_CARRERA[clave]
    base = simular_base(clave, N_SIM_RESUMEN, SEMILLA_BASE, firma_sim())

    st.subheader("Simulación")
    st.caption(
        f"{simulador.programa.nombre}. "
        "Edita tasas o parámetros y pulsa **Simular**. Los CSV no se modifican."
    )

    faltan = _ids_sin_tasa(st.session_state.tasas_editor)
    if faltan:
        st.warning(
            f"Faltan tasas para {len(faltan)} asignatura(s) del grafo "
            f"(p. ej. {', '.join(str(c) for c in faltan[:8])}"
            f"{'…' if len(faltan) > 8 else ''}). "
            "Complétalas en el editor o la simulación no podrá correr."
        )

    controles, resultados = st.columns([1, 1.45], gap="large")

    with controles:
        with st.form("form_simular", clear_on_submit=False, border=True):
            n_estudiantes = st.slider(
                "Estudiantes representativos",
                min_value=100,
                max_value=10_000,
                value=2_000,
                step=100,
            )
            semilla = st.number_input(
                "Semilla",
                min_value=0,
                value=SEMILLA_BASE,
                step=1,
            )
            with st.expander("Supuestos del escenario", expanded=False):
                st.caption(
                    "Cupo de electivas del plan por defecto. "
                    "Las electivas reprobadas no se repiten."
                )
                respetar = st.toggle("Respetar semestre recomendado", value=True)
                creditos = st.number_input(
                    "Créditos mínimos de electivas",
                    min_value=0,
                    max_value=48,
                    value=creditos_electivos_del_plan(simulador.red),
                    step=1,
                    help="0 = exigir todas las electivas del grafo.",
                )
                electivas_sin = st.toggle(
                    "Electivas sin reintento al reprobar",
                    value=True,
                )
                opciones = st.toggle(
                    "Cupos excluyentes (basta aprobar una opción)",
                    value=True,
                )
                max_sem = st.number_input(
                    "Tope de semestres",
                    min_value=10,
                    max_value=80,
                    value=tope_default,
                    step=1,
                    help="Por defecto: 1,5 × duración del plan.",
                )
                max_cred = st.number_input(
                    "Tope créditos/semestre (0 = sin tope)",
                    min_value=0,
                    max_value=40,
                    value=0,
                    step=1,
                )

            st.markdown("**Tasas de aprobación**")
            st.caption("Edita `tasa_aprobacion` entre 0 y 1.")
            editadas = st.data_editor(
                st.session_state.tasas_editor,
                width="stretch",
                hide_index=True,
                height=320,
                disabled=["id", "nombre", "semestre"],
                column_config={
                    "tasa_aprobacion": st.column_config.NumberColumn(
                        "% aprobación",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.01,
                        format="%.2f",
                    ),
                },
                key="editor_tasas_sim",
            )
            correr = st.form_submit_button(
                "Simular",
                type="primary",
                width="stretch",
                icon=":material/science:",
            )

        if st.button("Restablecer tasas al histórico", key="reset_tasas_sim"):
            st.session_state.tasas_editor = st.session_state.tasas_base.copy()
            st.session_state.pop("editor_tasas_sim", None)
            st.rerun()

        st.session_state.tasas_editor = editadas

        if correr:
            escenario = Escenario(
                n_estudiantes=int(n_estudiantes),
                semilla=int(semilla),
                respetar_semestre_recomendado=bool(respetar),
                creditos_electivas_minimos=(
                    None if int(creditos) == 0 else int(creditos)
                ),
                electivas_sin_reintento=bool(electivas_sin),
                max_semestres=int(max_sem),
                max_creditos_semestre=(
                    None if int(max_cred) == 0 else int(max_cred)
                ),
                opciones_excluyentes=bool(opciones),
            )
            with st.spinner(
                f"Simulando {n_estudiantes} trayectorias (semilla {semilla})…"
            ):
                try:
                    tasas_uso = tasas_desde_editor(simulador.tasas, editadas)
                    resultado = simulador.simular(escenario, tasas=tasas_uso)
                except (ValueError, RuntimeError) as error:
                    st.session_state.mensaje_sim = ("error", str(error))
                    st.session_state.resultado_sim = None
                else:
                    st.session_state.resultado_sim = resultado
                    st.session_state.escenario_usado = escenario
                    st.session_state.tasas_simuladas = _firma_tasas(editadas)
                    n_censurados = int(getattr(resultado, "n_censurados", 0) or 0)
                    tope = getattr(resultado, "tope_semestres", escenario.max_semestres)
                    mensaje = (
                        "Simulación terminada: tiempo esperado ≈ "
                        f"**{resultado.media:.2f}** semestres "
                        f"(E(X) ≈ {resultado.media:.2f})."
                    )
                    if n_censurados:
                        mensaje += (
                            f" **{n_censurados}** trayectoria(s) no se graduaron "
                            f"antes de {tope} semestres (censuradas en el tope)."
                        )
                        st.session_state.mensaje_sim = ("warning", mensaje)
                    else:
                        st.session_state.mensaje_sim = ("success", mensaje)
                    st.toast(
                        f"Tiempo esperado ≈ {resultado.media:.2f} semestres"
                    )

    with resultados:
        mensaje_sim = st.session_state.get("mensaje_sim")
        if mensaje_sim:
            tipo, texto = mensaje_sim
            if tipo == "success":
                st.success(texto)
            elif tipo == "warning":
                st.warning(texto)
            elif tipo == "error":
                st.error(texto)

        resultado = st.session_state.resultado_sim
        firma_actual = _firma_tasas(st.session_state.tasas_editor)
        if (
            resultado is not None
            and st.session_state.get("tasas_simuladas") is not None
            and firma_actual != st.session_state.tasas_simuladas
            and not correr
        ):
            st.info(
                "Hay tasas editadas que aún no se han simulado. "
                "Pulsa **Simular** para actualizar el tiempo esperado y la gráfica."
            )

        with st.container(border=True):
            if resultado is None:
                st.markdown("**Escenario base (histórico cacheado)**")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(
                    "Semestres esperados",
                    f"{base.media:.2f}",
                    border=True,
                    help="E(X): promedio del tiempo hasta el grado en la simulación.",
                )
                m2.metric(
                    "Graduados a tiempo (+2)",
                    f"{100 * base.tasa_grado_en(nominal + 2):.0f}%",
                    border=True,
                    help=(
                        "Porcentaje con X ≤ N+2, donde N es la duración "
                        "nominal del plan en semestres."
                    ),
                )
                m3.metric(
                    "Dispersión",
                    f"{base.desviacion:.2f}",
                    border=True,
                    help="Desviación estándar de X (semestres).",
                )
                m4.metric(
                    "Rango de semestres",
                    f"{min(base.tiempos)} – {max(base.tiempos)}",
                    border=True,
                    help="Mínimo y máximo de X en la muestra simulada.",
                )
                st.altair_chart(
                    histograma_tiempos(base.tiempos, nominal, color),
                    width="stretch",
                )
                st.caption(
                    "Ajusta tasas o parámetros a la izquierda y pulsa **Simular** "
                    "para contrastar con este escenario base."
                )
            else:
                usado = st.session_state.escenario_usado
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(
                    "Semestres (base)",
                    f"{base.media:.2f}",
                    border=True,
                    help=(
                        "E(X) del escenario histórico cacheado "
                        "(tasas sin editar)."
                    ),
                )
                m2.metric(
                    "Semestres (escenario)",
                    f"{resultado.media:.2f}",
                    delta=f"{resultado.media - base.media:+.2f}",
                    border=True,
                    help="E(X) con las tasas y parámetros que acabas de simular.",
                )
                m3.metric(
                    "A tiempo base (+2)",
                    f"{100 * base.tasa_grado_en(nominal + 2):.0f}%",
                    border=True,
                    help="Porcentaje con X ≤ N+2 en el escenario base.",
                )
                delta_pp = 100 * (
                    resultado.tasa_grado_en(nominal + 2)
                    - base.tasa_grado_en(nominal + 2)
                )
                m4.metric(
                    "A tiempo escenario (+2)",
                    f"{100 * resultado.tasa_grado_en(nominal + 2):.0f}%",
                    delta=f"{delta_pp:+.1f} pp",
                    border=True,
                    help="Porcentaje con X ≤ N+2 en el escenario simulado.",
                )
                st.altair_chart(
                    histograma_tiempos_contraste(
                        base.tiempos,
                        resultado.tiempos,
                        nominal,
                    ),
                    width="stretch",
                )
                if usado is not None:
                    st.caption(
                        f"n = {usado.n_estudiantes}, semilla = {usado.semilla}, "
                        f"tope = {usado.max_semestres} semestres. "
                        "Línea dorada: duración nominal del plan."
                    )

                extras = st.container(horizontal=True, gap="medium")
                with extras:
                    st.metric(
                        "Dispersión",
                        f"{resultado.desviacion:.2f}",
                        border=True,
                        help="Desviación estándar de X (semestres).",
                    )
                    st.metric(
                        "Rango de semestres",
                        f"{min(resultado.tiempos)} – {max(resultado.tiempos)}",
                        border=True,
                        help="Mínimo y máximo de X en la muestra simulada.",
                    )
                    st.metric(
                        "Sin grado a tiempo",
                        int(getattr(resultado, "n_censurados", 0) or 0),
                        border=True,
                        help=(
                            "Trayectorias censuradas: no alcanzan el grado "
                            "antes del tope de semestres."
                        ),
                    )
                    st.metric(
                        f"Graduados en ≤ {nominal}",
                        f"{100 * resultado.tasa_grado_en(nominal):.0f}%",
                        border=True,
                        help=f"Porcentaje con X ≤ N (N = {nominal}).",
                    )

                if getattr(resultado, "reprobaciones", None):
                    st.markdown("**Materias que más frenan (simulación)**")
                    st.dataframe(
                        _tabla_frenan(resultado, simulador),
                        width="stretch",
                        hide_index=True,
                    )
                with st.expander("Frecuencias del tiempo hasta el grado"):
                    st.dataframe(
                        tabla_tiempos(resultado),
                        width="stretch",
                        hide_index=True,
                    )
