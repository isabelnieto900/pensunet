"""Fachada única para cargar el pensum, medir la red y, más adelante, simular."""

import pandas as pd

from pensunet.datos.lector import LectorDatos
from pensunet.dominio.escenario import Escenario
from pensunet.dominio.indicadores import IndicadoresTopologicos, calcular_indicadores
from pensunet.dominio.red import RedPrerrequisitos, construir_red
from pensunet.dominio.reglas import ReglasCarrera
from pensunet.dominio.reglas_fisica import ReglasFisica
from pensunet.simulacion.estrategia import EstrategiaSimulacion, ResultadoSimulacion
from pensunet.simulacion.montecarlo_molontay import MonteCarloMolontay


class SimuladorPensum:
    """Punto de entrada de Pensunet.

    Reúne la lectura de datos, el DAG de la sección II.A, los indicadores
    de la sección II.B (ecuación (1) incluida) y la estrategia de
    simulación de las ecuaciones (3) y (4). Quien use el paquete no
    necesita conocer los subsistemas; la interfaz y los scripts hablan
    solo con esta clase.
    """

    def __init__(
        self,
        lector: LectorDatos,
        estrategia: EstrategiaSimulacion | None = None,
        reglas: ReglasCarrera | None = None,
    ) -> None:
        self._lector = lector
        self._estrategia = estrategia if estrategia is not None else MonteCarloMolontay()
        # Por defecto Física: es el único programa con revisión experta hoy.
        self._reglas = reglas if reglas is not None else ReglasFisica()
        self.pensum: pd.DataFrame | None = None
        self.prerequisitos: pd.DataFrame | None = None
        self.tasas: pd.DataFrame | None = None
        self.red: RedPrerrequisitos | None = None

    def cargar(self, aplicar_reglas: bool = True) -> RedPrerrequisitos:
        """Lee las tres tablas y construye el DAG.

        Sección II.A y ecuación (7) de Molontay et al. (2020). Con
        ``aplicar_reglas`` en verdadero se usa la ``ReglasCarrera``
        inyectada (por defecto ``ReglasFisica``). Con falso se conserva
        el extracto crudo, sin correcciones locales.
        """
        self.pensum = self._lector.leer_pensum()
        self.prerequisitos = self._lector.leer_prerequisitos()
        self.tasas = self._lector.leer_tasas_aprobacion()
        if aplicar_reglas:
            tablas = self._reglas.preparar(
                self.pensum,
                self.prerequisitos,
                self.tasas,
            )
            self.pensum = tablas.pensum
            self.prerequisitos = tablas.prerrequisitos
            self.tasas = tablas.tasas
            self.red = construir_red(
                self.pensum,
                self.prerequisitos,
                reglas_aplicadas=list(tablas.notas),
            )
        else:
            self.red = construir_red(self.pensum, self.prerequisitos)
        return self.red

    def indicadores(self) -> IndicadoresTopologicos:
        """Calcula bloqueo, posponimiento, intermediación y cuellos de botella.

        Sección II.B, ecuación (1) y ecuación (2).
        """
        return calcular_indicadores(self._exigir_red())

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

        Ecuaciones (3) y (4). Por defecto corre el Monte Carlo de la
        sección III.B con el cupo de 18 créditos de línea de Física.
        ``tasas`` permite explorar escenarios alterando p_i sin tocar
        el CSV (p. ej. desde la interfaz).
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
