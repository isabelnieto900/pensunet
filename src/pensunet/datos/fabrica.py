"""Elige el lector sin que el resto del modelo conozca el origen."""

from pensunet.datos.lector import LectorDatos
from pensunet.datos.lector_csv import LectorCSV
from pensunet.datos.lector_redshift import LectorRedshift


class FabricaLectores:
    """Fábrica de lectores de pensum, prerrequisitos y tasas.

    Sección II.A y ecuación (7) de Molontay et al. (2020): ambas piezas
    necesitan las mismas tres tablas. La fábrica permite pasar de CSV a
    Redshift sin tocar el grafo ni los indicadores.

    El tipo ``csv`` construye un ``LectorCSV``. El tipo ``redshift``
    construye el stub documentado; todavía no consulta el almacén.
    """

    @staticmethod
    def crear(tipo: str, **opciones) -> LectorDatos:
        """Crea el lector pedido.

        Parámetros
        ----------
        tipo:
            ``csv`` o ``redshift``.
        opciones:
            Argumentos del lector concreto.
        """
        if tipo == "csv":
            return LectorCSV(**opciones)
        if tipo == "redshift":
            return LectorRedshift(**opciones)
        raise ValueError(
            f"No hay un lector registrado para el tipo {tipo!r}. Use 'csv' o 'redshift'."
        )
