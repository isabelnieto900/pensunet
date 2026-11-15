"""Dibujo del DAG de prerrequisitos para documentación y ejemplos."""

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

from pensunet.dominio.red import RedPrerrequisitos


def dibujar_red(
    red: RedPrerrequisitos,
    ruta: str | Path | None = None,
    titulo: str = "Red de prerrequisitos",
    mostrar_nombres: bool = False,
) -> Path | None:
    """Dibuja el DAG agrupando nodos por semestre del plan.

    Sección II.A de Molontay et al. (2020). La disposición es por el
    atributo ``semestre`` (el del pensum), no por el nivel topológico.
    Si ``ruta`` no es None, guarda un PNG y la devuelve.
    """
    grafo = red.grafo
    posiciones = _posiciones_por_semestre(grafo)
    figura, eje = plt.subplots(figsize=(14, 8))
    nx.draw_networkx_edges(
        grafo,
        posiciones,
        ax=eje,
        arrows=True,
        arrowsize=10,
        edge_color="#666666",
        alpha=0.55,
        width=0.8,
    )
    nx.draw_networkx_nodes(
        grafo,
        posiciones,
        ax=eje,
        node_size=180,
        node_color="#4C78A8",
        linewidths=0.4,
        edgecolors="#222222",
    )
    etiquetas = {
        nodo: (
            str(grafo.nodes[nodo].get("nombre", nodo))[:18]
            if mostrar_nombres
            else str(nodo)
        )
        for nodo in grafo
    }
    nx.draw_networkx_labels(grafo, posiciones, labels=etiquetas, ax=eje, font_size=6)
    eje.set_title(titulo)
    eje.set_axis_off()
    figura.tight_layout()
    destino: Path | None = None
    if ruta is not None:
        destino = Path(ruta)
        destino.parent.mkdir(parents=True, exist_ok=True)
        figura.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(figura)
    return destino


def _posiciones_por_semestre(grafo: nx.DiGraph) -> dict[int, tuple[float, float]]:
    """Coloca cada asignatura en una columna según su semestre."""
    por_semestre: dict[int, list[int]] = {}
    for nodo, datos in grafo.nodes(data=True):
        semestre = datos.get("semestre")
        clave = int(semestre) if semestre is not None else 0
        por_semestre.setdefault(clave, []).append(int(nodo))

    posiciones: dict[int, tuple[float, float]] = {}
    for semestre, nodos in sorted(por_semestre.items()):
        nodos_ordenados = sorted(nodos)
        n = len(nodos_ordenados)
        for indice, nodo in enumerate(nodos_ordenados):
            y = (indice - (n - 1) / 2) * 1.4
            posiciones[nodo] = (float(semestre), y)
    return posiciones
