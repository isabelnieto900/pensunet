"""Entrypoint del dashboard Pensunet (dos niveles: Facultad / carrera)."""

from __future__ import annotations

import streamlit as st

from pensunet import __version__
from pensunet.datos.programas import PROGRAMAS
from pensunet.ui.app_pages import (
    acerca,
    facultad,
    materias,
    materias_facultad,
    red,
    resumen,
    tiempo_grado,
)
from pensunet.ui.compartido import (
    CLAVE_FACULTAD,
    aplicar_selector_pendiente,
    nivel,
)
from pensunet.ui.estilo import inyectar_estilo, marca_sidebar


def _marcar_cambio_nivel() -> None:
    st.session_state["_ir_a_default_nivel"] = True


def _sidebar() -> None:
    with st.sidebar:
        marca_sidebar()
        opciones = [CLAVE_FACULTAD, *sorted(PROGRAMAS)]
        etiquetas = {
            CLAVE_FACULTAD: "Facultad de Ciencias Matemáticas y Naturales",
            **{
                c: f"{PROGRAMAS[c].nombre} (plan {PROGRAMAS[c].id_plan})"
                for c in PROGRAMAS
            },
        }
        st.selectbox(
            "Nivel",
            options=opciones,
            format_func=lambda c: etiquetas[c],
            key="selector_programa",
            on_change=_marcar_cambio_nivel,
            help="Facultad (panorama) o una carrera (detalle).",
        )
        st.caption(f"Pensunet {__version__}")


def _navegacion() -> object:
    """Registra siempre Facultad y carrera para que /plan y /simulacion existan."""
    en_facultad = nivel() == "facultad"
    panorama = st.Page(
        facultad.mostrar,
        title="Panorama",
        icon=":material/dashboard:",
        url_path="panorama",
        default=en_facultad,
    )
    resumen_p = st.Page(
        resumen.mostrar,
        title="Resumen",
        icon=":material/dashboard:",
        url_path="resumen",
        default=not en_facultad,
    )
    secciones = {
        "Facultad": [
            panorama,
            st.Page(
                materias_facultad.mostrar,
                title="Materias de la Facultad",
                icon=":material/school:",
                url_path="materias-facultad",
            ),
            st.Page(
                acerca.mostrar,
                title="Acerca de",
                icon=":material/info:",
                url_path="acerca",
            ),
        ],
        "Carrera": [
            resumen_p,
            st.Page(
                red.mostrar,
                title="Plan de estudios",
                icon=":material/account_tree:",
                url_path="plan",
            ),
            st.Page(
                materias.mostrar,
                title="Materias",
                icon=":material/menu_book:",
                url_path="materias",
            ),
            st.Page(
                tiempo_grado.mostrar,
                title="Simulación",
                icon=":material/science:",
                url_path="simulacion",
            ),
        ],
    }
    pagina = st.navigation(secciones, position="sidebar")
    if st.session_state.pop("_ir_a_default_nivel", False):
        st.switch_page(panorama if en_facultad else resumen_p)
    return pagina


def main() -> None:
    st.set_page_config(
        page_title="Pensunet",
        page_icon=":material/hub:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    aplicar_selector_pendiente()
    if "selector_programa" not in st.session_state:
        st.session_state.selector_programa = CLAVE_FACULTAD
    if "modo_oscuro" not in st.session_state:
        st.session_state.modo_oscuro = False
    inyectar_estilo()
    _sidebar()
    pagina = _navegacion()
    pagina.run()


if __name__ == "__main__":
    main()
