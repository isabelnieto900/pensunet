"""Figura del pensum al estilo del plan oficial, con aristas de prerrequisito.

La disposición imita el PDF del plan de estudios (columnas por semestre y
cajas de color por área). Encima se dibujan las aristas estrictas del DAG
de la sección II.A de Molontay et al. (2020).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.axes import Axes
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch

from pensunet.dominio.red import RedPrerrequisitos

# Paleta aproximada al PDF del programa de Física UD.
_COLOR_BASICAS = "#5B2C6F"
_COLOR_PROFESION = "#1A5276"
_COLOR_TRANSVERSAL = "#148F77"
_COLOR_LINEA = "#AF7AC5"
_COLOR_TEXTO = "#FFFFFF"
_COLOR_BORDE = "#1C1C1C"
_COLOR_ARISTA = "#5D6D7E"
_COLOR_FONDO = "#F7F5F2"
_COLOR_ENCABEZADO = "#2C3E50"

_ANCHO_CAJA = 1.55
_ALTO_CAJA = 1.05
_GAP_X = 0.35
_GAP_Y = 0.22

_ROMANOS = {
    1: "I",
    2: "II",
    3: "III",
    4: "IV",
    5: "V",
    6: "VI",
    7: "VII",
    8: "VIII",
    9: "IX",
    10: "X",
}


def dibujar_red(
    red: RedPrerrequisitos,
    ruta: str | Path | None = None,
    titulo: str = "Plan de estudios · red de prerrequisitos",
    mostrar_nombres: bool = True,
    mostrar_aristas: bool = True,
) -> Path | None:
    """Dibuja el pensum en grilla por semestre, como el plan oficial.

    Cada caja muestra nombre, código y créditos. El color sigue el área
    curricular del PDF (básicas, profesión, transversal, línea). Las
    aristas del DAG se dibujan por detrás, con trazo suave.

    ``mostrar_nombres`` se conserva por compatibilidad con la API anterior;
    en este estilo el nombre siempre aparece en la caja.
    """
    del mostrar_nombres  # el estilo pensum siempre etiqueta con nombre
    grafo = red.grafo
    por_semestre = _agrupar_por_semestre(grafo)
    cajas = _posiciones_cajas(por_semestre)

    max_filas = max((len(nodos) for nodos in por_semestre.values()), default=1)
    ancho = 10 * (_ANCHO_CAJA + _GAP_X) + 1.2
    alto = max_filas * (_ALTO_CAJA + _GAP_Y) + 2.8
    figura, eje = plt.subplots(figsize=(max(16.0, ancho * 1.05), max(9.0, alto * 0.95)))
    figura.patch.set_facecolor(_COLOR_FONDO)
    eje.set_facecolor(_COLOR_FONDO)

    if mostrar_aristas:
        _dibujar_aristas(eje, grafo, cajas)

    for nodo, caja in cajas.items():
        _dibujar_caja(eje, grafo, nodo, caja)

    for semestre in sorted(por_semestre):
        x = _x_columna(semestre)
        eje.text(
            x,
            _y_superior(max_filas) + _ALTO_CAJA * 0.75,
            f"Semestre {_ROMANOS.get(semestre, semestre)}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
            color=_COLOR_ENCABEZADO,
        )

    eje.set_title(titulo, fontsize=13, fontweight="bold", color=_COLOR_ENCABEZADO, pad=14)
    _leyenda(eje)
    eje.set_xlim(-0.4, _x_columna(10) + _ANCHO_CAJA / 2 + 0.5)
    eje.set_ylim(_y_inferior(max_filas) - 1.6, _y_superior(max_filas) + 1.3)
    eje.set_aspect("equal")
    eje.axis("off")
    figura.tight_layout()

    destino: Path | None = None
    if ruta is not None:
        destino = Path(ruta)
        destino.parent.mkdir(parents=True, exist_ok=True)
        figura.savefig(destino, dpi=180, bbox_inches="tight", facecolor=figura.get_facecolor())
    plt.close(figura)
    return destino


def _agrupar_por_semestre(grafo: nx.DiGraph) -> dict[int, list[int]]:
    por_semestre: dict[int, list[int]] = {}
    for nodo, datos in grafo.nodes(data=True):
        semestre = datos.get("semestre")
        clave = int(semestre) if semestre is not None else 0
        por_semestre.setdefault(clave, []).append(int(nodo))
    for semestre, nodos in por_semestre.items():
        por_semestre[semestre] = sorted(nodos, key=lambda n: _orden_en_semestre(grafo, n))
    return dict(sorted(por_semestre.items()))


def _orden_en_semestre(grafo: nx.DiGraph, nodo: int) -> tuple:
    """Obligatorias arriba, electivas abajo; dentro, más conexiones primero."""
    datos = grafo.nodes[nodo]
    clasificacion = str(datos.get("clasificacion") or "")
    es_electiva = 1 if "Electivo" in clasificacion else 0
    grado = grafo.out_degree(nodo) + grafo.in_degree(nodo)
    nombre = str(datos.get("nombre") or "")
    return (es_electiva, -grado, nombre)


def _posiciones_cajas(
    por_semestre: dict[int, list[int]],
) -> dict[int, tuple[float, float, float, float]]:
    """Devuelve (x_centro, y_centro, ancho, alto) por asignatura."""
    max_filas = max((len(nodos) for nodos in por_semestre.values()), default=1)
    cajas: dict[int, tuple[float, float, float, float]] = {}
    for semestre, nodos in por_semestre.items():
        x = _x_columna(semestre)
        for fila, nodo in enumerate(nodos):
            y = _y_superior(max_filas) - fila * (_ALTO_CAJA + _GAP_Y)
            cajas[nodo] = (x, y, _ANCHO_CAJA, _ALTO_CAJA)
    return cajas


def _x_columna(semestre: int) -> float:
    return (semestre - 1) * (_ANCHO_CAJA + _GAP_X) + _ANCHO_CAJA / 2


def _y_superior(max_filas: int) -> float:
    return (max_filas - 1) * (_ALTO_CAJA + _GAP_Y) / 2


def _y_inferior(max_filas: int) -> float:
    return -_y_superior(max_filas)


def _dibujar_caja(
    eje: Axes,
    grafo: nx.DiGraph,
    nodo: int,
    caja: tuple[float, float, float, float],
) -> None:
    x, y, ancho, alto = caja
    datos = grafo.nodes[nodo]
    color = _color_area(datos)
    rect = FancyBboxPatch(
        (x - ancho / 2, y - alto / 2),
        ancho,
        alto,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=0.6,
        edgecolor=_COLOR_BORDE,
        facecolor=color,
        zorder=3,
    )
    eje.add_patch(rect)

    nombre = _acortar_nombre(str(datos.get("nombre") or nodo), 34)
    lineas = _partir_texto(nombre, 18)
    creditos = datos.get("creditos")
    pie = f"{nodo}"
    if creditos is not None:
        pie = f"{nodo}  ·  {int(creditos)} cr"

    texto_y = y + alto * 0.18
    for linea in lineas[:3]:
        eje.text(
            x,
            texto_y,
            linea,
            ha="center",
            va="center",
            fontsize=5.2,
            color=_COLOR_TEXTO,
            fontweight="bold",
            zorder=4,
            wrap=False,
        )
        texto_y -= 0.18
    eje.text(
        x,
        y - alto * 0.32,
        pie,
        ha="center",
        va="center",
        fontsize=5,
        color=_COLOR_TEXTO,
        zorder=4,
    )


def _dibujar_aristas(
    eje: Axes,
    grafo: nx.DiGraph,
    cajas: dict[int, tuple[float, float, float, float]],
) -> None:
    for origen, destino in grafo.edges():
        if origen not in cajas or destino not in cajas:
            continue
        x0, y0, w0, _ = cajas[origen]
        x1, y1, w1, _ = cajas[destino]
        # Sale por la derecha de la caja origen y entra por la izquierda del destino.
        inicio = (x0 + w0 / 2, y0)
        fin = (x1 - w1 / 2, y1)
        radio = 0.12 if abs(y1 - y0) > 0.05 else 0.0
        estilo = f"arc3,rad={radio if y1 >= y0 else -radio}"
        flecha = FancyArrowPatch(
            inicio,
            fin,
            arrowstyle="-|>",
            mutation_scale=7,
            linewidth=0.55,
            color=_COLOR_ARISTA,
            alpha=0.45,
            connectionstyle=estilo,
            zorder=1,
        )
        eje.add_patch(flecha)


def _color_area(datos: dict) -> str:
    """Asigna el color del PDF según clasificación y nombre."""
    nombre = str(datos.get("nombre") or "").upper()
    clasificacion = str(datos.get("clasificacion") or "")
    grupo = str(datos.get("grupo_slot") or "")
    bloque = str(datos.get("bloque_electivo") or "")

    if (
        "Electivo" in clasificacion
        or "LÍNEA" in nombre
        or "TRABAJO DE GRADO" in nombre
        or "SEMINARIO DE INVESTIGACIÓN" in nombre
        or "Línea de aplicación" in grupo
        or "Línea de aplicación" in bloque
    ):
        return _COLOR_LINEA

    transversales = (
        "LENGUA",
        "CÁTEDRA",
        "ÉTICA",
        "ETICA",
        "HISTORIA",
        "EPISTEMOLOG",
        "REDACCIÓN",
        "REDACCION",
        "MODELOS Y GESTIÓN",
        "MODELOS Y GESTION",
        "GESTIÓN TECNOLÓGICA",
        "GESTION TECNOLOGICA",
        "DEMOCRACIA",
    )
    if "Complementario" in clasificacion or any(clave in nombre for clave in transversales):
        return _COLOR_TRANSVERSAL

    profesion = (
        "COMPUTACIONAL",
        "INSTRUMENTACIÓN",
        "INSTRUMENTACION",
        "ELECTRÓNICA",
        "ELECTRONICA",
        "ASTRONOM",
        "ASTROFÍSICA",
        "ASTROFISICA",
        "LENGUAJES Y ALGORITMOS",
        "MÉTODOS NUMÉRICOS",
        "METODOS NUMERICOS",
        "ELEMENTOS COMPUTACIONALES",
        "METROLOG",
        "AUTOMATIZACIÓN",
        "AUTOMATIZACION",
        "TALLER DE MÁQUINAS",
        "TALLER DE MAQUINAS",
        "PROBABILIDAD",
    )
    if any(clave in nombre for clave in profesion):
        return _COLOR_PROFESION

    return _COLOR_BASICAS


def _leyenda(eje: Axes) -> None:
    parches = [
        Patch(
            facecolor=_COLOR_BASICAS,
            edgecolor=_COLOR_BORDE,
            label="Ciencias básicas de la física",
        ),
        Patch(
            facecolor=_COLOR_PROFESION,
            edgecolor=_COLOR_BORDE,
            label="Ciencias básicas de la profesión",
        ),
        Patch(
            facecolor=_COLOR_TRANSVERSAL,
            edgecolor=_COLOR_BORDE,
            label="Área transversal socio-humanística",
        ),
        Patch(
            facecolor=_COLOR_LINEA,
            edgecolor=_COLOR_BORDE,
            label="Líneas de aplicación / grado",
        ),
    ]
    eje.legend(
        handles=parches,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=2,
        frameon=False,
        fontsize=7,
    )


def _acortar_nombre(nombre: str, maximo: int) -> str:
    texto = " ".join(nombre.split())
    if len(texto) <= maximo:
        return texto
    return texto[: maximo - 1].rstrip() + "…"


def _partir_texto(texto: str, ancho: int) -> list[str]:
    palabras = texto.split()
    if not palabras:
        return [texto]
    lineas: list[str] = []
    actual = palabras[0]
    for palabra in palabras[1:]:
        candidato = f"{actual} {palabra}"
        if len(candidato) <= ancho:
            actual = candidato
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas
