"""Interfaz intercambiable de la simulación del tiempo de grado."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd

from pensunet.dominio.escenario import Escenario
from pensunet.dominio.red import RedPrerrequisitos


@dataclass(frozen=True)
class ResultadoSimulacion:
    """Muestra del tiempo de grado y sus resúmenes.

    ``tiempos`` permite
    estimar p(x) = P(X = x) por frecuencias, y ``media`` estima E(X).

    ``n_censurados`` cuenta trayectorias que no se graduaron dentro del
    tope ``max_semestres`` (o agotaron electivas): su tiempo queda en el
    tope o en el semestre de corte, para que la simulación no falle.

    ``censurados`` marca, trayectoria por trayectoria, cuáles no se
    graduaron. ``reprobaciones`` e ``inscripciones`` suman, por
    asignatura, los intentos fallidos y totales de toda la muestra; sirven
    para encontrar las asignaturas que más frenan el flujo simulado.
    """

    tiempos: tuple[int, ...]
    media: float
    desviacion: float
    n_censurados: int = 0
    tope_semestres: int | None = None
    censurados: tuple[bool, ...] = ()
    reprobaciones: dict[int, int] = field(default_factory=dict)
    inscripciones: dict[int, int] = field(default_factory=dict)

    def tasa_grado_en(self, semestres: int) -> float:
        """Proporción de la muestra graduada en a lo sumo ``semestres``.

        Las trayectorias censuradas no cuentan como graduadas.
        """
        if not self.tiempos:
            return 0.0
        marcas = self.censurados or tuple(False for _ in self.tiempos)
        graduados = sum(
            1
            for tiempo, censurado in zip(self.tiempos, marcas)
            if not censurado and tiempo <= semestres
        )
        return graduados / len(self.tiempos)

    def asignaturas_que_frenan(self, n: int = 10) -> list[tuple[int, float]]:
        """Las ``n`` asignaturas con más reprobaciones por estudiante simulado.

        Devuelve pares (código, reprobaciones medias por estudiante), de
        mayor a menor; empates por código.
        """
        total = max(1, len(self.tiempos))
        pares = [(codigo, veces / total) for codigo, veces in self.reprobaciones.items() if veces]
        pares.sort(key=lambda par: (-par[1], par[0]))
        return pares[: max(0, n)]

    def resumen(self, *, semestres_a_tiempo: int | None = None) -> pd.DataFrame:
        """Tabla de una fila con los indicadores principales del Monte Carlo.

        Si se indica ``semestres_a_tiempo`` (p. ej. N o N+2), incluye la
        proporción graduada en ese plazo.
        """
        fila: dict[str, float | int] = {
            "estudiantes": len(self.tiempos),
            "semestres_esperados": round(self.media, 4),
            "dispersion": round(self.desviacion, 4),
            "min_semestres": min(self.tiempos) if self.tiempos else 0,
            "max_semestres": max(self.tiempos) if self.tiempos else 0,
            "sin_grado_a_tiempo": int(self.n_censurados),
        }
        if semestres_a_tiempo is not None:
            clave = f"pct_grado_en_{int(semestres_a_tiempo)}"
            fila[clave] = round(100 * self.tasa_grado_en(int(semestres_a_tiempo)), 2)
        return pd.DataFrame([fila])

    def tabla_asignaturas_que_frenan(
        self,
        red: RedPrerrequisitos,
        n: int = 10,
    ) -> pd.DataFrame:
        """Las ``n`` materias que más frenan, con nombre y reprobaciones medias."""
        filas = []
        for codigo, media in self.asignaturas_que_frenan(n):
            datos = red.grafo.nodes[codigo] if codigo in red.grafo else {}
            filas.append(
                {
                    "id_asignatura": codigo,
                    "nombre": datos.get("nombre", ""),
                    "reprobaciones_por_estudiante": round(media, 4),
                }
            )
        return pd.DataFrame(
            filas,
            columns=["id_asignatura", "nombre", "reprobaciones_por_estudiante"],
        )


class EstrategiaSimulacion(ABC):
    """Algoritmo que aproxima la distribución del tiempo de grado.

    La fachada depende de
    esta interfaz, no de un algoritmo concreto, para poder sustituir el
    Monte Carlo del tiempo de grado sin reescribir el resto.
    """

    @abstractmethod
    def simular(
        self,
        red: RedPrerrequisitos,
        tasas: pd.DataFrame,
        escenario: Escenario,
    ) -> ResultadoSimulacion:
        """Estima la distribución de X bajo los supuestos del escenario.

        Ecuaciones (3) y (4). ``tasas`` aporta la estimación de p_i de
        la tabla de tasas de aprobación.
        """
