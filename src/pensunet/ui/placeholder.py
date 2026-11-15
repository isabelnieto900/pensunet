"""Marcador de la interfaz. La etapa 1 se usa desde Python."""


def ejecutar() -> None:
    """No abre una ventana.

    La interfaz Streamlit queda para una fase posterior. El uso actual
    es la fachada ``SimuladorPensum`` (secciones II.A y II.B de
    Molontay et al., 2020).
    """
    raise NotImplementedError(
        "La interfaz de usuario no forma parte de la etapa 1. Use SimuladorPensum desde Python."
    )
