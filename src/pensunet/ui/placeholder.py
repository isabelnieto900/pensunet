"""Lanza la interfaz Streamlit o indica cómo instalarla."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def ejecutar() -> None:
    """Abre la interfaz Streamlit de Pensunet.

    Requiere el extra ``ui``: ``pip install -e ".[ui]"``.
    """
    if shutil.which("streamlit") is None and not _streamlit_importable():
        raise ModuleNotFoundError(
            "Streamlit no está instalado. Ejecute: pip install -e \".[ui]\""
        )
    ruta_app = Path(__file__).resolve().parent / "app.py"
    comando = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(ruta_app),
        "--browser.gatherUsageStats",
        "false",
    ]
    raise SystemExit(subprocess.call(comando))


def _streamlit_importable() -> bool:
    try:
        import streamlit  # noqa: F401
    except ImportError:
        return False
    return True
