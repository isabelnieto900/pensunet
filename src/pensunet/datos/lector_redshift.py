"""Stub del lector institucional. No abre conexiones en esta etapa."""

import pandas as pd

from pensunet.datos.lector import LectorDatos

_MENSAJE = (
    "La lectura desde Redshift no está implementada. Cuando exista, las "
    "credenciales tienen que llegar por variables de entorno y la consulta "
    "debe agregar en el servidor. No se descarga el detalle por estudiante: "
    "la ecuación (7) de Molontay et al. (2020) solo necesita inscritos y "
    "aprobados por asignatura, y la sección II.A solo el catálogo del pensum."
)


class LectorRedshift(LectorDatos):
    """Punto de extensión para el histórico institucional en Redshift.

    Sección II.A y ecuación (7). Hoy no consulta nada: evita dejar en el
    repositorio una conexión a medio hacer o una ruta hacia microdatos.
    """

    def __init__(
        self,
        host: str | None = None,
        puerto: int = 5439,
        base_datos: str | None = None,
        usuario: str | None = None,
        esquema: str | None = None,
    ) -> None:
        self.host = host
        self.puerto = puerto
        self.base_datos = base_datos
        self.usuario = usuario
        self.esquema = esquema

    def leer_pensum(self) -> pd.DataFrame:
        """Sección II.A. Pendiente de la consulta agregada al catálogo."""
        raise NotImplementedError(_MENSAJE)

    def leer_prerequisitos(self) -> pd.DataFrame:
        """Sección II.A. Pendiente de la consulta de aristas."""
        raise NotImplementedError(_MENSAJE)

    def leer_tasas_aprobacion(self) -> pd.DataFrame:
        """Ecuación (7). Pendiente de la agregación por asignatura."""
        raise NotImplementedError(_MENSAJE)
