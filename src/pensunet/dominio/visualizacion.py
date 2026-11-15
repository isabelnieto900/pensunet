"""Figura del pensum y vista HTML interactiva de la red.

La disposición imita el PDF del plan (columnas por semestre y cajas por
área). Las aristas del DAG (Molontay et al., 2020, sección II.A) se
dibujan con trazo oscuro y halo claro para que se lean entre columnas.
``exportar_red_html`` genera una página donde al hacer clic en una
asignatura se resaltan sus prerrequisitos y sus continuaciones.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib import patheffects
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
_COLOR_ARISTA = "#1B2631"
_COLOR_FONDO = "#F7F5F2"
_COLOR_ENCABEZADO = "#2C3E50"

# Cajas más compactas y con más aire entre columnas para ver las flechas.
_ANCHO_CAJA = 1.15
_ALTO_CAJA = 0.78
_GAP_X = 0.55
_GAP_Y = 0.28

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
    curricular del PDF. Las aristas van por encima de las cajas, con halo
    claro, para no perderse detrás del relleno.

    ``mostrar_nombres`` se conserva por compatibilidad; el nombre siempre
    aparece en la caja.
    """
    del mostrar_nombres
    grafo = red.grafo
    por_semestre = _agrupar_por_semestre(grafo)
    cajas = _posiciones_cajas(por_semestre)

    max_filas = max((len(nodos) for nodos in por_semestre.values()), default=1)
    ancho = 10 * (_ANCHO_CAJA + _GAP_X) + 1.5
    alto = max_filas * (_ALTO_CAJA + _GAP_Y) + 3.0
    figura, eje = plt.subplots(figsize=(max(18.0, ancho * 1.15), max(10.0, alto * 1.05)))
    figura.patch.set_facecolor(_COLOR_FONDO)
    eje.set_facecolor(_COLOR_FONDO)

    for nodo, caja in cajas.items():
        _dibujar_caja(eje, grafo, nodo, caja)

    if mostrar_aristas:
        _dibujar_aristas(eje, grafo, cajas)

    for semestre in sorted(por_semestre):
        x = _x_columna(semestre)
        eje.text(
            x,
            _y_superior(max_filas) + _ALTO_CAJA * 0.85,
            f"Semestre {_ROMANOS.get(semestre, semestre)}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color=_COLOR_ENCABEZADO,
        )

    eje.set_title(titulo, fontsize=14, fontweight="bold", color=_COLOR_ENCABEZADO, pad=16)
    _leyenda(eje)
    eje.set_xlim(-0.5, _x_columna(10) + _ANCHO_CAJA / 2 + 0.6)
    eje.set_ylim(_y_inferior(max_filas) - 1.8, _y_superior(max_filas) + 1.5)
    eje.set_aspect("equal")
    eje.axis("off")
    figura.tight_layout()

    destino: Path | None = None
    if ruta is not None:
        destino = Path(ruta)
        destino.parent.mkdir(parents=True, exist_ok=True)
        figura.savefig(destino, dpi=200, bbox_inches="tight", facecolor=figura.get_facecolor())
    plt.close(figura)
    return destino


def exportar_red_html(
    red: RedPrerrequisitos,
    ruta: str | Path,
    titulo: str = "Plan de estudios · red de prerrequisitos",
) -> Path:
    """Exporta una página HTML interactiva de la red.

    Al hacer clic en una asignatura se resaltan sus prerrequisitos
    (entrantes) y las materias que la exigen (salientes). No añade
    dependencias nuevas: es HTML + SVG + JavaScript embebido.
    """
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    grafo = red.grafo
    por_semestre = _agrupar_por_semestre(grafo)
    cajas = _posiciones_cajas(por_semestre)
    max_filas = max((len(nodos) for nodos in por_semestre.values()), default=1)

    margen = 40.0
    escala = 70.0
    svg_ancho = margen * 2 + (_x_columna(10) + _ANCHO_CAJA / 2) * escala
    svg_alto = margen * 2 + (_y_superior(max_filas) - _y_inferior(max_filas) + 2.2) * escala

    def sx(x: float) -> float:
        return margen + (x + _ANCHO_CAJA / 2) * escala

    def sy(y: float) -> float:
        # SVG crece hacia abajo.
        return margen + (_y_superior(max_filas) + 1.0 - y) * escala

    nodos_js = []
    cajas_svg = []
    for nodo, (x, y, ancho, alto) in cajas.items():
        datos = grafo.nodes[nodo]
        color = _color_area(datos)
        nombre = str(datos.get("nombre") or nodo)
        creditos = datos.get("creditos")
        pie = f"{nodo}" if creditos is None else f"{nodo} · {int(creditos)} cr"
        left = sx(x - ancho / 2)
        top = sy(y + alto / 2)
        w = ancho * escala
        h = alto * escala
        lineas = _partir_texto(_acortar_nombre(nombre, 36), 16)[:3]
        texto = "<br/>".join(html.escape(linea) for linea in lineas)
        cajas_svg.append(
            f'<g class="nodo" id="n{nodo}" data-id="{nodo}">'
            f'<rect x="{left:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="8" ry="8" fill="{color}" stroke="{_COLOR_BORDE}" stroke-width="1.2"/>'
            f'<foreignObject x="{left + 4:.1f}" y="{top + 4:.1f}" '
            f'width="{w - 8:.1f}" height="{h - 8:.1f}">'
            f'<div xmlns="http://www.w3.org/1999/xhtml" class="caja-texto">'
            f"<strong>{texto}</strong><span>{html.escape(pie)}</span></div>"
            f"</foreignObject></g>"
        )
        nodos_js.append(
            {
                "id": int(nodo),
                "nombre": nombre,
                "semestre": int(datos.get("semestre") or 0),
                "previos": [int(p) for p in grafo.predecessors(nodo)],
                "siguientes": [int(s) for s in grafo.successors(nodo)],
            }
        )

    aristas_svg = []
    for origen, destino_nodo in grafo.edges():
        if origen not in cajas or destino_nodo not in cajas:
            continue
        x0, y0, w0, _ = cajas[origen]
        x1, y1, w1, _ = cajas[destino_nodo]
        x_ini, y_ini = sx(x0 + w0 / 2), sy(y0)
        x_fin, y_fin = sx(x1 - w1 / 2), sy(y1)
        dy = y_fin - y_ini
        ctrl = 28 if abs(dy) < 8 else (40 if dy > 0 else -40)
        d = (
            f"M {x_ini:.1f} {y_ini:.1f} "
            f"C {x_ini + ctrl:.1f} {y_ini:.1f}, "
            f"{x_fin - ctrl:.1f} {y_fin:.1f}, "
            f"{x_fin:.1f} {y_fin:.1f}"
        )
        aristas_svg.append(
            f'<path class="arista" id="e{origen}-{destino_nodo}" '
            f'data-from="{origen}" data-to="{destino_nodo}" '
            f'd="{d}" fill="none" stroke="{_COLOR_ARISTA}" '
            f'stroke-width="2.2" marker-end="url(#flecha)"/>'
        )

    encabezados = []
    for semestre in sorted(por_semestre):
        x = sx(_x_columna(semestre))
        y = sy(_y_superior(max_filas) + _ALTO_CAJA * 0.9)
        encabezados.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'class="semestre">Semestre {_ROMANOS.get(semestre, semestre)}</text>'
        )

    pagina = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(titulo)}</title>
  <style>
    body {{
      margin: 0; font-family: "Segoe UI", system-ui, sans-serif;
      background: {_COLOR_FONDO}; color: {_COLOR_ENCABEZADO};
    }}
    header {{
      padding: 1rem 1.5rem 0.5rem; max-width: 1200px;
    }}
    h1 {{ font-size: 1.25rem; margin: 0 0 0.35rem; }}
    .ayuda {{ font-size: 0.9rem; color: #555; margin: 0 0 0.75rem; }}
    #detalle {{
      min-height: 2.8rem; padding: 0.6rem 0.8rem; background: #fff;
      border: 1px solid #d0d0d0; border-radius: 8px; font-size: 0.9rem;
    }}
    .lienzo {{ overflow: auto; padding: 0.5rem 1rem 2rem; }}
    svg {{ display: block; background: {_COLOR_FONDO}; }}
    .caja-texto {{
      color: white; font-size: 10px; line-height: 1.15;
      display: flex; flex-direction: column; justify-content: center;
      height: 100%; text-align: center;
    }}
    .caja-texto strong {{ font-size: 10px; }}
    .caja-texto span {{ opacity: 0.9; margin-top: 2px; font-size: 9px; }}
    .nodo {{ cursor: pointer; }}
    .nodo rect {{ transition: opacity 0.15s, filter 0.15s; }}
    .arista {{ opacity: 0.35; transition: opacity 0.15s, stroke-width 0.15s; }}
    .semestre {{ fill: {_COLOR_ENCABEZADO}; font-size: 13px; font-weight: 700; }}
    .atenua .nodo rect {{ opacity: 0.22; }}
    .atenua .arista {{ opacity: 0.05; }}
    .nodo.activo rect, .nodo.previo rect, .nodo.siguiente rect {{
      opacity: 1; filter: drop-shadow(0 0 4px rgba(0,0,0,0.35));
    }}
    .nodo.previo rect {{ stroke: #f4d03f; stroke-width: 3; }}
    .nodo.siguiente rect {{ stroke: #5dade2; stroke-width: 3; }}
    .nodo.activo rect {{ stroke: #e74c3c; stroke-width: 3.5; }}
    .arista.activa {{ opacity: 0.95; stroke-width: 3.2; stroke: #c0392b; }}
    .leyenda {{
      display: flex; flex-wrap: wrap; gap: 0.75rem 1.25rem;
      padding: 0.5rem 1.5rem 1.5rem; font-size: 0.85rem;
    }}
    .leyenda span {{ display: inline-flex; align-items: center; gap: 0.4rem; }}
    .swatch {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid #333; }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(titulo)}</h1>
    <p class="ayuda">
      Clic en una asignatura para ver prerrequisitos (amarillo) y materias
      que la exigen (azul). Clic en el fondo para limpiar.
    </p>
    <div id="detalle">Ninguna asignatura seleccionada.</div>
  </header>
  <div class="lienzo">
    <svg id="red" width="{svg_ancho:.0f}" height="{svg_alto:.0f}"
         viewBox="0 0 {svg_ancho:.0f} {svg_alto:.0f}">
      <defs>
        <marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5"
                markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="{_COLOR_ARISTA}"/>
        </marker>
      </defs>
      {"".join(encabezados)}
      <g id="aristas">{"".join(aristas_svg)}</g>
      <g id="nodos">{"".join(cajas_svg)}</g>
    </svg>
  </div>
  <div class="leyenda">
    <span><i class="swatch" style="background:{_COLOR_BASICAS}"></i>
      Ciencias básicas de la física</span>
    <span><i class="swatch" style="background:{_COLOR_PROFESION}"></i>
      Ciencias básicas de la profesión</span>
    <span><i class="swatch" style="background:{_COLOR_TRANSVERSAL}"></i>
      Área transversal socio-humanística</span>
    <span><i class="swatch" style="background:{_COLOR_LINEA}"></i>
      Líneas de aplicación / grado</span>
  </div>
  <script>
    const NODOS = {json.dumps(nodos_js, ensure_ascii=False)};
    const porId = Object.fromEntries(NODOS.map(n => [n.id, n]));
    const svg = document.getElementById("red");
    const detalle = document.getElementById("detalle");

    function limpiar() {{
      svg.classList.remove("atenua");
      svg.querySelectorAll(".nodo").forEach(n => n.classList.remove("activo","previo","siguiente"));
      svg.querySelectorAll(".arista").forEach(a => a.classList.remove("activa"));
      detalle.textContent = "Ninguna asignatura seleccionada.";
    }}

    function seleccionar(id) {{
      const nodo = porId[id];
      if (!nodo) return;
      limpiar();
      svg.classList.add("atenua");
      const activo = document.getElementById("n" + id);
      if (activo) activo.classList.add("activo");
      nodo.previos.forEach(p => {{
        const el = document.getElementById("n" + p);
        if (el) el.classList.add("previo");
        const ar = document.getElementById("e" + p + "-" + id);
        if (ar) ar.classList.add("activa");
      }});
      nodo.siguientes.forEach(s => {{
        const el = document.getElementById("n" + s);
        if (el) el.classList.add("siguiente");
        const ar = document.getElementById("e" + id + "-" + s);
        if (ar) ar.classList.add("activa");
      }});
      const prev = nodo.previos.map(p => porId[p].nombre).join(", ") || "ninguno";
      const sig = nodo.siguientes.map(s => porId[s].nombre).join(", ") || "ninguna";
      detalle.innerHTML = "<strong>" + nodo.nombre + "</strong> (semestre " +
        nodo.semestre + ")<br/>Prerrequisitos: " + prev +
        "<br/>Habilita: " + sig;
    }}

    svg.querySelectorAll(".nodo").forEach(el => {{
      el.addEventListener("click", ev => {{
        ev.stopPropagation();
        seleccionar(Number(el.dataset.id));
      }});
    }});
    svg.addEventListener("click", limpiar);
  </script>
</body>
</html>
"""
    destino.write_text(pagina, encoding="utf-8")
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
        boxstyle="round,pad=0.015,rounding_size=0.06",
        linewidth=0.7,
        edgecolor=_COLOR_BORDE,
        facecolor=color,
        zorder=3,
    )
    eje.add_patch(rect)

    nombre = _acortar_nombre(str(datos.get("nombre") or nodo), 30)
    lineas = _partir_texto(nombre, 15)
    creditos = datos.get("creditos")
    pie = f"{nodo}" if creditos is None else f"{nodo} · {int(creditos)} cr"

    texto_y = y + alto * 0.16
    for linea in lineas[:3]:
        eje.text(
            x,
            texto_y,
            linea,
            ha="center",
            va="center",
            fontsize=4.8,
            color=_COLOR_TEXTO,
            fontweight="bold",
            zorder=4,
        )
        texto_y -= 0.14
    eje.text(
        x,
        y - alto * 0.30,
        pie,
        ha="center",
        va="center",
        fontsize=4.6,
        color=_COLOR_TEXTO,
        zorder=4,
    )


def _dibujar_aristas(
    eje: Axes,
    grafo: nx.DiGraph,
    cajas: dict[int, tuple[float, float, float, float]],
) -> None:
    halo = [
        patheffects.Stroke(linewidth=3.2, foreground="white", alpha=0.9),
        patheffects.Normal(),
    ]
    for origen, destino in grafo.edges():
        if origen not in cajas or destino not in cajas:
            continue
        x0, y0, w0, _ = cajas[origen]
        x1, y1, w1, _ = cajas[destino]
        inicio = (x0 + w0 / 2, y0)
        fin = (x1 - w1 / 2, y1)
        radio = 0.18 if abs(y1 - y0) > 0.04 else 0.05
        estilo = f"arc3,rad={radio if y1 >= y0 else -radio}"
        flecha = FancyArrowPatch(
            inicio,
            fin,
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=1.35,
            color=_COLOR_ARISTA,
            alpha=0.88,
            connectionstyle=estilo,
            zorder=5,
            clip_on=False,
        )
        flecha.set_path_effects(halo)
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
