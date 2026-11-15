"""Reglas confirmadas del programa aplicadas al grafo de análisis.

Los CSV de referencia se conservan tal cual. Esta capa prepara las
tablas que alimentan ``construir_red``: excluye nodos que no deben
entrar al modelo, deja solo el inglés como segunda lengua y añade las
aristas estrictas que el extracto no trae. Cada decisión queda en la
bitácora ``notas``.
"""

from dataclasses import dataclass

import pandas as pd

# Segunda lengua: un solo idioma en el modelo (el de más histórico).
IDIOMAS_MODELO = frozenset({9901, 9902, 9903})

# Cupo del slot, no materias cursables.
SLOTS_GENERICOS_LINEA = frozenset({25139, 25144, 25147, 25152})

# Confirmadas como no ofrecidas aunque tengan tasa en el histórico.
NO_OFRECIDAS = frozenset({25176})

# Aristas estrictas confirmadas y ausentes del CSV: (prerrequisito, asignatura).
ARISTAS_CONFIRMADAS = (
    (25140, 25145),  # Introducción a la mecánica cuántica → Cuántica avanzada
    (25149, 25154),  # Trabajo de grado I → Trabajo de grado II
    (25141, 25146),  # Estado sólido → Ciencias de los materiales
    (25146, 25151),  # Ciencias de los materiales → Nanotecnología
    (25142, 25148),  # Modelos y gestión I → Modelos y gestión II
    (25148, 25153),  # Modelos y gestión II → Gestión tecnológica
    (4, 12),  # Cátedra F. J. de Caldas → Cátedra democracia y ciudadanía
    # Epistemología 25120 → 25127 ya viene en el CSV.
    # La tercera cátedra institucional suele ser "de contexto" (25246 en
    # tasas, fuera del pensum vigente). En Física el cupo del semestre 3
    # es Historia y filosofía de la ciencia I (25115); no se modela aún
    # 12 → 25115 hasta confirmar si esa equivalencia administrativa vale
    # como prerrequisito estricto.
)


@dataclass(frozen=True)
class TablasAnalisis:
    """Pensum y prerrequisitos listos para el DAG de análisis."""

    pensum: pd.DataFrame
    prerrequisitos: pd.DataFrame
    notas: tuple[str, ...]
    excluidos: frozenset[int]


def preparar_tablas_analisis(
    pensum: pd.DataFrame,
    prerrequisitos: pd.DataFrame,
    tasas: pd.DataFrame,
) -> TablasAnalisis:
    """Filtra nodos y completa aristas según las reglas confirmadas.

    No modifica los DataFrames de entrada. Las obligatorias sin tasa
    (p. ej. trabajo de grado) se conservan: la exclusión por tasa ausente
    solo aplica a electivas.
    """
    notas: list[str] = []
    ids_tasa = {int(valor) for valor in tasas["id_asignatura"]}
    excluidos: set[int] = set()

    for fila in pensum.to_dict(orient="records"):
        identificador = int(fila["id_asignatura"])
        motivo = _motivo_exclusion(fila, ids_tasa)
        if motivo is None:
            continue
        excluidos.add(identificador)
        notas.append(f"Se excluye {identificador} ({fila['nombre']}): {motivo}.")

    pensum_filtrado = pensum.loc[
        ~pensum["id_asignatura"].map(lambda valor: int(valor) in excluidos)
    ].copy()
    ids_vivos = {int(valor) for valor in pensum_filtrado["id_asignatura"]}

    prerrequisitos_filtrados = prerrequisitos.loc[
        prerrequisitos["id_asignatura"].map(lambda valor: int(valor) in ids_vivos)
        & prerrequisitos["id_prerequisito"].map(lambda valor: int(valor) in ids_vivos)
    ].copy()

    filas_nuevas = []
    for id_prerequisito, id_asignatura in ARISTAS_CONFIRMADAS:
        if id_prerequisito not in ids_vivos or id_asignatura not in ids_vivos:
            notas.append(
                f"No se pudo añadir la arista {id_prerequisito} → {id_asignatura}: "
                "falta algún extremo en el pensum filtrado."
            )
            continue
        ya = (
            (prerrequisitos_filtrados["id_asignatura"] == id_asignatura)
            & (prerrequisitos_filtrados["id_prerequisito"] == id_prerequisito)
        )
        if ya.any():
            notas.append(
                f"La arista confirmada {id_prerequisito} → {id_asignatura} "
                "ya estaba en la tabla."
            )
            continue
        nombre_asig = pensum_filtrado.loc[
            pensum_filtrado["id_asignatura"] == id_asignatura, "nombre"
        ].iloc[0]
        nombre_prev = pensum_filtrado.loc[
            pensum_filtrado["id_asignatura"] == id_prerequisito, "nombre"
        ].iloc[0]
        filas_nuevas.append(
            {
                "id_asignatura": id_asignatura,
                "nombre": nombre_asig,
                "id_prerequisito": id_prerequisito,
                "nombre_prerequisito": nombre_prev,
                "orden": 1,
                "debe_aprobado": True,
            }
        )
        notas.append(
            f"Se añade la arista estricta confirmada "
            f"{id_prerequisito} → {id_asignatura}."
        )

    if filas_nuevas:
        prerrequisitos_filtrados = pd.concat(
            [prerrequisitos_filtrados, pd.DataFrame(filas_nuevas)],
            ignore_index=True,
        )

    notas.append(
        f"Grafo de análisis: {len(pensum_filtrado)} asignaturas "
        f"(se excluyeron {len(excluidos)} del pensum crudo)."
    )
    return TablasAnalisis(
        pensum=pensum_filtrado.reset_index(drop=True),
        prerrequisitos=prerrequisitos_filtrados.reset_index(drop=True),
        notas=tuple(notas),
        excluidos=frozenset(excluidos),
    )


def _motivo_exclusion(fila: dict, ids_tasa: set[int]) -> str | None:
    """Devuelve el motivo de exclusión, o None si el nodo entra al grafo."""
    identificador = int(fila["id_asignatura"])
    if identificador in NO_OFRECIDAS:
        return "materia confirmada como no ofrecida"
    if identificador in SLOTS_GENERICOS_LINEA:
        return "fila genérica de cupo de línea de aplicación, no una materia"
    if _es_segunda_lengua(fila) and identificador not in IDIOMAS_MODELO:
        return "segunda lengua distinta del inglés (el modelo usa un solo idioma)"
    clasificacion = fila.get("clasificacion")
    texto = "" if clasificacion is None else str(clasificacion)
    if "Electivo" in texto and identificador not in ids_tasa:
        return "electiva sin tasa de aprobación (no se ofrece)"
    return None


def _es_segunda_lengua(fila: dict) -> bool:
    grupo = fila.get("grupo_slot")
    if grupo is None:
        return False
    return str(grupo).startswith("Segunda Lengua")
