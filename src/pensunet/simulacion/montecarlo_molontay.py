"""Esqueleto del Monte Carlo descrito en la sección III.B."""

import pandas as pd

from pensunet.dominio.escenario import Escenario
from pensunet.dominio.red import RedPrerrequisitos
from pensunet.simulacion.estrategia import EstrategiaSimulacion, ResultadoSimulacion


class MonteCarloMolontay(EstrategiaSimulacion):
    """Monte Carlo del tiempo de grado. Todavía no simula.

    Molontay et al. (2020), sección III.B. El artículo muestra que la
    esperanza del máximo de geométricas (ecuaciones (8) y (9)) deja de
    ser tratable en cuanto los caminos se anidan, y por eso aproxima
    p(x) y E(X) —ecuaciones (3) y (4)— simulando estudiantes.

    Pasos previstos para la etapa 3, no ejecutados aquí:

    1. Estimar p_i con la ecuación (7), cociente de aprobados sobre
       inscritos. El número de intentos de la asignatura i es
       X_i ~ Geom(p_i), con esperanza 1/p_i (ensayos hasta el primer
       éxito, no la cuenta de fracasos).
    2. Para cada estudiante y cada semestre, inscribir las asignaturas
       cuyo semestre recomendado ya llegó y cuyos prerrequisitos
       estrictos están aprobados. El artículo supone que todas se abren
       cada semestre y que no hay semestres pasivos.
    3. Aprobar cada inscripción con probabilidad p_i, independiente del
       intento y de las demás asignaturas (supuestos de la sección III).
    4. El tiempo de grado X es el semestre en el que se aprueba la
       última asignatura exigida. Con las réplicas se estiman p(x) y
       E(X). El artículo usa 10 000 estudiantes (``Escenario``).

    No se copia la convención del caso BME de fijar p_i = 1 en las
    electivas: en este pensum también faltan tasas de obligatorias, y
    esa decisión queda para cuando la simulación exista.

    El efecto de atravesar una asignatura (ecuaciones (5), (6) y
    (10)-(13)) tampoco se calcula en este esqueleto.
    """

    def simular(
        self,
        red: RedPrerrequisitos,
        tasas: pd.DataFrame,
        escenario: Escenario,
    ) -> ResultadoSimulacion:
        """No genera tiempos de grado. Ecuaciones (3), (4) y (7), sección III.B."""
        raise NotImplementedError(
            "La simulación Monte Carlo de Molontay et al. (2020, sección III.B) "
            "se implementa en la etapa 3. Este esqueleto fija la interfaz y los "
            f"supuestos, pero todavía no genera tiempos de grado "
            f"({red.grafo.number_of_nodes()} asignaturas, {len(tasas)} tasas, "
            f"{escenario.n_estudiantes} estudiantes)."
        )
