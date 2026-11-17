"""Catálogo de programas FCMN disponibles en Pensunet."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

RAIZ_DATOS = Path(__file__).resolve().parents[3] / "data"


@dataclass(frozen=True)
class Programa:
    """Metadatos de un plan cargable desde los CSV de data/."""

    clave: str
    nombre: str
    id_plan: int
    creditos_plan: int
    ids_trabajo_grado: tuple[int, ...]

    @property
    def ruta_pensum(self) -> Path:
        return RAIZ_DATOS / "reference" / f"pensum_{self.clave}.csv"

    @property
    def ruta_prerequisitos(self) -> Path:
        return RAIZ_DATOS / "reference" / f"prerequisitos_{self.clave}.csv"

    @property
    def ruta_tasas(self) -> Path:
        return RAIZ_DATOS / "processed" / f"tasas_aprobacion_{self.clave}.csv"

    def rutas(self) -> dict[str, Path]:
        """Argumentos de ``FabricaLectores.crear('csv', ...)``."""
        return {
            "ruta_pensum": self.ruta_pensum,
            "ruta_prerequisitos": self.ruta_prerequisitos,
            "ruta_tasas": self.ruta_tasas,
        }


PROGRAMAS: dict[str, Programa] = {
    "fisica": Programa(
        clave="fisica",
        nombre="Física",
        id_plan=327,
        creditos_plan=145,
        ids_trabajo_grado=(25149, 25154),
    ),
    "quimica": Programa(
        clave="quimica",
        nombre="Química",
        id_plan=328,
        creditos_plan=145,
        ids_trabajo_grado=(25149, 25242),
    ),
    "biologia": Programa(
        clave="biologia",
        nombre="Biología",
        id_plan=329,
        creditos_plan=144,
        ids_trabajo_grado=(22540, 25345),
    ),
    "matematicas": Programa(
        clave="matematicas",
        nombre="Matemáticas",
        id_plan=298,
        creditos_plan=140,
        ids_trabajo_grado=(19924, 19925),
    ),
}

RUTA_AJUSTES = RAIZ_DATOS / "reference" / "ajustes_prerrequisitos.csv"
RUTA_CUPOS_SIN_ASIGNATURA = RAIZ_DATOS / "reference" / "cupos_sin_asignatura.csv"
RUTA_TRABAJO_GRADO = RAIZ_DATOS / "reference" / "trabajo_de_grado.csv"
RUTA_JUICIO_EXPERTO = RAIZ_DATOS / "reference" / "juicio_experto.csv"


def obtener_programa(clave: str) -> Programa:
    """Devuelve el programa o falla con las claves conocidas."""
    try:
        return PROGRAMAS[clave.strip().lower()]
    except KeyError as error:
        conocidos = ", ".join(sorted(PROGRAMAS))
        raise KeyError(
            f"Programa {clave!r} no registrado. Opciones: {conocidos}."
        ) from error
