"""Identidad visual UD para el dashboard Streamlit (sin escudo ni logo)."""

from __future__ import annotations

from typing import Any

import altair as alt
import streamlit as st

PALETA_CATEGORICA = (
    "#8C1919",
    "#FDB400",
    "#1291C0",
    "#00A859",
    "#98999A",
    "#373435",
)

COLORES_CARRERA = {
    "fisica": PALETA_CATEGORICA[0],
    "quimica": PALETA_CATEGORICA[1],
    "biologia": PALETA_CATEGORICA[2],
    "matematicas": PALETA_CATEGORICA[3],
}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind:wght@400;500;600;700&family=Titillium+Web:wght@600;700&display=swap');
h1, h2, h3, h4, h5, h6,
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"] {
  font-family: "Titillium Web", Hind, sans-serif !important;
}
html, body, [class*="css"], p, label, span {
  font-family: Hind, "Segoe UI", sans-serif;
}
.pensunet-marca-side {
  font-family: "Titillium Web", Hind, sans-serif !important;
  font-size: 1.55rem;
  font-weight: 700;
  color: #8C1919;
  margin: 0.15rem 0 0.75rem 0;
  letter-spacing: -0.02em;
}
div[data-testid="stMetric"] {
  background: var(--secondary-background-color);
  border: 1px solid color-mix(in srgb, #98999A 55%, transparent);
  border-radius: 14px;
  padding: 0.7rem 0.85rem;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: 14px !important;
}
.pensunet-breadcrumb {
  font-family: Hind, sans-serif;
  font-size: 0.9rem;
  margin: 0 0 0.6rem 0;
  opacity: 0.9;
}
.pensunet-leyenda {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0.35rem 0 0.15rem 0;
  font-family: Hind, sans-serif;
  font-size: 0.88rem;
  font-weight: 600;
}
.pensunet-leyenda > span {
  flex: 0 0 auto;
  white-space: nowrap;
}
.pensunet-degradado {
  flex: 1 1 auto;
  min-width: 12rem;
  height: 14px;
  border-radius: 7px;
  border: 1px solid color-mix(in srgb, #98999A 55%, transparent);
}
.pensunet-nota {
  margin: 0 0 0.55rem 0;
  font-family: Hind, sans-serif;
  font-size: 0.8rem;
  opacity: 0.85;
}
</style>
"""

_ALTAIR_REGISTRADO = False


def inyectar_estilo() -> None:
    """Inyecta CSS UD una sola vez por sesión."""
    if st.session_state.get("_pensunet_css"):
        return
    st.html(_CSS)
    st.session_state._pensunet_css = True
    _registrar_tema_altair()


def _registrar_tema_altair() -> None:
    global _ALTAIR_REGISTRADO
    if _ALTAIR_REGISTRADO:
        return
    config = {
        "background": "transparent",
        "view": {"stroke": "transparent"},
        "axis": {
            "labelFont": "Hind",
            "titleFont": "Titillium Web",
            "labelFontSize": 11,
            "titleFontSize": 12,
            "gridColor": "#E6E6E6",
            "domainColor": "#98999A",
        },
        "legend": {
            "labelFont": "Hind",
            "titleFont": "Titillium Web",
        },
        "title": {
            "font": "Titillium Web",
            "fontSize": 14,
            "color": "#000000",
        },
        "range": {"category": list(PALETA_CATEGORICA)},
    }
    if hasattr(alt, "theme") and hasattr(alt.theme, "register"):

        @alt.theme.register("pensunet_ud", enable=True)
        def _tema_ud():
            return {"config": config}

        del _tema_ud
    else:
        alt.themes.register("pensunet_ud", lambda: {"config": config})
        alt.themes.enable("pensunet_ud")
    _ALTAIR_REGISTRADO = True


def tarjeta_kpi(
    titulo: str,
    valor: Any,
    delta: Any | None = None,
    ayuda: str | None = None,
) -> None:
    """KPI en tarjeta con tipografía Titillium."""
    st.metric(titulo, valor, delta=delta, help=ayuda, border=True)


def marca_sidebar() -> None:
    st.markdown(
        ':material/hub: <span class="pensunet-marca-side">Pensunet</span>',
        unsafe_allow_html=True,
    )
    st.caption("Simulador curricular FCMN")


def breadcrumb() -> None:
    """Reexporta la miga de pan de ``navegacion`` (una sola clave de widget)."""
    from pensunet.ui.navegacion import breadcrumb as _breadcrumb

    _breadcrumb()
