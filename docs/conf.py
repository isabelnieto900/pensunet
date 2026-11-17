"""Configuración de Sphinx para la documentación de Pensunet."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pensunet import __version__  # noqa: E402

project = "Pensunet"
author = "Laura Isabel Nieto Parroyo"
copyright = f"{date.today().year}, {author}"
version = __version__
release = __version__
language = "es"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
]

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
root_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "*.pdf"]

myst_enable_extensions = ["colon_fence", "dollarmath"]
myst_heading_anchors = 3
suppress_warnings = ["myst.xref_missing"]

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_mock_imports = ["streamlit"]
napoleon_google_docstring = True
napoleon_numpy_docstring = True

html_theme = "furo"
html_title = f"Pensunet {release}"
html_theme_options = {
    "source_repository": "https://github.com/isabelnieto900/pensunet/",
    "source_branch": "main",
    "source_directory": "docs/",
    "light_css_variables": {"color-brand-primary": "#1F6F5B", "color-brand-content": "#1F6F5B"},
    "dark_css_variables": {"color-brand-primary": "#4FB39A", "color-brand-content": "#4FB39A"},
}
