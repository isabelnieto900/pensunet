"""Lanza la interfaz Streamlit o indica cómo instalarla."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from pensunet.datos.programas import PROGRAMAS


def ejecutar(programa: str | None = None) -> None:
    """Abre la interfaz Streamlit de Pensunet.

    Requiere el extra ``ui``: ``pip install -e ".[ui]"``.
    ``programa`` se reenvía como query param inicial del selector.
    """
    if programa is not None and programa not in PROGRAMAS:
        conocidos = ", ".join(sorted(PROGRAMAS))
        raise ValueError(f"Programa {programa!r} desconocido. Opciones: {conocidos}.")
    if shutil.which("streamlit") is None and not _streamlit_importable():
        raise ModuleNotFoundError(
            'Streamlit no está instalado. Ejecute: pip install -e ".[ui]"'
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
    if programa is not None:
        comando.extend(["--", f"--programa={programa}"])
    raise SystemExit(subprocess.call(comando))


def programas_disponibles() -> list[str]:
    """Claves del selector de carrera."""
    return sorted(PROGRAMAS)


def _streamlit_importable() -> bool:
    try:
        import streamlit  # noqa: F401
    except ImportError:
        return False
    return True
