"""Elige el lector sin que el resto del modelo conozca el origen."""

from pensunet.datos.lector import LectorDatos
from pensunet.datos.lector_csv import LectorCSV


class FabricaLectores:
    """Fábrica de lectores de pensum, prerrequisitos y tasas.

    Sección II.A y ecuación (7) de Molontay et al. (2020): ambas piezas
    necesitan las mismas tres tablas. En esta versión el único origen
    admitido es CSV; la fábrica concentra esa creación para que la
    fachada y los ejemplos no construyan ``LectorCSV`` a mano.
    """

    @staticmethod
    def crear(tipo: str, **opciones) -> LectorDatos:
        """Crea el lector pedido.

        Parámetros
        ----------
        tipo:
            Solo ``csv``.
        opciones:
            Argumentos del ``LectorCSV`` (rutas del pensum, de los
            prerrequisitos y de las tasas).
        """
        if tipo == "csv":
            return LectorCSV(**opciones)
        raise ValueError(
            f"No hay un lector registrado para el tipo {tipo!r}. "
            "Esta versión solo admite 'csv'."
        )
