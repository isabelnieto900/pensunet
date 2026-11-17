"""Interfaz Streamlit de Pensunet: red, indicadores y tiempo de grado."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

from pensunet import SimuladorPensum, __version__
from pensunet.datos.programas import PROGRAMAS
from pensunet.dominio.escenario import Escenario
from pensunet.dominio.indicadores import (
    UMBRAL_ENTRADA_CUELLO,
    UMBRAL_SALIDA_CUELLO,
    UMBRAL_TOTAL_CUELLO,
    IndicadoresTopologicos,
    camino_mas_largo,
)
from pensunet.dominio.visualizacion import ESCALAS_COLOR, colores_por_valor, html_de_la_red
from pensunet.ui.tablas import (
    tabla_indicadores,
    tabla_resumen_red,
    tabla_tasas_del_grafo,
    tabla_tiempos,
    tasa_media,
    tasas_desde_editor,
    tasas_por_asignatura,
)

# Modos de color de las cajas en la vista de indicadores.
_MODOS_COLOR = {
    "area": "Área del plan",
    "tasa": "Tasa de aprobación p_i",
    "complejidad": "Complejidad estructural",
}

_PAGINAS = (
    "Red de prerrequisitos",
    "Indicadores",
    "Tiempo de grado",
)

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Source+Sans+3:wght@400;600;700&display=swap');
html, body, [class*="css"] {
  font-family: "Source Sans 3", "Segoe UI", sans-serif;
}
.pensunet-marca {
  font-family: Fraunces, Georgia, serif !important;
  font-size: 2.55rem;
  font-weight: 700;
  margin: 0 0 0.2rem 0;
  line-height: 1.05;
  letter-spacing: -0.02em;
  color: var(--text-color) !important;
}
.pensunet-lema {
  font-size: 1.05rem;
  margin: 0 0 1.25rem 0;
  max-width: 42rem;
  color: var(--text-color);
  opacity: 0.78;
}
div[data-testid="stMetric"] {
  background: color-mix(in srgb, var(--background-color) 80%, var(--text-color) 6%);
  border: 1px solid color-mix(in srgb, var(--text-color) 12%, transparent);
  border-radius: 6px;
  padding: 0.55rem 0.75rem;
}
iframe {
  border: none !important;
  background: transparent !important;
  overflow: hidden !important;
}
p.pensunet-marca {
  font-size: 2.55rem !important;
  border-bottom: 3px solid var(--primary-color);
  display: inline-block;
  padding-bottom: 0.15rem;
}
div[data-testid="stMetricLabel"] p {
  white-space: normal !important;
  font-size: 0.82rem;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  opacity: 0.8;
}
div[data-testid="stMetricValue"] {
  font-size: 1.75rem;
  font-variant-numeric: tabular-nums;
}
.pensunet-leyenda {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.85rem;
  max-width: 28rem;
}
.pensunet-degradado {
  flex: 1;
  height: 0.7rem;
  border-radius: 999px;
}
.pensunet-nota {
  font-size: 0.8rem;
  opacity: 0.75;
  margin: 0.15rem 0 0.6rem 0;
}
div[data-testid="stIFrame"],
div[data-testid="stIFrame"] > iframe {
  border: none !important;
  overflow: hidden !important;
}
</style>
"""


def _mostrar_red_html(html: str) -> None:
    """Muestra la red interactiva (iframe sin barra de scroll interna)."""
    st.iframe(html, height=560)


def _tema_oscuro() -> bool:
    try:
        return str(st.context.theme.type).lower() == "dark"
    except Exception:
        return False


def _firma_codigo_sim() -> str:
    """Invalida la caché si cambia el Monte Carlo o el resultado."""
    firmas = []
    for relativo in (
        "simulacion/montecarlo_molontay.py",
        "simulacion/estrategia.py",
        "dominio/escenario.py",
        "datos/ajustes.py",
    ):
        ruta = Path(__file__).resolve().parents[1] / relativo
        firmas.append(f"{relativo}:{ruta.stat().st_mtime_ns}")
    return "|".join(firmas)


@st.cache_resource(show_spinner="Cargando el pensum…")
def _cargar_simulador(clave: str, _firma: str) -> SimuladorPensum:
    """Carga el programa con ajustes documentados aplicados."""
    del _firma
    modelo = SimuladorPensum.desde_programa(clave)
    modelo.cargar(aplicar_ajustes_documentados=True)
    return modelo


def _motivo_cuello(entrada: int, salida: int) -> str | None:
    motivos: list[str] = []
    if entrada > UMBRAL_ENTRADA_CUELLO:
        motivos.append(f"grado de entrada {entrada} > {UMBRAL_ENTRADA_CUELLO}")
    if salida > UMBRAL_SALIDA_CUELLO:
        motivos.append(f"grado de salida {salida} > {UMBRAL_SALIDA_CUELLO}")
    if entrada + salida > UMBRAL_TOTAL_CUELLO:
        motivos.append(
            f"grado total {entrada + salida} > {UMBRAL_TOTAL_CUELLO}"
        )
    return "; ".join(motivos) if motivos else None


def _metricas_nodos(
    simulador: SimuladorPensum,
    indicadores: IndicadoresTopologicos,
) -> dict[int, dict]:
    assert simulador.red is not None
    complejidad = simulador.complejidad()
    metricas: dict[int, dict] = {}
    for nodo in simulador.red.grafo:
        codigo = int(nodo)
        entrada = int(simulador.red.grafo.in_degree(nodo))
        salida = int(simulador.red.grafo.out_degree(nodo))
        metricas[codigo] = {
            "tasa": simulador.tasa_de(codigo),
            "bloqueo": indicadores.factor_bloqueo.get(codigo),
            "posponimiento": indicadores.factor_posponimiento.get(codigo),
            "intermediacion": indicadores.intermediacion.get(codigo),
            "retraso": complejidad.retraso.get(codigo),
            "complejidad": complejidad.complejidad_estructural.get(codigo),
            "motivo_cuello": (
                _motivo_cuello(entrada, salida)
                if codigo in indicadores.cuellos_de_botella
                else None
            ),
        }
    return metricas


@st.cache_data(show_spinner=False)
def _html_red_cacheado(
    clave: str,
    nodos: int,
    aristas: int,
    oscuro: bool,
    cuellos: tuple[int, ...],
    camino: tuple[int, ...],
    con_metricas: bool,
    _vista: int = 1,
    modo_color: str = "area",
) -> str:
    """Regenera el HTML embebido cuando cambian programa, red, tema, resaltados o color."""
    del nodos, aristas, _vista
    simulador = _cargar_simulador(clave, _firma_codigo_sim())
    assert simulador.red is not None and simulador.programa is not None
    indicadores = simulador.indicadores()
    metricas = _metricas_nodos(simulador, indicadores) if con_metricas else None
    colores = _colores_de_cajas(simulador, modo_color)
    return html_de_la_red(
        simulador.red,
        titulo=f"Red de prerrequisitos · {simulador.programa.nombre}",
        embebido=True,
        oscuro=oscuro,
        resaltar=cuellos,
        camino=camino,
        metricas=metricas,
        colores=colores,
    )


def _colores_de_cajas(simulador: SimuladorPensum, modo: str) -> dict[int, str] | None:
    """Colores por tasa o complejidad; ``None`` conserva los colores del plan."""
    assert simulador.red is not None and simulador.tasas is not None
    if modo == "tasa":
        return colores_por_valor(
            tasas_por_asignatura(simulador.red, simulador.tasas),
            escala="tasa",
            minimo=0.0,
            maximo=1.0,
        )
    if modo == "complejidad":
        return colores_por_valor(
            dict(simulador.complejidad().complejidad_estructural),
            escala="complejidad",
        )
    return None


def _leyenda_color(modo: str, simulador: SimuladorPensum) -> None:
    """Barra de degradado bajo los controles, en HTML ligero."""
    if modo == "area":
        return
    paradas = ", ".join(ESCALAS_COLOR[modo])
    if modo == "tasa":
        izquierda, derecha = "p = 0", "p = 1"
        nota = "Gris: sin histórico (no se completa con 0 ni 1)."
    else:
        valores = simulador.complejidad().complejidad_estructural.values()
        izquierda, derecha = f"h = {min(valores)}", f"h = {max(valores)}"
        nota = "h(v) = retraso + bloqueo (Curricular Analytics)."
    st.markdown(
        f'<div class="pensunet-leyenda"><span>{izquierda}</span>'
        f'<div class="pensunet-degradado" style="background: linear-gradient(90deg, {paradas});">'
        f"</div><span>{derecha}</span></div>"
        f'<p class="pensunet-nota">{nota}</p>',
        unsafe_allow_html=True,
    )


def _histograma(
    tiempos: tuple[int, ...],
    media: float,
    oscuro: bool,
    *,
    xmax: int | None = None,
) -> plt.Figure:
    fondo = "#0e1117" if oscuro else "#ffffff"
    tipografia = "#fafafa" if oscuro else "#1a2e28"
    barras = "#3d9b84" if oscuro else "#1f6f5b"
    media_color = "#e8a87c" if oscuro else "#b35c2e"
    figura, eje = plt.subplots(figsize=(8.0, 3.6), dpi=120)
    figura.patch.set_facecolor(fondo)
    eje.set_facecolor(fondo)
    lo = int(min(tiempos))
    hi = int(max(tiempos) if xmax is None else max(max(tiempos), xmax))
    eje.hist(
        tiempos,
        bins=range(lo, hi + 2),
        color=barras,
        edgecolor=fondo,
        align="left",
    )
    eje.set_xlim(lo - 0.5, hi + 0.5)
    eje.axvline(media, color=media_color, linewidth=2, label=f"E(X) ≈ {media:.2f}")
    eje.set_xlabel("Semestres hasta el grado (X)", color=tipografia)
    eje.set_ylabel("Estudiantes representativos", color=tipografia)
    eje.tick_params(colors=tipografia)
    eje.legend(frameon=False, labelcolor=tipografia)
    for spine in eje.spines.values():
        spine.set_color(tipografia)
    eje.spines["top"].set_visible(False)
    eje.spines["right"].set_visible(False)
    figura.tight_layout()
    return figura


def _firma_tasas(tabla) -> tuple[tuple[int, float], ...]:
    """Huella estable de las p_i del editor (para saber si hay cambios pendientes)."""
    firmas = []
    for fila in tabla.sort_values("id").to_dict(orient="records"):
        valor = fila["tasa_aprobacion"]
        if valor is None or (isinstance(valor, float) and valor != valor):
            firmas.append((int(fila["id"]), float("nan")))
        else:
            firmas.append((int(fila["id"]), round(float(valor), 6)))
    return tuple(firmas)


def _ids_sin_tasa(tabla) -> list[int]:
    faltan = []
    for fila in tabla.to_dict(orient="records"):
        valor = fila["tasa_aprobacion"]
        if valor is None or (isinstance(valor, float) and valor != valor):
            faltan.append(int(fila["id"]))
    return faltan


def _asegurar_tasas_sesion(clave: str, simulador: SimuladorPensum) -> None:
    assert simulador.red is not None and simulador.tasas is not None
    if st.session_state.get("tasas_programa") != clave:
        st.session_state.tasas_programa = clave
        st.session_state.tasas_editor = tabla_tasas_del_grafo(
            simulador.red,
            simulador.tasas,
        )
        st.session_state.tasas_base = st.session_state.tasas_editor.copy()
        st.session_state.resultado = None
        st.session_state.escenario_usado = None
        st.session_state.tasas_simuladas = None
        st.session_state.mensaje_sim = None
        st.session_state.pop("editor_tasas", None)
    if "tasas_editor" not in st.session_state:
        st.session_state.tasas_editor = tabla_tasas_del_grafo(
            simulador.red,
            simulador.tasas,
        )
    if "tasas_base" not in st.session_state:
        st.session_state.tasas_base = st.session_state.tasas_editor.copy()


def _creditos_linea_default(clave: str) -> int:
    """Física usa cupo de línea 18; el resto exige todos los nodos del grafo."""
    return 18 if clave == "fisica" else 0


def _pagina_red(clave: str, simulador: SimuladorPensum, resumen: dict, oscuro: bool) -> None:
    st.subheader("Red de prerrequisitos")
    st.caption(
        "Clic en una materia para ver prerrequisitos a la derecha; clic en el "
        "fondo vacío para deseleccionar. Zoom con rueda o +/−; arrastra el "
        "fondo para desplazar."
    )
    html = _html_red_cacheado(
        clave,
        int(resumen["asignaturas"]),
        int(resumen["aristas"]),
        oscuro,
        (),
        (),
        True,
    )
    _mostrar_red_html(html)
    assert simulador.red is not None
    if simulador.red.reglas_aplicadas:
        with st.expander("Bitácora de ajustes documentados"):
            for nota in simulador.red.reglas_aplicadas:
                st.markdown(f"- {nota}")
    if simulador.red.inconsistencias:
        with st.expander("Inconsistencias del extracto (no corregidas en silencio)"):
            for nota in simulador.red.inconsistencias:
                st.markdown(f"- {nota}")


def _pagina_indicadores(
    clave: str,
    simulador: SimuladorPensum,
    resumen: dict,
    oscuro: bool,
    cuellos: tuple[int, ...],
    camino: tuple[int, ...],
) -> None:
    st.subheader("Indicadores")
    st.markdown(
        "Bloqueo, posponimiento e intermediación (sección II.B). "
        "Clic en una materia para ver tasa y métricas; clic en el fondo "
        "para deseleccionar."
    )
    assert simulador.red is not None
    indicadores = simulador.indicadores()

    c_a, c_b = st.columns(2)
    with c_a:
        ver_cuellos = st.toggle(
            "Resaltar cuellos de botella (naranja)",
            value=True,
            key="toggle_cuellos",
        )
    with c_b:
        ver_camino = st.toggle(
            "Resaltar camino más largo (rojo)",
            value=True,
            key="toggle_camino",
        )

    modo_color = st.segmented_control(
        "Color de las cajas",
        options=list(_MODOS_COLOR),
        format_func=lambda clave_modo: _MODOS_COLOR[clave_modo],
        default="area",
        key="modo_color_indicadores",
    ) or "area"
    _leyenda_color(modo_color, simulador)

    cuellos_vista = cuellos if ver_cuellos else ()
    camino_vista = camino if ver_camino else ()

    if ver_cuellos and cuellos_vista:
        nombres = []
        for codigo in cuellos_vista:
            nombre = simulador.red.grafo.nodes[codigo].get("nombre", "")
            nombres.append(f"**{codigo}** · {nombre}")
        st.info("Cuellos de botella: " + " · ".join(nombres))
    if ver_camino and camino_vista:
        nombres_camino = [
            f"{codigo} ({simulador.red.grafo.nodes[codigo].get('nombre', '')})"
            for codigo in camino_vista
        ]
        st.caption("Camino más largo: " + " → ".join(nombres_camino))

    html = _html_red_cacheado(
        clave,
        int(resumen["asignaturas"]),
        int(resumen["aristas"]),
        oscuro,
        cuellos_vista,
        camino_vista,
        True,
        modo_color=modo_color,
    )
    _mostrar_red_html(html)
    complejidad = simulador.complejidad()
    st.caption(
        f"Complejidad curricular del plan: **{complejidad.complejidad_total}** "
        "(suma de h(v) = retraso + bloqueo; Heileman et al., 2018, "
        "curricularanalytics.org). Ordena la tabla por `complejidad` para ver "
        "las asignaturas que más arrastran una reprobación."
    )
    st.dataframe(
        tabla_indicadores(simulador.red, indicadores, complejidad),
        width="stretch",
        hide_index=True,
        height=360,
    )


def _pagina_simulacion(clave: str, simulador: SimuladorPensum, oscuro: bool) -> None:
    st.subheader("Tiempo de grado")
    st.markdown(
        "Monte Carlo de la sección III.B: estima p(x) y E(X). "
        "Edita tasas o parámetros y pulsa **Simular**. Los CSV no se modifican. "
        "Trabajo de grado y electivas sin histórico dejan la tasa vacía "
        "(juicio experto): hay que completarlas aquí antes de simular; "
        "no se usa 0 ni 1 por defecto."
    )
    _asegurar_tasas_sesion(clave, simulador)
    if "resultado" not in st.session_state:
        st.session_state.resultado = None
        st.session_state.escenario_usado = None
        st.session_state.tasas_simuladas = None
        st.session_state.mensaje_sim = None

    faltan = _ids_sin_tasa(st.session_state.tasas_editor)
    if faltan:
        st.warning(
            f"Faltan tasas para {len(faltan)} asignatura(s) del grafo "
            f"(p. ej. {', '.join(str(c) for c in faltan[:8])}"
            f"{'…' if len(faltan) > 8 else ''}). "
            "Complétalas en el editor o la simulación no podrá correr."
        )

    with st.form("form_simular", clear_on_submit=False):
        col_a, col_b = st.columns([3, 1])
        with col_a:
            n_estudiantes = st.slider(
                "Estudiantes representativos",
                min_value=100,
                max_value=10_000,
                value=2_000,
                step=100,
            )
        with col_b:
            semilla = st.number_input(
                "Semilla",
                min_value=0,
                value=1,
                step=1,
            )

        with st.expander("Supuestos del escenario (Molontay + políticas locales)", expanded=False):
            st.caption(
                "Parámetros de la sección III. El cupo de electivas de 18 "
                "créditos es propio de la línea de aplicación de Física."
            )
            respetar_semestre = st.toggle(
                "Respetar semestre recomendado",
                value=True,
                help="No cursar una asignatura antes del semestre del plan.",
            )
            creditos_linea = st.number_input(
                "Créditos mínimos de electivas (línea)",
                min_value=0,
                max_value=48,
                value=_creditos_linea_default(clave),
                step=1,
                help=(
                    "En Física: cupo de línea de aplicación. "
                    "0 = exigir todas las del grafo."
                ),
            )
            electivas_sin_reintento = st.toggle(
                "Electivas sin reintento al reprobar",
                value=True,
            )
            max_semestres = st.number_input(
                "Tope de semestres en la simulación",
                min_value=10,
                max_value=80,
                value=40,
                step=1,
            )
            max_creditos = st.number_input(
                "Tope de créditos por semestre (0 = sin tope)",
                min_value=0,
                max_value=40,
                value=0,
                step=1,
                help=(
                    "Sin tope es el supuesto del artículo. Con tope se inscriben "
                    "primero las obligatorias de semestre más bajo."
                ),
            )

        with st.expander("Tasas de aprobación (editables)", expanded=True):
            st.caption(
                "Edita `tasa_aprobacion` entre 0 y 1. Al pulsar **Simular** "
                "se usan estos valores."
            )
            editadas = st.data_editor(
                st.session_state.tasas_editor,
                width="stretch",
                hide_index=True,
                height=280,
                disabled=["id", "nombre", "semestre"],
                column_config={
                    "tasa_aprobacion": st.column_config.NumberColumn(
                        "tasa_aprobacion",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.01,
                        format="%.3f",
                    ),
                },
                key="editor_tasas",
            )

        correr = st.form_submit_button(
            "Simular",
            type="primary",
            width="stretch",
        )

    b_reset, b_tg = st.columns(2)
    with b_reset:
        if st.button("Restablecer tasas al histórico", key="reset_tasas", width="stretch"):
            st.session_state.tasas_editor = st.session_state.tasas_base.copy()
            st.session_state.pop("editor_tasas", None)
            st.rerun()
    with b_tg:
        ids_tg = set(simulador.programa.ids_trabajo_grado) if simulador.programa else set()
        if ids_tg and st.button(
            "Usar p = 1 en Trabajo de Grado (juicio experto)",
            key="tg_uno",
            width="stretch",
            help=(
                "Opcional y explícito: solo cambia el editor de esta sesión. "
                "El CSV deja la tasa de TG vacía."
            ),
        ):
            tabla = st.session_state.tasas_editor.copy()
            tabla.loc[tabla["id"].astype(int).isin(ids_tg), "tasa_aprobacion"] = 1.0
            st.session_state.tasas_editor = tabla
            st.session_state.pop("editor_tasas", None)
            st.rerun()

    st.session_state.tasas_editor = editadas

    slot_estado = st.empty()
    slot_aviso = st.empty()
    slot_caption = st.empty()
    slot_metricas = st.container()
    slot_grafica = st.container()
    slot_tabla = st.container()

    if correr:
        escenario = Escenario(
            n_estudiantes=int(n_estudiantes),
            semilla=int(semilla),
            respetar_semestre_recomendado=bool(respetar_semestre),
            creditos_electivas_minimos=(
                None if int(creditos_linea) == 0 else int(creditos_linea)
            ),
            electivas_sin_reintento=bool(electivas_sin_reintento),
            max_semestres=int(max_semestres),
            max_creditos_semestre=None if int(max_creditos) == 0 else int(max_creditos),
        )
        with slot_estado:
            barra = st.progress(0, text="Preparando la simulación…")
        slot_aviso.info(
            f"Simulando **{n_estudiantes}** trayectorias con semilla "
            f"**{semilla}**…"
        )
        try:
            assert simulador.tasas is not None
            tasas_uso = tasas_desde_editor(simulador.tasas, editadas)
            barra.progress(20, text="Aplicando tasas y armando el escenario…")
            resultado = simulador.simular(escenario, tasas=tasas_uso)
        except (ValueError, RuntimeError) as error:
            barra.empty()
            slot_aviso.error(str(error))
            st.session_state.mensaje_sim = ("error", str(error))
            return
        barra.progress(100, text="Listo.")
        st.session_state.resultado = resultado
        st.session_state.escenario_usado = escenario
        st.session_state.tasas_simuladas = _firma_tasas(editadas)
        n_censurados = int(getattr(resultado, "n_censurados", 0) or 0)
        tope = getattr(resultado, "tope_semestres", escenario.max_semestres)
        mensaje = (
            f"Simulación terminada: E(X) ≈ **{resultado.media:.2f}** semestres."
        )
        if n_censurados:
            mensaje += (
                f" **{n_censurados}** trayectoria(s) no se graduaron en "
                f"≤ {tope} semestres (censuradas en el tope; no es un error)."
            )
            st.session_state.mensaje_sim = ("warning", mensaje)
        else:
            st.session_state.mensaje_sim = ("success", mensaje)
        st.toast(f"E(X) ≈ {resultado.media:.2f} semestres")

    resultado = st.session_state.resultado
    mensaje_sim = st.session_state.get("mensaje_sim")
    if mensaje_sim:
        tipo, texto = mensaje_sim
        if tipo == "success":
            slot_aviso.success(texto)
        elif tipo == "warning":
            slot_aviso.warning(texto)
        elif tipo == "error":
            slot_aviso.error(texto)

    if resultado is None:
        slot_aviso.warning(
            "Ajusta tasas o parámetros arriba y pulsa **Simular**."
        )
        return
    if not hasattr(resultado, "n_censurados"):
        st.session_state.resultado = None
        slot_aviso.info(
            "El resultado anterior quedó obsoleto. Vuelve a pulsar **Simular**."
        )
        return

    firma_actual = _firma_tasas(st.session_state.tasas_editor)
    if (
        st.session_state.get("tasas_simuladas") is not None
        and firma_actual != st.session_state.tasas_simuladas
        and not correr
    ):
        slot_estado.info(
            "Hay tasas editadas que aún no se han simulado. "
            "Pulsa **Simular** para actualizar E(X) y la gráfica."
        )

    usado = st.session_state.escenario_usado
    if usado is not None:
        slot_caption.caption(
            f"Resultado con n = {usado.n_estudiantes}, semilla = {usado.semilla}, "
            f"tope = {usado.max_semestres} semestres."
        )
    nominal = int(simulador.red.duracion_nominal) if simulador.red is not None else 10
    tiene_tasa_grado = hasattr(resultado, "tasa_grado_en")
    with slot_metricas:
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("E(X) semestres", f"{resultado.media:.2f}")
        m2.metric("Desviación", f"{resultado.desviacion:.2f}")
        m3.metric("Rango", f"{min(resultado.tiempos)} – {max(resultado.tiempos)}")
        m4.metric("Censurados", resultado.n_censurados)
        if tiene_tasa_grado:
            m5.metric(
                f"Grado ≤ {nominal} sem.",
                f"{resultado.tasa_grado_en(nominal):.0%}",
                help="Proporción graduada en la duración nominal.",
            )
            m6.metric(
                f"Grado ≤ {nominal + 2} sem.",
                f"{resultado.tasa_grado_en(nominal + 2):.0%}",
                help="Proporción graduada con hasta dos semestres de rezago.",
            )
    with slot_grafica:
        xmax = None if usado is None else int(usado.max_semestres)
        st.pyplot(
            _histograma(
                resultado.tiempos,
                resultado.media,
                oscuro,
                xmax=xmax,
            ),
            clear_figure=True,
            width="stretch",
        )
    with slot_tabla:
        if getattr(resultado, "reprobaciones", None):
            st.markdown("##### Asignaturas que más frenan el flujo simulado")
            st.caption(
                "Reprobaciones medias por estudiante simulado. Una asignatura con "
                "muchas reprobaciones y alto bloqueo es un cuello de botella real."
            )
            st.dataframe(
                _tabla_frenan(resultado, simulador),
                width="stretch",
                hide_index=True,
            )
        with st.expander("Frecuencias de X"):
            st.dataframe(
                tabla_tiempos(resultado),
                width="stretch",
                hide_index=True,
            )


def _tabla_frenan(resultado, simulador: SimuladorPensum, n: int = 10):
    """Top de reprobaciones medias con nombre, p_i y bloqueo."""
    import pandas as pd

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


def main() -> None:
    """Punto de entrada de la app Streamlit."""
    st.set_page_config(
        page_title="Pensunet",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    oscuro = _tema_oscuro()

    st.markdown('<p class="pensunet-marca">Pensunet</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="pensunet-lema">Red de prerrequisitos y tiempo de grado '
        "de los pensum FCMN (Universidad Distrital).</p>",
        unsafe_allow_html=True,
    )

    etiquetas = {clave: prog.nombre for clave, prog in PROGRAMAS.items()}
    with st.sidebar:
        st.markdown("### Carrera")
        clave = st.selectbox(
            "Programa",
            options=sorted(PROGRAMAS),
            format_func=lambda c: f"{etiquetas[c]} (plan {PROGRAMAS[c].id_plan})",
            index=sorted(PROGRAMAS).index("fisica"),
            key="selector_programa",
        )
        st.markdown("### Navegación")
        pagina = st.radio(
            "Sección",
            _PAGINAS,
            index=0,
            label_visibility="collapsed",
        )
        st.caption(
            "Ajustes documentados aplicados (ver "
            "`ajustes_prerrequisitos.csv`). TG sin tasa por defecto."
        )
        st.caption(f"Pensunet {__version__} · Molontay et al. (2020)")

    simulador = _cargar_simulador(clave, _firma_codigo_sim())
    assert simulador.red is not None and simulador.programa is not None
    resumen = tabla_resumen_red(simulador.red)
    indicadores = simulador.indicadores()
    cuellos = tuple(int(c) for c in indicadores.cuellos_de_botella)
    camino = tuple(int(c) for c in camino_mas_largo(simulador.red))

    assert simulador.tasas is not None
    media_p = tasa_media(simulador.red, simulador.tasas)
    complejidad_total = simulador.complejidad().complejidad_total
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Asignaturas", resumen["asignaturas"], help="Nodos del grafo con ajustes.")
    c2.metric("Aristas", resumen["aristas"], help="Prerrequisitos estrictos (deben aprobarse).")
    c3.metric(
        "Créditos",
        simulador.programa.creditos_plan,
        help="Créditos del grado; cada cupo electivo cuenta una vez.",
    )
    c4.metric(
        "Semestres",
        resumen["duracion_nominal"],
        help="Duración nominal del plan (máximo semestre recomendado).",
    )
    c5.metric(
        "p̄ media",
        "—" if media_p is None else f"{media_p:.2f}",
        help="Promedio simple de p_i en las asignaturas con histórico.",
    )
    c6.metric(
        "Complejidad",
        complejidad_total,
        help="Complejidad curricular (Curricular Analytics): suma de retraso + bloqueo.",
    )
    c7.metric("Cuellos", len(cuellos), help="Cuellos de botella, ecuación (2) de Molontay.")

    if pagina == "Red de prerrequisitos":
        _pagina_red(clave, simulador, resumen, oscuro)
    elif pagina == "Indicadores":
        _pagina_indicadores(clave, simulador, resumen, oscuro, cuellos, camino)
    else:
        _pagina_simulacion(clave, simulador, oscuro)


if __name__ == "__main__":
    main()
