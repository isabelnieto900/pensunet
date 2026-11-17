"""Monte Carlo del tiempo de grado (Molontay et al. 2020, sección III.B)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from pensunet.dominio.escenario import Escenario
from pensunet.dominio.red import RedPrerrequisitos
from pensunet.simulacion.estrategia import EstrategiaSimulacion, ResultadoSimulacion


class MonteCarloMolontay(EstrategiaSimulacion):
    """Simula estudiantes representativos para estimar p(x) y E(X).

    Molontay et al. (2020), sección III.B. El artículo muestra que la
    esperanza del máximo de geométricas (ecuaciones (8) y (9)) deja de
    ser tratable en cuanto los caminos se anidan, y por eso aproxima
    p(x) y E(X) —ecuaciones (3) y (4)— simulando estudiantes.

    Pasos:

    1. Estimar p_i con la ecuación (7) (tabla de tasas).
    2. Cada semestre, inscribir las obligatorias cuyo semestre
       recomendado ya llegó y cuyos prerrequisitos estrictos están
       aprobados; reintentar hasta aprobar.
    3. Las electivas del grafo de Física son cupo de línea: se elige
       una elegible al azar mientras falten créditos; si se reprueba y
       ``electivas_sin_reintento``, no se vuelve a cursar.
    4. X es el semestre en que se cumplen obligatorias y el mínimo de
       créditos electivos. El artículo usa 10 000 réplicas.

    No se copia la convención BME de fijar p_i = 1 en electivas.
    Trabajo de grado I y II reciben p_i = 1 vía ``ReglasFisica``.
    """

    def simular(
        self,
        red: RedPrerrequisitos,
        tasas: pd.DataFrame,
        escenario: Escenario,
    ) -> ResultadoSimulacion:
        """Estima la muestra de X. Ecuaciones (3), (4) y (7), sección III.B.

        Si una trayectoria no se gradúa dentro de ``max_semestres`` (o
        agota electivas), se censura en ese tope: la simulación termina
        igual y ``n_censurados`` lo reporta.
        """
        tasas_por_id = _mapa_tasas(tasas)
        _exigir_tasas_completas(red, tasas_por_id)

        rng = np.random.default_rng(escenario.semilla)
        tiempos: list[int] = []
        censurados = 0
        for _ in range(escenario.n_estudiantes):
            tiempo, censurado = _simular_estudiante(
                red, tasas_por_id, escenario, rng
            )
            tiempos.append(tiempo)
            if censurado:
                censurados += 1

        media = float(np.mean(tiempos))
        desviacion = float(np.std(tiempos, ddof=1)) if len(tiempos) > 1 else 0.0
        return ResultadoSimulacion(
            tiempos=tuple(tiempos),
            media=media,
            desviacion=desviacion,
            n_censurados=censurados,
            tope_semestres=escenario.max_semestres,
        )


def _mapa_tasas(tasas: pd.DataFrame) -> dict[int, float]:
    """Convierte la tabla de la ecuación (7) en un diccionario id → p_i."""
    resultado: dict[int, float] = {}
    for fila in tasas.to_dict(orient="records"):
        identificador = int(fila["id_asignatura"])
        probabilidad = float(fila["tasa_aprobacion"])
        if not (0.0 <= probabilidad <= 1.0) or math.isnan(probabilidad):
            raise ValueError(
                f"La tasa de {identificador} debe estar en [0, 1]; "
                f"se recibió {probabilidad}."
            )
        resultado[identificador] = probabilidad
    return resultado


def _exigir_tasas_completas(
    red: RedPrerrequisitos,
    tasas_por_id: dict[int, float],
) -> None:
    """Toda asignatura del grafo necesita p_i para poder simular."""
    faltantes = sorted(
        nodo for nodo in red.grafo.nodes if int(nodo) not in tasas_por_id
    )
    if faltantes:
        muestra = ", ".join(str(codigo) for codigo in faltantes[:8])
        extra = "" if len(faltantes) <= 8 else f" y {len(faltantes) - 8} más"
        raise ValueError(
            "No se puede simular: faltan tasas de aprobación para "
            f"{muestra}{extra}."
        )


def _es_electiva(clasificacion: object) -> bool:
    texto = "" if clasificacion is None else str(clasificacion)
    return "Electivo" in texto


def _simular_estudiante(
    red: RedPrerrequisitos,
    tasas_por_id: dict[int, float],
    escenario: Escenario,
    rng: np.random.Generator,
) -> tuple[int, bool]:
    """Devuelve (X, censurado).

    Si se gradúa dentro del tope, ``censurado`` es falso. Si supera
    ``max_semestres`` o agota electivas sin reunir el cupo, se censura
    en el semestre de corte (no se aborta la muestra entera).
    """
    grafo = red.grafo
    obligatorias = {
        int(nodo)
        for nodo, datos in grafo.nodes(data=True)
        if not _es_electiva(datos.get("clasificacion"))
    }
    electivas = {
        int(nodo)
        for nodo, datos in grafo.nodes(data=True)
        if _es_electiva(datos.get("clasificacion"))
    }
    cupo = escenario.creditos_electivas_minimos
    if cupo is None:
        # Comportamiento tipo paper: todos los nodos del grafo son exigidos.
        obligatorias = {int(nodo) for nodo in grafo.nodes}
        electivas = set()

    aprobadas: set[int] = set()
    electivas_abandonadas: set[int] = set()
    creditos_electivos = 0

    for semestre in range(1, escenario.max_semestres + 1):
        candidatas_obl = [
            codigo
            for codigo in obligatorias
            if codigo not in aprobadas
            and _elegible(codigo, grafo, aprobadas, semestre, escenario)
        ]
        for codigo in candidatas_obl:
            if rng.random() < tasas_por_id[codigo]:
                aprobadas.add(codigo)

        if cupo is not None and creditos_electivos < cupo:
            disponibles = [
                codigo
                for codigo in electivas
                if codigo not in aprobadas
                and codigo not in electivas_abandonadas
                and _elegible(codigo, grafo, aprobadas, semestre, escenario)
            ]
            if disponibles:
                # Una electiva por semestre: el cupo oficial es un slot
                # por nivel (I–IV); no se modela carga electiva múltiple.
                codigo = int(rng.choice(disponibles))
                if rng.random() < tasas_por_id[codigo]:
                    aprobadas.add(codigo)
                    creditos = grafo.nodes[codigo].get("creditos")
                    creditos_electivos += int(creditos) if creditos is not None else 0
                elif escenario.electivas_sin_reintento:
                    electivas_abandonadas.add(codigo)

        if _cumple_grado(
            obligatorias,
            aprobadas,
            cupo,
            creditos_electivos,
        ):
            return semestre, False

        if cupo is not None and not _queda_margen_electivo(
            electivas,
            aprobadas,
            electivas_abandonadas,
            grafo,
            creditos_electivos,
            cupo,
        ):
            # Sin margen electivo ya no puede graduarse: censura en este semestre.
            return semestre, True

    return escenario.max_semestres, True


def _elegible(
    codigo: int,
    grafo,
    aprobadas: set[int],
    semestre: int,
    escenario: Escenario,
) -> bool:
    """True si la red y el semestre recomendado permiten inscribir."""
    if escenario.respetar_semestre_recomendado:
        recomendado = grafo.nodes[codigo].get("semestre")
        if recomendado is not None and semestre < int(recomendado):
            return False
    previos = [int(previo) for previo in grafo.predecessors(codigo)]
    return all(previo in aprobadas for previo in previos)


def _cumple_grado(
    obligatorias: set[int],
    aprobadas: set[int],
    cupo: int | None,
    creditos_electivos: int,
) -> bool:
    if not obligatorias.issubset(aprobadas):
        return False
    if cupo is None:
        return True
    return creditos_electivos >= cupo


def _queda_margen_electivo(
    electivas: set[int],
    aprobadas: set[int],
    abandonadas: set[int],
    grafo,
    creditos_electivos: int,
    cupo: int,
) -> bool:
    """False si ya no hay forma de llegar al mínimo de créditos."""
    if creditos_electivos >= cupo:
        return True
    restantes = electivas - aprobadas - abandonadas
    potencial = creditos_electivos
    for codigo in restantes:
        creditos = grafo.nodes[codigo].get("creditos")
        potencial += int(creditos) if creditos is not None else 0
    return potencial >= cupo
