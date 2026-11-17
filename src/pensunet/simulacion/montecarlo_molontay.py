"""Monte Carlo del tiempo de grado (Molontay et al. 2020, sección III.B)."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

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
    3. Las electivas (clasificación «Electivo») son cupo: se elige una
       elegible al azar mientras falten créditos; si se reprueba y
       ``electivas_sin_reintento``, no se vuelve a cursar.
    4. Cupos de opciones (``grupo_slot`` con dos o más asignaturas no
       electivas, p. ej. idiomas, énfasis o profundizaciones): el
       estudiante elige una opción al azar entre las elegibles con p_i
       conocida y la cursa hasta aprobarla; las demás opciones no se
       exigen (``Escenario.opciones_excluyentes``).
    5. X es el semestre en que se cumplen obligatorias, cupos y el mínimo
       de créditos electivos. El artículo usa 10 000 réplicas.

    No se copia la convención BME de fijar p_i = 1 en electivas.
    Trabajo de grado y materias sin histórico deben traer p_i en
    ``tasas`` (p. ej. editadas en la interfaz); no se inventa 0 ni 1.
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
        plan = _estructura_del_plan(red, escenario)
        _exigir_tasas_completas(red, tasas_por_id, plan, escenario)

        rng = np.random.default_rng(escenario.semilla)
        tiempos: list[int] = []
        marcas: list[bool] = []
        censurados = 0
        reprobaciones: dict[int, int] = {}
        inscripciones: dict[int, int] = {}
        for _ in range(escenario.n_estudiantes):
            tiempo, censurado = _simular_estudiante(
                red, tasas_por_id, escenario, rng, reprobaciones, inscripciones, plan
            )
            tiempos.append(tiempo)
            marcas.append(censurado)
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
            censurados=tuple(marcas),
            reprobaciones=reprobaciones,
            inscripciones=inscripciones,
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
    plan: _Plan | None = None,
    escenario: Escenario | None = None,
) -> None:
    """Comprueba que haya p_i para todo lo que el grado exige.

    - Obligatorias: todas necesitan p_i.
    - Cupos de opciones: basta una opción con p_i; las opciones sin tasa
      no se eligen en la simulación.
    - Electivas: las que tienen p_i deben poder sumar el cupo de
      créditos; las demás no se eligen.
    """
    if plan is None or escenario is None:
        exigidas = {int(nodo) for nodo in red.grafo.nodes}
        cupos: dict[str, tuple[int, ...]] = {}
        electivas: frozenset[int] = frozenset()
        cupo = None
    else:
        exigidas = set(plan.obligatorias)
        cupos = plan.cupos
        electivas = plan.electivas
        cupo = escenario.creditos_electivas_minimos
    faltantes = sorted(codigo for codigo in exigidas if codigo not in tasas_por_id)
    if faltantes:
        muestra = ", ".join(str(codigo) for codigo in faltantes[:8])
        extra = "" if len(faltantes) <= 8 else f" y {len(faltantes) - 8} más"
        raise ValueError(
            "No se puede simular: faltan tasas de aprobación para "
            f"{muestra}{extra}."
        )
    sin_opcion = sorted(
        nombre
        for nombre, opciones in cupos.items()
        if not any(codigo in tasas_por_id for codigo in opciones)
    )
    if sin_opcion:
        raise ValueError(
            "No se puede simular: faltan tasas de aprobación en todas las opciones "
            f"del cupo {', '.join(sin_opcion)}."
        )
    if cupo is not None and electivas:
        potencial = sum(
            _creditos(red.grafo, codigo) for codigo in electivas if codigo in tasas_por_id
        )
        if potencial < cupo:
            raise ValueError(
                "No se puede simular: faltan tasas de electivas; las que tienen tasa "
                f"suman {potencial} créditos y el cupo exige {cupo}."
            )


@dataclass(frozen=True)
class _Plan:
    """Qué exige el grado: obligatorias, cupos de opciones y electivas."""

    obligatorias: frozenset[int]
    cupos: dict[str, tuple[int, ...]]
    electivas: frozenset[int]


def cupos_de_opciones(red: RedPrerrequisitos) -> dict[str, tuple[int, ...]]:
    """Cupos no electivos con dos o más opciones en el grafo.

    Agrupa por ``grupo_slot`` las asignaturas que no son «Electivo».
    Un cupo con varias opciones (idiomas, énfasis, profundizaciones) se
    cumple aprobando una sola de ellas.
    """
    grupos: dict[str, list[int]] = defaultdict(list)
    for nodo, datos in red.grafo.nodes(data=True):
        slot = datos.get("grupo_slot")
        if slot is None or _es_electiva(datos.get("clasificacion")):
            continue
        texto = str(slot).strip()
        if texto and texto.lower() != "nan":
            grupos[texto].append(int(nodo))
    return {nombre: tuple(sorted(ids)) for nombre, ids in grupos.items() if len(ids) >= 2}


def creditos_electivos_del_plan(red: RedPrerrequisitos) -> int:
    """Créditos electivos del plan: una opción por cupo electivo.

    Suma, por cada ``grupo_slot`` de asignaturas «Electivo», los créditos
    del cupo (el mayor entre sus opciones); las electivas sin
    ``grupo_slot`` cuentan una vez cada una. En Física da 18 (línea de
    aplicación I–IV: 4 + 5 + 4 + 5).
    """
    por_slot: dict[str, int] = {}
    sueltas = 0
    for nodo, datos in red.grafo.nodes(data=True):
        if not _es_electiva(datos.get("clasificacion")):
            continue
        creditos = _creditos(red.grafo, int(nodo))
        slot = datos.get("grupo_slot")
        texto = "" if slot is None else str(slot).strip()
        if texto and texto.lower() != "nan":
            por_slot[texto] = max(por_slot.get(texto, 0), creditos)
        else:
            sueltas += creditos
    return int(sum(por_slot.values()) + sueltas)


def _estructura_del_plan(red: RedPrerrequisitos, escenario: Escenario) -> _Plan:
    grafo = red.grafo
    electivas = {
        int(nodo)
        for nodo, datos in grafo.nodes(data=True)
        if _es_electiva(datos.get("clasificacion"))
    }
    cupos = cupos_de_opciones(red) if escenario.opciones_excluyentes else {}
    en_cupos = {codigo for opciones in cupos.values() for codigo in opciones}
    obligatorias = {int(nodo) for nodo in grafo.nodes} - electivas - en_cupos
    if escenario.creditos_electivas_minimos is None:
        # Comportamiento tipo paper: todas las electivas del grafo se exigen.
        obligatorias |= electivas
        electivas = set()
    return _Plan(
        obligatorias=frozenset(obligatorias),
        cupos=cupos,
        electivas=frozenset(electivas),
    )


def _es_electiva(clasificacion: object) -> bool:
    texto = "" if clasificacion is None else str(clasificacion)
    return "Electivo" in texto


def _simular_estudiante(
    red: RedPrerrequisitos,
    tasas_por_id: dict[int, float],
    escenario: Escenario,
    rng: np.random.Generator,
    reprobaciones: dict[int, int] | None = None,
    inscripciones: dict[int, int] | None = None,
    plan: _Plan | None = None,
) -> tuple[int, bool]:
    """Devuelve (X, censurado).

    Si se gradúa dentro del tope, ``censurado`` es falso. Si supera
    ``max_semestres`` o agota electivas sin reunir el cupo, se censura
    en el semestre de corte (no se aborta la muestra entera).
    """
    grafo = red.grafo
    if plan is None:
        plan = _estructura_del_plan(red, escenario)
    obligatorias = set(plan.obligatorias)
    # Solo se eligen electivas con p_i conocida.
    electivas = {codigo for codigo in plan.electivas if codigo in tasas_por_id}
    cupo = escenario.creditos_electivas_minimos
    pendientes = dict(plan.cupos)
    elegidas: list[int] = []

    aprobadas: set[int] = set()
    electivas_abandonadas: set[int] = set()
    creditos_electivos = 0
    tope = escenario.max_creditos_semestre
    fallos = reprobaciones if reprobaciones is not None else {}
    intentos = inscripciones if inscripciones is not None else {}

    def registrar(codigo: int, aprobo: bool) -> None:
        intentos[codigo] = intentos.get(codigo, 0) + 1
        if not aprobo:
            fallos[codigo] = fallos.get(codigo, 0) + 1

    for semestre in range(1, escenario.max_semestres + 1):
        for nombre in sorted(pendientes):
            opciones = [
                codigo
                for codigo in pendientes[nombre]
                if codigo in tasas_por_id
                and _elegible(codigo, grafo, aprobadas, semestre, escenario)
            ]
            if opciones:
                elegida = opciones[0] if len(opciones) == 1 else int(rng.choice(opciones))
                elegidas.append(elegida)
                del pendientes[nombre]
        candidatas_obl = [
            codigo
            for codigo in obligatorias
            if codigo not in aprobadas
            and _elegible(codigo, grafo, aprobadas, semestre, escenario)
        ] + [
            codigo
            for codigo in elegidas
            if codigo not in aprobadas
            and _elegible(codigo, grafo, aprobadas, semestre, escenario)
        ]
        carga = 0
        if tope is not None:
            candidatas_obl = _recortar_por_creditos(candidatas_obl, grafo, tope)
            carga = sum(_creditos(grafo, codigo) for codigo in candidatas_obl)
        for codigo in candidatas_obl:
            aprobo = bool(rng.random() < tasas_por_id[codigo])
            registrar(codigo, aprobo)
            if aprobo:
                aprobadas.add(codigo)

        if cupo is not None and creditos_electivos < cupo:
            disponibles = [
                codigo
                for codigo in electivas
                if codigo not in aprobadas
                and codigo not in electivas_abandonadas
                and _elegible(codigo, grafo, aprobadas, semestre, escenario)
            ]
            if tope is not None:
                disponibles = [
                    codigo
                    for codigo in disponibles
                    if carga + _creditos(grafo, codigo) <= tope
                ]
            if disponibles:
                # Una electiva por semestre: el cupo oficial es un slot
                # por nivel (I–IV); no se modela carga electiva múltiple.
                codigo = int(rng.choice(disponibles))
                aprobo = bool(rng.random() < tasas_por_id[codigo])
                registrar(codigo, aprobo)
                if aprobo:
                    aprobadas.add(codigo)
                    creditos = grafo.nodes[codigo].get("creditos")
                    creditos_electivos += int(creditos) if creditos is not None else 0
                elif escenario.electivas_sin_reintento:
                    electivas_abandonadas.add(codigo)

        if not pendientes and _cumple_grado(
            obligatorias | set(elegidas),
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


def _creditos(grafo, codigo: int) -> int:
    creditos = grafo.nodes[codigo].get("creditos")
    return int(creditos) if creditos is not None else 0


def _recortar_por_creditos(candidatas: list[int], grafo, tope: int) -> list[int]:
    """Obligatorias que caben en el tope, por semestre recomendado y código.

    Si la primera asignatura sola supera el tope, se inscribe igual para
    que la trayectoria no quede bloqueada para siempre.
    """
    ordenadas = sorted(
        candidatas,
        key=lambda codigo: (int(grafo.nodes[codigo].get("semestre") or 0), codigo),
    )
    elegidas: list[int] = []
    carga = 0
    for codigo in ordenadas:
        creditos = _creditos(grafo, codigo)
        if carga + creditos <= tope or not elegidas:
            elegidas.append(codigo)
            carga += creditos
    return elegidas


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
