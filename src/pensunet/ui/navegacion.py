"""Navegación compartida: breadcrumb y helpers de nivel."""

from __future__ import annotations

import streamlit as st

from pensunet.datos.programas import PROGRAMAS
from pensunet.ui.compartido import CLAVE_FACULTAD, clave_carrera, definir_selector


def breadcrumb() -> None:
    """Miga de pan Facultad / carrera; el primer tramo vuelve a Facultad."""
    clave = clave_carrera()
    fila = st.container(horizontal=True, gap="small", vertical_alignment="center")
    with fila:
        if st.button(
            "Facultad de Ciencias Matemáticas y Naturales",
            key="breadcrumb_facultad",
            type="tertiary",
        ):
            definir_selector(CLAVE_FACULTAD)
            st.rerun()
        if clave is not None:
            st.caption(f"/ **{PROGRAMAS[clave].nombre}**")
