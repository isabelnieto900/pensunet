"""Grafo dirigido de prerrequisitos del pensum."""

from collections.abc import Iterable

import networkx as nx
import pandas as pd


class RedPrerrequisitos:
    """Pensum representado como grafo dirigido acíclico.

    Sección II.A de Molontay et al. (2020): los nodos son asignaturas y
    hay una arista de i a j cuando i es prerrequisito estricto de j. Un
    ciclo significaría que dos asignaturas se exigen mutuamente, así que
    el grafo tiene que ser un DAG.
    """

    def __init__(
        self,
        grafo: nx.DiGraph,
        duracion_nominal: int,
        inconsistencias: list[str],
        prerrequisitos_debiles_excluidos: list[tuple[int, int]],
    ) -> None:
        if not validar_aciclicidad(grafo):
            raise ValueError(_mensaje_ciclo(grafo))
        self.grafo = grafo
        self.duracion_nominal = duracion_nominal
        self.inconsistencias = list(inconsistencias)
        self.prerrequisitos_debiles_excluidos = list(prerrequisitos_debiles_excluidos)
        self._asignar_niveles()

    def es_aciclico(self) -> bool:
        """Confirma que el grafo es un DAG. Sección II.A."""
        return validar_aciclicidad(self.grafo)

    def niveles(self) -> dict[int, int]:
        """Semestre mínimo de cada asignatura según los prerrequisitos.

        Sección II.A y supuesto de la sección III: una asignatura no puede
        cursarse antes de que sus prerrequisitos estén aprobados. El nivel
        es 1 si no tiene prerrequisitos y, si los tiene, uno más que el
        mayor nivel de ellos. No sustituye al semestre escrito en el plan:
        ese sigue en el atributo ``semestre`` del nodo.
        """
        return {int(nodo): int(datos["nivel"]) for nodo, datos in self.grafo.nodes(data=True)}

    def _asignar_niveles(self) -> None:
        """Escribe el nivel en cada nodo. Sección II.A."""
        for nodo in nx.topological_sort(self.grafo):
            previos = list(self.grafo.predecessors(nodo))
            if not previos:
                nivel = 1
            else:
                nivel = 1 + max(int(self.grafo.nodes[previo]["nivel"]) for previo in previos)
            self.grafo.nodes[nodo]["nivel"] = nivel


def validar_aciclicidad(grafo: nx.DiGraph) -> bool:
    """Indica si el grafo de prerrequisitos es acíclico.

    Sección II.A de Molontay et al. (2020): si hubiera un ciclo, alguna
    asignatura tendría que estar aprobada para poder cursar otra y al revés.
    """
    return nx.is_directed_acyclic_graph(grafo)


def construir_red(
    pensum: pd.DataFrame,
    prerequisitos: pd.DataFrame,
    solo_prerrequisitos_estrictos: bool = True,
) -> RedPrerrequisitos:
    """Construye el DAG a partir del pensum y de la tabla de aristas.

    Sección II.A de Molontay et al. (2020). La arista sale del
    prerrequisito y llega a la asignatura que lo exige. Con
    ``solo_prerrequisitos_estrictos`` se omiten las filas en las que
    ``debe_aprobado`` es falso: el artículo no considera los
    prerrequisitos débiles (los que permiten la inscripción en paralelo).

    La duración nominal es el máximo semestre declarado en el pensum, que
    en el artículo es la duración para la cual se diseñó el plan.
    """
    _exigir_columnas(pensum, ("id_asignatura", "nombre", "semestre"), "pensum")
    _exigir_columnas(
        prerequisitos,
        ("id_asignatura", "id_prerequisito", "debe_aprobado"),
        "prerrequisitos",
    )
    identificadores = [int(valor) for valor in pensum["id_asignatura"]]
    if len(identificadores) != len(set(identificadores)):
        raise ValueError("El pensum tiene identificadores de asignatura repetidos.")

    grafo = nx.DiGraph()
    for fila in pensum.to_dict(orient="records"):
        grafo.add_node(int(fila["id_asignatura"]), **_atributos_nodo(fila))

    inconsistencias: list[str] = []
    excluidos: list[tuple[int, int]] = []
    for fila in prerequisitos.to_dict(orient="records"):
        _agregar_arista(
            grafo,
            fila,
            solo_prerrequisitos_estrictos,
            inconsistencias,
            excluidos,
        )

    semestres = [
        int(datos["semestre"])
        for _, datos in grafo.nodes(data=True)
        if datos.get("semestre") is not None
    ]
    if not semestres:
        raise ValueError("Ninguna asignatura del pensum tiene semestre.")
    return RedPrerrequisitos(
        grafo=grafo,
        duracion_nominal=max(semestres),
        inconsistencias=inconsistencias,
        prerrequisitos_debiles_excluidos=excluidos,
    )


def _agregar_arista(
    grafo: nx.DiGraph,
    fila: dict,
    solo_estrictos: bool,
    inconsistencias: list[str],
    excluidos: list[tuple[int, int]],
) -> None:
    """Agrega i → j o registra por qué no entra al grafo. Sección II.A."""
    id_asignatura = int(fila["id_asignatura"])
    id_prerequisito = int(fila["id_prerequisito"])
    estricto = bool(fila["debe_aprobado"])
    _asegurar_nodo(grafo, id_asignatura, fila.get("nombre"), inconsistencias)
    _asegurar_nodo(grafo, id_prerequisito, fila.get("nombre_prerequisito"), inconsistencias)
    _revisar_orden_de_semestres(
        grafo,
        id_prerequisito,
        id_asignatura,
        estricto,
        inconsistencias,
    )
    if solo_estrictos and not estricto:
        excluidos.append((id_prerequisito, id_asignatura))
        return
    if grafo.has_edge(id_prerequisito, id_asignatura):
        inconsistencias.append(
            f"La arista {id_prerequisito} → {id_asignatura} está repetida en la tabla."
        )
        return
    grafo.add_edge(
        id_prerequisito,
        id_asignatura,
        orden=int(fila["orden"]) if fila.get("orden") is not None else None,
        debe_aprobado=estricto,
    )


def _asegurar_nodo(
    grafo: nx.DiGraph,
    identificador: int,
    nombre: object,
    inconsistencias: list[str],
) -> None:
    """Crea un nodo ausente del pensum y lo deja anotado. Sección II.A."""
    if identificador in grafo:
        return
    texto = str(nombre).strip() if nombre is not None else ""
    grafo.add_node(
        identificador,
        nombre=texto or f"Asignatura {identificador}",
        nombre_pensum=None,
        semestre=None,
        creditos=None,
        clasificacion=None,
        grupo_slot=None,
        linea_tematica=None,
        bloque_electivo=None,
    )
    inconsistencias.append(
        f"El identificador {identificador} aparece en prerrequisitos y no está en el pensum."
    )


def _revisar_orden_de_semestres(
    grafo: nx.DiGraph,
    id_prerequisito: int,
    id_asignatura: int,
    estricto: bool,
    inconsistencias: list[str],
) -> None:
    """Anota si el plan ubica el prerrequisito demasiado tarde.

    Sección II.A: un prerrequisito estricto tiene que poder aprobarse
    antes. Un prerrequisito débil admite el mismo semestre, no uno posterior.
    """
    semestre_prerequisito = grafo.nodes[id_prerequisito].get("semestre")
    semestre_asignatura = grafo.nodes[id_asignatura].get("semestre")
    if semestre_prerequisito is None or semestre_asignatura is None:
        return
    desordenado = (
        semestre_prerequisito >= semestre_asignatura
        if estricto
        else semestre_prerequisito > semestre_asignatura
    )
    if not desordenado:
        return
    tipo = "estricto" if estricto else "débil"
    inconsistencias.append(
        f"La asignatura {id_asignatura} (semestre {int(semestre_asignatura)}) tiene como "
        f"prerrequisito {tipo} {id_prerequisito} (semestre {int(semestre_prerequisito)})."
    )


def _atributos_nodo(fila: dict) -> dict:
    """Copia los atributos conocidos sin inventar los que no vienen."""
    return {
        "nombre": str(fila["nombre"]),
        "nombre_pensum": _opcional(fila.get("nombre_pensum")),
        "semestre": int(fila["semestre"]),
        "creditos": _entero_opcional(fila.get("creditos")),
        "clasificacion": _opcional(fila.get("clasificacion")),
        "grupo_slot": _opcional(fila.get("grupo_slot")),
        "linea_tematica": _opcional(fila.get("linea_tematica")),
        "bloque_electivo": _opcional(fila.get("bloque_electivo")),
    }


def _opcional(valor: object) -> str | None:
    if _ausente(valor):
        return None
    texto = str(valor).strip()
    if texto == "" or texto.lower() == "nan":
        return None
    return texto


def _entero_opcional(valor: object) -> int | None:
    if _ausente(valor):
        return None
    return int(valor)


def _ausente(valor: object) -> bool:
    """Reconoce None, pd.NA y NaN de numpy. Sección II.A: no se inventa el dato."""
    if valor is None:
        return True
    try:
        return bool(pd.isna(valor))
    except (TypeError, ValueError):
        return False


def _exigir_columnas(tabla: pd.DataFrame, columnas: Iterable[str], nombre: str) -> None:
    faltan = [columna for columna in columnas if columna not in tabla.columns]
    if faltan:
        lista = ", ".join(faltan)
        raise ValueError(f"A la tabla de {nombre} le faltan columnas internas: {lista}.")


def _mensaje_ciclo(grafo: nx.DiGraph) -> str:
    """Describe un ciclo. Sección II.A: el pensum no puede exigirlo."""
    ciclo = nx.find_cycle(grafo)
    tramo = " → ".join(str(origen) for origen, _ in ciclo)
    cierre = ciclo[-1][1]
    return (
        "La red de prerrequisitos tiene un ciclo y no es un DAG "
        f"(Molontay et al., 2020, sección II.A): {tramo} → {cierre}."
    )
