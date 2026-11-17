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
# Camino más largo: rojo vivo, distinto del naranja de cuellos.
_COLOR_CAMINO = "#c0392b"
_COLOR_CAMINO_GLOW = "rgba(192, 57, 43, 0.7)"
_ALTURA_EMBEBIDO_PX = 540

# Cajas más compactas y con más aire entre columnas para ver las flechas.
_ANCHO_CAJA = 1.20
_ALTO_CAJA = 0.92
_GAP_X = 0.50
_GAP_Y = 0.26

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
    destino.write_text(
        html_de_la_red(red, titulo=titulo, embebido=False),
        encoding="utf-8",
    )
    return destino


def html_de_la_red(
    red: RedPrerrequisitos,
    titulo: str = "Plan de estudios · red de prerrequisitos",
    *,
    embebido: bool = False,
    oscuro: bool = False,
    resaltar: frozenset[int] | set[int] | tuple[int, ...] | None = None,
    camino: frozenset[int] | set[int] | tuple[int, ...] | None = None,
    metricas: dict[int, dict[str, float | int | str | None]] | None = None,
) -> str:
    """Devuelve el HTML interactivo de la red.

    Con ``embebido=True`` omite el título de página, usa fondo
    transparente y una vista compacta con zoom/pan (el plan cabe
    entero; al acercar se puede arrastrar).
    ``oscuro`` fija colores legibles dentro del iframe.
    ``resaltar`` marca cuellos de botella; ``camino`` el camino más largo.
    ``metricas`` aporta tasa, bloqueo, etc. al panel lateral al hacer clic.
    """
    destacados = frozenset(int(x) for x in (resaltar or ()))
    en_camino = tuple(int(x) for x in (camino or ()))
    ids_camino = frozenset(en_camino)
    aristas_camino = {
        (en_camino[i], en_camino[i + 1]) for i in range(len(en_camino) - 1)
    }
    datos_extra = metricas or {}
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
        lineas = _partir_texto(nombre, 15)[:4]
        texto = "<br/>".join(html.escape(linea) for linea in lineas)
        titulo_attr = html.escape(nombre, quote=True)
        clases = ["nodo"]
        if int(nodo) in destacados:
            clases.append("cuello")
        if int(nodo) in ids_camino:
            clases.append("camino")
        extra = datos_extra.get(int(nodo), {})
        cajas_svg.append(
            f'<g class="{" ".join(clases)}" id="n{nodo}" data-id="{nodo}">'
            f'<rect x="{left:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="8" ry="8" fill="{color}" stroke="{_COLOR_BORDE}" stroke-width="1.2"/>'
            f'<foreignObject x="{left + 3:.1f}" y="{top + 3:.1f}" '
            f'width="{w - 6:.1f}" height="{h - 6:.1f}">'
            f'<div xmlns="http://www.w3.org/1999/xhtml" class="caja-texto" '
            f'title="{titulo_attr}">'
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
                "cuello": int(nodo) in destacados,
                "camino": int(nodo) in ids_camino,
                "entrada": int(grafo.in_degree(nodo)),
                "salida": int(grafo.out_degree(nodo)),
                "tasa": extra.get("tasa"),
                "bloqueo": extra.get("bloqueo"),
                "posponimiento": extra.get("posponimiento"),
                "intermediacion": extra.get("intermediacion"),
                "motivo_cuello": extra.get("motivo_cuello"),
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
        en_critico = (int(origen), int(destino_nodo)) in aristas_camino
        clase_a = "arista camino" if en_critico else "arista"
        color_a = _COLOR_CAMINO if en_critico else _COLOR_ARISTA
        ancho_a = "4.5" if en_critico else "2.2"
        marcador = "url(#flecha-camino)" if en_critico else "url(#flecha)"
        aristas_svg.append(
            f'<path class="{clase_a}" id="e{origen}-{destino_nodo}" '
            f'data-from="{origen}" data-to="{destino_nodo}" '
            f'd="{d}" fill="none" stroke="{color_a}" '
            f'stroke-width="{ancho_a}" marker-end="{marcador}"/>'
        )
    encabezados = []
    for semestre in sorted(por_semestre):
        x = sx(_x_columna(semestre))
        y = sy(_y_superior(max_filas) + _ALTO_CAJA * 0.9)
        encabezados.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'class="semestre">Semestre {_ROMANOS.get(semestre, semestre)}</text>'
        )

    if embebido and oscuro:
        # Fondo propio: transparent + height % colapsaba el SVG en el iframe.
        fondo = "#0e1117"
        color_texto = "#e8eeeb"
        color_detalle_bg = "#1c2421"
        color_detalle_borde = "#3d4f47"
        color_semestre = "#d7e2dc"
        titulo_html = ""
        color_scheme = "dark"
    elif embebido:
        fondo = "#ffffff"
        color_texto = "#1a2e28"
        color_detalle_bg = "#f4f6f5"
        color_detalle_borde = "#d5ddd8"
        color_semestre = _COLOR_ENCABEZADO
        titulo_html = ""
        color_scheme = "light"
    else:
        fondo = _COLOR_FONDO
        color_texto = _COLOR_ENCABEZADO
        color_detalle_bg = "#ffffff"
        color_detalle_borde = "#d0d0d0"
        color_semestre = _COLOR_ENCABEZADO
        titulo_html = f"<h1>{html.escape(titulo)}</h1>"
        color_scheme = "light"

    leyenda_extra = ""
    if destacados:
        leyenda_extra += (
            '<span><i class="swatch cuello-swatch"></i> Cuello de botella (ec. 2)</span>'
        )
    if en_camino:
        leyenda_extra += (
            '<span><i class="swatch camino-swatch"></i> Camino más largo</span>'
        )
    svg_attrs = (
        f'width="100%" height="{_ALTURA_EMBEBIDO_PX}" '
        f'viewBox="0 0 {svg_ancho:.0f} {svg_alto:.0f}" '
        f'preserveAspectRatio="xMidYMid meet"'
        if embebido
        else (
            f'width="{svg_ancho:.0f}" height="{svg_alto:.0f}" '
            f'viewBox="0 0 {svg_ancho:.0f} {svg_alto:.0f}"'
        )
    )
    zoom_bar = ""
    if embebido:
        zoom_bar = """
    <div class="zoom-flotante">
      <button type="button" id="z-out" title="Alejar">-</button>
      <button type="button" id="z-fit" title="Ver plan completo">Encajar</button>
      <button type="button" id="z-in" title="Acercar">+</button>
      <span id="z-pct">100%</span>
    </div>"""
    clases_raiz = ["pensunet-red"]
    if embebido:
        clases_raiz.append("embebido")
    if oscuro and embebido:
        clases_raiz.append("oscuro")
    if en_camino:
        clases_raiz.append("con-camino")
    if destacados:
        clases_raiz.append("con-cuellos")
    clase_raiz = " ".join(clases_raiz)
    altura_cuerpo = (
        f"{_ALTURA_EMBEBIDO_PX}px" if embebido else "auto"
    )
    # Fragmento para st.html (sin iframe) o documento completo para exportar.
    estilos = f"""
    .pensunet-red {{
      margin: 0; padding: 0; overflow: hidden;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: {fondo}; color: {color_texto};
      color-scheme: {color_scheme};
      width: 100%;
      box-sizing: border-box;
    }}
    .pensunet-red:not(.embebido) {{ overflow: auto; }}
    .pensunet-red h1 {{
      font-size: 1.25rem; margin: 0 0 0.35rem; padding: 0.5rem 0.25rem 0;
    }}
    .pensunet-red .cuerpo {{
      display: block;
      position: relative;
      height: {altura_cuerpo};
      box-sizing: border-box;
      padding: {"0" if embebido else "0.5rem"};
      overflow: hidden;
    }}
    .pensunet-red .vista {{
      position: absolute; inset: 0;
      overflow: hidden; background: {fondo};
      min-height: {altura_cuerpo};
    }}
    .pensunet-red .panel-lado {{
      position: absolute; top: 0; right: 0; bottom: 0;
      width: min(250px, 34%);
      z-index: 3;
      background: {color_detalle_bg};
      padding: 0.55rem 0.65rem;
      color: {color_texto};
      font-size: 0.86rem;
      line-height: 1.35;
      overflow: auto;
      border-left: 1px solid {color_detalle_borde};
      box-shadow: -6px 0 16px rgba(0,0,0,0.18);
    }}
    .pensunet-red .panel-lado h2 {{
      font-size: 0.92rem; margin: 0 0 0.4rem; font-weight: 700;
    }}
    .pensunet-red .panel-lado .dato {{
      margin: 0.3rem 0; padding: 0.3rem 0;
      border-top: 1px solid {color_detalle_borde};
    }}
    .pensunet-red .panel-lado .etiqueta {{ opacity: 0.7; font-size: 0.76rem; }}
    .pensunet-red .zoom-flotante {{
      position: absolute; top: 0.35rem; left: 0.35rem; z-index: 2;
      display: flex; align-items: center; gap: 0.3rem;
      padding: 0.2rem 0.35rem; border-radius: 6px;
      background: color-mix(in srgb, {color_detalle_bg} 92%, transparent);
      font-size: 0.8rem;
    }}
    .pensunet-red .zoom-flotante button {{
      font: inherit; min-width: 1.7rem; padding: 0.12rem 0.4rem;
      border-radius: 4px; border: 1px solid {color_detalle_borde};
      background: transparent; color: inherit; cursor: pointer;
    }}
    .pensunet-red .lienzo {{
      overflow: hidden; padding: 0; width: 100%;
      height: 100%;
      cursor: grab;
      box-sizing: border-box;
    }}
    .pensunet-red .lienzo.arrastrando {{ cursor: grabbing; }}
    .pensunet-red svg {{
      display: block; width: 100%; height: 100%;
      background: {fondo}; touch-action: none;
    }}
    .pensunet-red .caja-texto {{
      color: white; line-height: 1.12;
      display: flex; flex-direction: column; justify-content: center;
      align-items: center; height: 100%; text-align: center;
      overflow: hidden; padding: 1px 2px; box-sizing: border-box;
      pointer-events: none;
    }}
    .pensunet-red .caja-texto strong {{
      font-size: 9px; font-weight: 700; max-width: 100%;
      overflow-wrap: anywhere; word-break: break-word;
    }}
    .pensunet-red .caja-texto span {{
      opacity: 0.95; margin-top: 3px; font-size: 8px; flex-shrink: 0;
    }}
    .pensunet-red .nodo {{ cursor: pointer; }}
    .pensunet-red .nodo rect {{
      opacity: 1;
      transition: opacity 0.15s, filter 0.15s;
      pointer-events: all;
    }}
    .pensunet-red .arista {{
      opacity: 0.4; transition: opacity 0.15s, stroke-width 0.15s;
    }}
    .pensunet-red .semestre {{
      fill: {color_semestre}; font-size: 13px; font-weight: 700;
    }}
    .pensunet-red.con-camino .nodo:not(.camino) rect {{ opacity: 0.82; }}
    .pensunet-red.con-camino .nodo.camino rect {{ opacity: 1; }}
    .pensunet-red.con-camino .arista:not(.camino) {{ opacity: 0.16; }}
    .pensunet-red .atenua .nodo rect {{ opacity: 0.35; }}
    .pensunet-red .atenua .arista {{ opacity: 0.08; }}
    .pensunet-red .atenua .arista.camino {{ opacity: 0.65; }}
    .pensunet-red .nodo.activo rect,
    .pensunet-red .nodo.previo rect,
    .pensunet-red .nodo.siguiente rect,
    .pensunet-red .atenua .nodo.cuello rect,
    .pensunet-red .atenua .nodo.camino rect {{
      opacity: 1; filter: drop-shadow(0 0 4px rgba(0,0,0,0.35));
    }}
    .pensunet-red .nodo.previo rect {{ stroke: #f4d03f; stroke-width: 3; }}
    .pensunet-red .nodo.siguiente rect {{ stroke: #5dade2; stroke-width: 3; }}
    .pensunet-red .nodo.activo rect {{ stroke: #e74c3c; stroke-width: 3.5; }}
    .pensunet-red .nodo.camino rect {{
      stroke: {_COLOR_CAMINO}; stroke-width: 4.2;
      filter: drop-shadow(0 0 7px {_COLOR_CAMINO_GLOW});
    }}
    .pensunet-red .nodo.cuello rect {{
      stroke: #e67e22; stroke-width: 3.2;
      filter: drop-shadow(0 0 5px rgba(230, 126, 34, 0.55));
    }}
    .pensunet-red .nodo.cuello.camino rect {{
      stroke: #a93226; stroke-width: 4.4;
      filter: drop-shadow(0 0 7px rgba(169, 50, 38, 0.85));
    }}
    .pensunet-red .arista.camino {{
      opacity: 1; stroke: {_COLOR_CAMINO}; stroke-width: 4.5;
    }}
    .pensunet-red .arista.activa {{
      opacity: 0.95; stroke-width: 3.2; stroke: {_COLOR_CAMINO};
    }}
    .pensunet-red .leyenda {{
      display: {"none" if embebido else "flex"};
      flex-wrap: wrap; gap: 0.75rem 1.25rem;
      padding: 0.35rem 0.15rem 0.25rem; font-size: 0.85rem;
      opacity: 0.92;
    }}
    .pensunet-red .leyenda span {{
      display: inline-flex; align-items: center; gap: 0.4rem;
    }}
    .pensunet-red .swatch {{
      width: 14px; height: 14px; border-radius: 3px; border: 1px solid #333;
    }}
    .pensunet-red .cuello-swatch {{ background: #e67e22; }}
    .pensunet-red .camino-swatch {{ background: {_COLOR_CAMINO}; }}
"""
    cuerpo = f"""
  {titulo_html}
  <div class="cuerpo">
    <div class="vista">
      {zoom_bar}
      <div class="lienzo" id="viewport">
        <svg id="red" {svg_attrs}>
          <defs>
            <marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="{_COLOR_ARISTA}"/>
            </marker>
            <marker id="flecha-camino" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="{_COLOR_CAMINO}"/>
            </marker>
          </defs>
          {"".join(encabezados)}
          <g id="aristas">{"".join(aristas_svg)}</g>
          <g id="nodos">{"".join(cajas_svg)}</g>
        </svg>
      </div>
    </div>
    <aside class="panel-lado">
      <h2>Asignatura</h2>
      <div id="detalle">Clic en una materia del plan para ver prerrequisitos,
        continuaciones y métricas.</div>
    </aside>
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
    {leyenda_extra}
  </div>
"""
    script = f"""
  <script>
    (function() {{
    let raiz = document.currentScript
      && document.currentScript.closest(".pensunet-red");
    if (!raiz) {{
      const todos = document.querySelectorAll(".pensunet-red");
      raiz = todos[todos.length - 1];
    }}
    if (!raiz) return;
    const NODOS = {json.dumps(nodos_js, ensure_ascii=False)};
    const W = {svg_ancho:.1f}, H = {svg_alto:.1f};
    const EMBEBIDO = {str(embebido).lower()};
    const porId = Object.fromEntries(NODOS.map(n => [n.id, n]));
    const svg = raiz.querySelector("#red");
    const viewport = raiz.querySelector("#viewport");
    const detalle = raiz.querySelector("#detalle");
    let vb = {{x: 0, y: 0, w: W, h: H}};
    let arrastrando = false, lastX = 0, lastY = 0, moved = false;

    function aplicarVista() {{
      svg.setAttribute("viewBox", vb.x + " " + vb.y + " " + vb.w + " " + vb.h);
      const pct = raiz.querySelector("#z-pct");
      if (pct) pct.textContent = Math.round(100 * W / vb.w) + "%";
    }}

    function encajar() {{
      vb = {{x: 0, y: 0, w: W, h: H}};
      aplicarVista();
    }}

    function zoomEn(factor, cx, cy) {{
      const nw = Math.min(W * 3, Math.max(W * 0.12, vb.w * factor));
      const nh = nw * (H / W);
      const px = (cx - vb.x) / vb.w;
      const py = (cy - vb.y) / vb.h;
      vb.w = nw; vb.h = nh;
      vb.x = cx - px * vb.w;
      vb.y = cy - py * vb.h;
      aplicarVista();
    }}

    function fmt(valor, digitos) {{
      if (valor === null || valor === undefined) return "—";
      if (typeof valor === "number") return Number(valor).toFixed(digitos);
      return String(valor);
    }}

    function limpiar() {{
      svg.classList.remove("atenua");
      svg.querySelectorAll(".nodo").forEach(n =>
        n.classList.remove("activo","previo","siguiente"));
      svg.querySelectorAll(".arista").forEach(a => a.classList.remove("activa"));
      detalle.innerHTML = "Clic en una materia del plan para ver " +
        "prerrequisitos, continuaciones y métricas.";
    }}

    function seleccionar(id) {{
      const nodo = porId[id];
      if (!nodo) return;
      limpiar();
      svg.classList.add("atenua");
      const activo = raiz.querySelector("#n" + id);
      if (activo) activo.classList.add("activo");
      nodo.previos.forEach(p => {{
        const el = raiz.querySelector("#n" + p);
        if (el) el.classList.add("previo");
        const ar = raiz.querySelector("#e" + p + "-" + id);
        if (ar) ar.classList.add("activa");
      }});
      nodo.siguientes.forEach(s => {{
        const el = raiz.querySelector("#n" + s);
        if (el) el.classList.add("siguiente");
        const ar = raiz.querySelector("#e" + id + "-" + s);
        if (ar) ar.classList.add("activa");
      }});
      const prev = nodo.previos.map(p => porId[p].nombre).join(", ") || "ninguno";
      const sig = nodo.siguientes.map(s => porId[s].nombre).join(", ") || "ninguna";
      const marcas = [];
      if (nodo.cuello) marcas.push("cuello de botella");
      if (nodo.camino) marcas.push("camino más largo");
      const marca = marcas.length ? " · " + marcas.join(", ") : "";
      let html = "<strong>" + nodo.nombre + "</strong><br/>id " + nodo.id +
        " · semestre " + nodo.semestre + marca;
      html += "<div class='dato'><span class='etiqueta'>Prerrequisitos</span><br/>"
        + prev + "</div>";
      html += "<div class='dato'><span class='etiqueta'>Habilita</span><br/>"
        + sig + "</div>";
      html += "<div class='dato'><span class='etiqueta'>Grado entrada / salida"
        + "</span><br/>" + nodo.entrada + " / " + nodo.salida + "</div>";
      html += "<div class='dato'><span class='etiqueta'>Tasa de aprobación p_i</span><br/>" +
        fmt(nodo.tasa, 3) + "</div>";
      html += "<div class='dato'><span class='etiqueta'>Bloqueo (descendientes)</span><br/>" +
        fmt(nodo.bloqueo, 0) + "</div>";
      html += "<div class='dato'><span class='etiqueta'>Posponimiento 1/(k+1)</span><br/>" +
        fmt(nodo.posponimiento, 3) + "</div>";
      html += "<div class='dato'><span class='etiqueta'>Intermediación</span><br/>" +
        fmt(nodo.intermediacion, 4) + "</div>";
      if (nodo.motivo_cuello) {{
        html += "<div class='dato'><span class='etiqueta'>Por qué es cuello</span><br/>" +
          nodo.motivo_cuello + "</div>";
      }}
      detalle.innerHTML = html;
    }}

    function esNodo(el) {{
      return el && el.closest && el.closest(".nodo");
    }}

    svg.querySelectorAll(".nodo").forEach(el => {{
      el.addEventListener("pointerup", ev => {{
        if (moved) return;
        ev.stopPropagation();
        seleccionar(Number(el.dataset.id));
      }});
    }});

    if (EMBEBIDO) {{
      const zIn = raiz.querySelector("#z-in");
      const zOut = raiz.querySelector("#z-out");
      const zFit = raiz.querySelector("#z-fit");
      zIn.addEventListener("click", ev => {{
        ev.stopPropagation();
        zoomEn(0.8, vb.x + vb.w/2, vb.y + vb.h/2);
      }});
      zOut.addEventListener("click", ev => {{
        ev.stopPropagation();
        zoomEn(1.25, vb.x + vb.w/2, vb.y + vb.h/2);
      }});
      zFit.addEventListener("click", ev => {{
        ev.stopPropagation(); encajar();
      }});
      viewport.addEventListener("wheel", ev => {{
        ev.preventDefault();
        const rect = svg.getBoundingClientRect();
        const mx = vb.x + ((ev.clientX - rect.left) / rect.width) * vb.w;
        const my = vb.y + ((ev.clientY - rect.top) / rect.height) * vb.h;
        zoomEn(ev.deltaY < 0 ? 0.85 : 1.18, mx, my);
      }}, {{passive: false}});
      viewport.addEventListener("pointerdown", ev => {{
        if (ev.button !== 0) return;
        if (esNodo(ev.target)) {{
          moved = false;
          return;
        }}
        arrastrando = true; moved = false;
        lastX = ev.clientX; lastY = ev.clientY;
        viewport.classList.add("arrastrando");
        viewport.setPointerCapture(ev.pointerId);
      }});
      viewport.addEventListener("pointermove", ev => {{
        if (!arrastrando) return;
        const rect = svg.getBoundingClientRect();
        const dx = (ev.clientX - lastX) / rect.width * vb.w;
        const dy = (ev.clientY - lastY) / rect.height * vb.h;
        if (Math.abs(ev.clientX - lastX) + Math.abs(ev.clientY - lastY) > 4)
          moved = true;
        vb.x -= dx; vb.y -= dy;
        lastX = ev.clientX; lastY = ev.clientY;
        aplicarVista();
      }});
      viewport.addEventListener("pointerup", ev => {{
        const huboArrastre = moved;
        arrastrando = false;
        viewport.classList.remove("arrastrando");
        if (!huboArrastre && !esNodo(ev.target)) {{
          limpiar();
        }}
        setTimeout(() => {{ moved = false; }}, 40);
      }});
      encajar();
    }} else {{
      svg.addEventListener("pointerup", ev => {{
        if (!moved && !esNodo(ev.target)) limpiar();
      }});
    }}
    }})();
  </script>
"""
    fragmento = (
        f'<div class="{clase_raiz}">\n'
        f"<style>{estilos}</style>\n"
        f"{cuerpo}\n"
        f"{script}\n"
        f"</div>"
    )
    # Siempre documento completo: st.iframe (y exportar) necesitan <html>.
    # st.html sanitiza SVG/JS y deja la red en blanco.
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="color-scheme" content="{color_scheme}"/>
  <title>{html.escape(titulo)}</title>
</head>
<body style="margin:0;overflow:hidden;background:{fondo};">
{fragmento}
</body>
</html>
"""


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

    nombre = str(datos.get("nombre") or nodo)
    lineas = _partir_texto(nombre, 14)[:4]
    creditos = datos.get("creditos")
    pie = f"{nodo}" if creditos is None else f"{nodo} · {int(creditos)} cr"

    texto_y = y + alto * 0.28
    for linea in lineas:
        eje.text(
            x,
            texto_y,
            linea,
            ha="center",
            va="center",
            fontsize=4.4,
            color=_COLOR_TEXTO,
            fontweight="bold",
            zorder=4,
            clip_on=True,
        )
        texto_y -= 0.13
    eje.text(
        x,
        y - alto * 0.34,
        pie,
        ha="center",
        va="center",
        fontsize=4.3,
        color=_COLOR_TEXTO,
        zorder=4,
        clip_on=True,
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
