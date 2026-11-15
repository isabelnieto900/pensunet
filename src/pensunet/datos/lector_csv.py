"""Lee las tres tablas desde CSV con columnas de la Universidad Distrital."""

from pathlib import Path

import pandas as pd

from pensunet.datos.adaptador_ud import AdaptadorUD
from pensunet.datos.lector import LectorDatos


class LectorCSV(LectorDatos):
    """Lector de los CSV de referencia y de la tasa agregada.

    Sección II.A y ecuación (7) de Molontay et al. (2020): entrega el
    pensum, las aristas y las tasas ya adaptadas al modelo interno.
    """

    def __init__(
        self,
        ruta_pensum: str | Path,
        ruta_prerequisitos: str | Path,
        ruta_tasas: str | Path,
        adaptador: AdaptadorUD | None = None,
    ) -> None:
        self.ruta_pensum = Path(ruta_pensum)
        self.ruta_prerequisitos = Path(ruta_prerequisitos)
        self.ruta_tasas = Path(ruta_tasas)
        self._adaptador = adaptador if adaptador is not None else AdaptadorUD()

    def leer_pensum(self) -> pd.DataFrame:
        """Lee y adapta el pensum. Sección II.A, nodos del grafo."""
        return self._adaptador.adaptar_pensum(_leer_csv(self.ruta_pensum))

    def leer_prerequisitos(self) -> pd.DataFrame:
        """Lee y adapta los prerrequisitos. Sección II.A, aristas."""
        return self._adaptador.adaptar_prerequisitos(_leer_csv(self.ruta_prerequisitos))

    def leer_tasas_aprobacion(self) -> pd.DataFrame:
        """Lee y adapta las tasas. Ecuación (7)."""
        return self._adaptador.adaptar_tasas(_leer_csv(self.ruta_tasas))


def _leer_csv(ruta: Path) -> pd.DataFrame:
    if not ruta.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de datos: {ruta}.")
    return pd.read_csv(ruta, encoding="utf-8")
