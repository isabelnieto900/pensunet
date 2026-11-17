"""Interfaz Streamlit de Pensunet: red, indicadores y tiempo de grado."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

from pensunet import SimuladorPensum, __version__
from pensunet.datos.fabrica import FabricaLectores
from pensunet.dominio.escenario import Escenario
from pensunet.dominio.indicadores import (
    UMBRAL_ENTRADA_CUELLO,
    UMBRAL_SALIDA_CUELLO,
    UMBRAL_TOTAL_CUELLO,
    IndicadoresTopologicos,
    camino_mas_largo,
)
from pensunet.dominio.visualizacion import html_de_la_red
from pensunet.ui.tablas import (
    tabla_indicadores,
    tabla_resumen_red,
    tabla_tasas_del_grafo,
    tabla_tiempos,
    tasas_desde_editor,
)


def _mostrar_red_html(html: str) -> None:
    """Muestra la red interactiva (iframe sin barra de scroll interna)."""
    st.iframe(html, height=560)

_PAGINAS = (
    "Red de prerrequisitos",
    "Indicadores",
    "Tiempo de grado",
)

# Tipografía propia; colores ligados al tema de Streamlit (claro/oscuro).
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
  max-width: 38rem;
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
div[data-testid="stIFrame"],
div[data-testid="stIFrame"] > iframe {
  border: none !important;
  overflow: hidden !important;
}
</style>
"""


def _raiz_proyecto() -> Path:
    """Localiza la raíz del repo (desarrollo) o el directorio de trabajo."""
    aqui = Path(__file__).resolve()
    candidatos = [aqui.parents[3], Path.cwd()]
    for candidato in candidatos:
        if (candidato / "data" / "reference" / "pensum_fisica.csv").is_file():
            return candidato
    raise FileNotFoundError(
        "No se encontraron los CSV de Física. Ejecute la interfaz desde "
        "la raíz del repositorio pensunet."
    )


def _rutas_por_defecto() -> dict[str, Path]:
    raiz = _raiz_proyecto()
    return {
        "ruta_pensum": raiz / "data" / "reference" / "pensum_fisica.csv",
        "ruta_prerequisitos": raiz / "data" / "reference" / "prerequisitos_fisica.csv",
        "ruta_tasas": raiz / "data" / "processed" / "tasas_aprobacion_fisica.csv",
    }


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
    ):
        ruta = Path(__file__).resolve().parents[1] / relativo
        firmas.append(f"{relativo}:{ruta.stat().st_mtime_ns}")
    return "|".join(firmas)


@st.cache_resource(show_spinner="Cargando el pensum de Física…")
def _cargar_simulador(_firma: str) -> SimuladorPensum:
    """Siempre con reglas de Física: es el modo de análisis del programa."""
    del _firma
    lector = FabricaLectores.crear("csv", **_rutas_por_defecto())
    modelo = SimuladorPensum(lector)
    modelo.cargar(aplicar_reglas=True)
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
            "motivo_cuello": (
                _motivo_cuello(entrada, salida)
                if codigo in indicadores.cuellos_de_botella
                else None
            ),
        }
    return metricas


@st.cache_data(show_spinner=False)
def _html_red_cacheado(
    nodos: int,
    aristas: int,
    oscuro: bool,
    cuellos: tuple[int, ...],
    camino: tuple[int, ...],
    con_metricas: bool,
    _vista: int = 4,
) -> str:
    """Regenera el HTML embebido cuando cambian red, tema o resaltados."""
    del nodos, aristas, _vista
    simulador = _cargar_simulador(_firma_codigo_sim())
    assert simulador.red is not None
    indicadores = simulador.indicadores()
    metricas = _metricas_nodos(simulador, indicadores) if con_metricas else None
    return html_de_la_red(
        simulador.red,
        titulo="Red de prerrequisitos · Física",
        embebido=True,
        oscuro=oscuro,
        resaltar=cuellos,
        camino=camino,
        metricas=metricas,
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
    return tuple(
        (int(fila["id"]), round(float(fila["tasa_aprobacion"]), 6))
        for fila in tabla.sort_values("id").to_dict(orient="records")
    )


def _asegurar_tasas_sesion(simulador: SimuladorPensum) -> None:
    assert simulador.red is not None and simulador.tasas is not None
    if "tasas_editor" not in st.session_state:
        st.session_state.tasas_editor = tabla_tasas_del_grafo(
            simulador.red,
            simulador.tasas,
        )
    if "tasas_base" not in st.session_state:
        st.session_state.tasas_base = st.session_state.tasas_editor.copy()


def _pagina_red(simulador: SimuladorPensum, resumen: dict, oscuro: bool) -> None:
    st.subheader("Red de prerrequisitos")
    st.caption(
        "Clic en una materia para ver prerrequisitos a la derecha; clic en el "
        "fondo vacío para deseleccionar. Zoom con rueda o +/−; arrastra el "
        "fondo para desplazar."
    )
    html = _html_red_cacheado(
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
        with st.expander("Bitácora de reglas aplicadas"):
            for nota in simulador.red.reglas_aplicadas:
                st.markdown(f"- {nota}")


def _pagina_indicadores(
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
        int(resumen["asignaturas"]),
        int(resumen["aristas"]),
        oscuro,
        cuellos_vista,
        camino_vista,
        True,
    )
    _mostrar_red_html(html)
    st.dataframe(
        tabla_indicadores(simulador.red, indicadores),
        width="stretch",
        hide_index=True,
        height=360,
    )


def _pagina_simulacion(simulador: SimuladorPensum, oscuro: bool) -> None:
    st.subheader("Tiempo de grado")
    st.markdown(
        "Monte Carlo de la sección III.B: estima p(x) y E(X). "
        "Edita tasas o parámetros y pulsa **Simular** (un solo clic aplica "
        "todo; no hace falta cambiar la semilla). Los CSV no se modifican."
    )
    _asegurar_tasas_sesion(simulador)
    if "resultado" not in st.session_state:
        st.session_state.resultado = None
        st.session_state.escenario_usado = None
        st.session_state.tasas_simuladas = None
        st.session_state.mensaje_sim = None

    # Formulario: al enviar, Streamlit confirma el data_editor (antes las
    # ediciones de tasas solo se “pegaban” al tocar otro control, p. ej. semilla).
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

        with st.expander("Supuestos del escenario (Molontay + Física)", expanded=False):
            st.caption(
                "Parámetros de la sección III y políticas locales. "
                "Las tasas p_i se editan en el bloque de abajo."
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
                value=18,
                step=1,
                help=(
                    "Cupo de línea de aplicación en Física. "
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
                help=(
                    "Si un estudiante no se gradúa a tiempo, se censura en este "
                    "tope (la simulación no falla; se reporta cuántos censurados)."
                ),
            )

        with st.expander("Tasas de aprobación (editables)", expanded=True):
            st.caption(
                "Edita `tasa_aprobacion` entre 0 y 1. Al pulsar **Simular** "
                "se usan estos valores (no hace falta tocar la semilla)."
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

    if st.button("Restablecer tasas al histórico", key="reset_tasas"):
        st.session_state.tasas_editor = st.session_state.tasas_base.copy()
        # Limpia el estado interno del data_editor del formulario.
        st.session_state.pop("editor_tasas", None)
        st.rerun()

    st.session_state.tasas_editor = editadas

    # Huecos fijos: el progreso/aviso no desplaza la gráfica entre corridas.
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
    with slot_metricas:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("E(X) semestres", f"{resultado.media:.2f}")
        m2.metric("Desviación", f"{resultado.desviacion:.2f}")
        m3.metric("Rango", f"{min(resultado.tiempos)} – {max(resultado.tiempos)}")
        m4.metric("Censurados", resultado.n_censurados)
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
        with st.expander("Frecuencias de X"):
            st.dataframe(
                tabla_tiempos(resultado),
                width="stretch",
                hide_index=True,
            )


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
        "del pensum de Física (Universidad Distrital).</p>",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Navegación")
        pagina = st.radio(
            "Sección",
            _PAGINAS,
            index=0,
            label_visibility="collapsed",
        )
        st.caption(
            "Datos de Física con reglas del programa aplicadas "
            "(exclusiones, aristas confirmadas, TG con tasa 1)."
        )
        st.caption(f"Pensunet {__version__} · Molontay et al. (2020)")

    simulador = _cargar_simulador(_firma_codigo_sim())
    assert simulador.red is not None
    resumen = tabla_resumen_red(simulador.red)
    indicadores = simulador.indicadores()
    cuellos = tuple(int(c) for c in indicadores.cuellos_de_botella)
    # Se calcula aparte por si Streamlit aún tiene un IndicadoresTopologicos
    # antiguo en memoria tras un hot-reload.
    camino = tuple(int(c) for c in camino_mas_largo(simulador.red))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Asignaturas", resumen["asignaturas"])
    c2.metric("Aristas estrictas", resumen["aristas"])
    c3.metric("Duración nominal", f"{resumen['duracion_nominal']} sem.")
    c4.metric("Cuellos de botella", len(cuellos))

    if pagina == "Red de prerrequisitos":
        _pagina_red(simulador, resumen, oscuro)
    elif pagina == "Indicadores":
        _pagina_indicadores(simulador, resumen, oscuro, cuellos, camino)
    else:
        _pagina_simulacion(simulador, oscuro)


if __name__ == "__main__":
    main()
