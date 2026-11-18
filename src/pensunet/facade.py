"""Fachada única para cargar el pensum, medir la red y simular."""

from __future__ import annotations

import pandas as pd

from pensunet.datos.fabrica import FabricaLectores
from pensunet.datos.lector import LectorDatos
from pensunet.datos.programas import Programa, obtener_programa
from pensunet.dominio.complejidad import ComplejidadCurricular, calcular_complejidad
from pensunet.dominio.escenario import Escenario
from pensunet.dominio.indicadores import IndicadoresTopologicos, calcular_indicadores
from pensunet.dominio.red import RedPrerrequisitos, construir_red
from pensunet.dominio.reglas import FabricaReglas, ReglasCarrera
from pensunet.simulacion.estrategia import EstrategiaSimulacion, ResultadoSimulacion
from pensunet.simulacion.montecarlo import MonteCarloTiempoGrado


class SimuladorPensum:
    """Punto de entrada de Pensunet.

    Reúne la lectura de datos, el DAG, los indicadores
    topológicos (intermediación incluida) y la estrategia de
    simulación de las ecuaciones (3) y (4). Quien use el paquete no
    necesita conocer los subsistemas; la interfaz y los scripts hablan
    solo con esta clase.
    """

    def __init__(
        self,
        lector: LectorDatos,
        estrategia: EstrategiaSimulacion | None = None,
        programa: str | Programa | None = None,
        reglas: ReglasCarrera | None = None,
    ) -> None:
        self._lector = lector
        self._estrategia = estrategia if estrategia is not None else MonteCarloTiempoGrado()
        self._programa = (
            None
            if programa is None
            else (programa if isinstance(programa, Programa) else obtener_programa(programa))
        )
        # Sin reglas explícitas: las documentadas del programa, si se conoce.
        if reglas is None and self._programa is not None:
            reglas = FabricaReglas.crear(self._programa.clave)
        self._reglas = reglas
        self.pensum: pd.DataFrame | None = None
        self.prerequisitos: pd.DataFrame | None = None
        self.tasas: pd.DataFrame | None = None
        self.red: RedPrerrequisitos | None = None
        self.ajustes_aplicados: list[str] = []

    @classmethod
    def desde_programa(
        cls,
        clave: str,
        estrategia: EstrategiaSimulacion | None = None,
    ) -> SimuladorPensum:
        """Crea el simulador con los CSV del programa indicado."""
        programa = obtener_programa(clave)
        lector = FabricaLectores.crear("csv", **programa.rutas())
        return cls(lector, estrategia=estrategia, programa=programa)

    @property
    def programa(self) -> Programa | None:
        return self._programa

    @property
    def reglas(self) -> ReglasCarrera | None:
        return self._reglas

    def cargar(
        self,
        aplicar_ajustes_documentados: bool = True,
        *,
        aplicar_reglas: bool | None = None,
    ) -> RedPrerrequisitos:
        """Lee las tres tablas y construye el DAG.

        Con
        ``aplicar_ajustes_documentados`` se aplica la ``ReglasCarrera`` del
        simulador (por defecto, las filas del programa en
        ``ajustes_prerrequisitos.csv`` y las tasas por juicio experto de
        ``trabajo_de_grado.csv`` y ``juicio_experto.csv``). ``aplicar_reglas`` es el nombre
        de la etapa 2 y, si se da, tiene prioridad.
        """
        aplicar = aplicar_ajustes_documentados if aplicar_reglas is None else aplicar_reglas
        self.pensum = self._lector.leer_pensum()
        self.prerequisitos = self._lector.leer_prerequisitos()
        self.tasas = self._lector.leer_tasas_aprobacion()
        self.ajustes_aplicados = []
        if aplicar and self._reglas is not None:
            tablas = self._reglas.preparar(self.pensum, self.prerequisitos, self.tasas)
            self.pensum = tablas.pensum
            self.prerequisitos = tablas.prerrequisitos
            self.tasas = tablas.tasas
            self.ajustes_aplicados = list(tablas.notas)
        self.red = construir_red(
            self.pensum,
            self.prerequisitos,
            reglas_aplicadas=list(self.ajustes_aplicados),
        )
        return self.red

    def indicadores(self) -> IndicadoresTopologicos:
        """Calcula bloqueo, posponimiento, intermediación y cuellos.

        Bloqueo, posponimiento, intermediación y cuellos de botella.
        """
        return calcular_indicadores(self._exigir_red())

    def complejidad(self) -> ComplejidadCurricular:
        """Bloqueo, retraso y complejidad estructural (Curricular Analytics).

        Heileman et al. (2018); complementa los indicadores topológicos.
        """
        return calcular_complejidad(self._exigir_red())

    def tasa_de(self, id_asignatura: int) -> float | None:
        """Devuelve la tasa agregada, o None si el código no está en la tabla.

        Ecuación (7). None significa que p_i no se puede estimar con este
        histórico, no que la probabilidad sea cero o uno.
        """
        if self.tasas is None:
            raise RuntimeError("Hay que llamar cargar() antes de consultar tasas.")
        filas = self.tasas.loc[self.tasas["id_asignatura"] == int(id_asignatura)]
        if filas.empty:
            return None
        return float(filas.iloc[0]["tasa_aprobacion"])

    def simular(
        self,
        escenario: Escenario | None = None,
        tasas: pd.DataFrame | None = None,
    ) -> ResultadoSimulacion:
        """Delega la simulación en la estrategia configurada.

        Ecuaciones (3) y (4). ``tasas`` permite explorar escenarios
        alterando p_i sin tocar el CSV (p. ej. desde la interfaz).
        """
        return self._estrategia.simular(
            self._exigir_red(),
            tasas if tasas is not None else self._exigir_tasas(),
            escenario if escenario is not None else Escenario(),
        )

    def _exigir_red(self) -> RedPrerrequisitos:
        if self.red is None:
            raise RuntimeError("Hay que llamar cargar() antes de usar la red.")
        return self.red

    def _exigir_tasas(self) -> pd.DataFrame:
        if self.tasas is None:
            raise RuntimeError("Hay que llamar cargar() antes de usar las tasas.")
        return self.tasas
