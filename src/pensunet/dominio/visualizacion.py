"""Figura del pensum y vista HTML interactiva de la red.

La disposición imita el PDF del plan (columnas por semestre y cajas por
área). Las aristas del DAG de prerrequisitos se
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

# Paleta identidad web Universidad Distrital (sin escudo ni logo).
_COLOR_BASICAS = "#8C1919"
_COLOR_PROFESION = "#1291C0"
_COLOR_TRANSVERSAL = "#00A859"
_COLOR_LINEA = "#373435"
_COLOR_TEXTO = "#FFFFFF"
_COLOR_BORDE = "#373435"
_COLOR_ARISTA = "#5C5657"
_COLOR_FONDO = "#F7F3EE"
_COLOR_FONDO_SEC = "#EFE9E2"
_COLOR_ENCABEZADO = "#000000"
_COLOR_CAMINO = "#8C1919"
_COLOR_CUELLO = "#FDB400"
_COLOR_DORADO = "#FDB400"
_ALTURA_EMBEBIDO_PX = 820
_ALTURA_PANEL_ARRIBA_PX = 118
_ESCALA_SVG = 78.0
_MARGEN_SVG = 36.0
_STATIC_DIR = Path(__file__).resolve().parents[1] / "ui" / "static"
# Lavados de columna (mismo set UD; se ciclan por semestre).
_COLORES_COLUMNA = (
    "#8C1919",
    "#FDB400",
    "#1291C0",
    "#00A859",
)

# Cajas por semestre; más aire horizontal para leer las flechas.
_ANCHO_CAJA = 1.28
_ALTO_CAJA = 0.96
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
    destino.write_text(
        html_de_la_red(red, titulo=titulo, embebido=False),
        encoding="utf-8",
    )
    return destino


def payload_de_la_red(
    red: RedPrerrequisitos,
    *,
    metricas: dict[int, dict] | None = None,
    colores: dict[int, str] | None = None,
    resaltar: frozenset[int] | None = None,
    camino: tuple[int, ...] | None = None,
) -> dict:
    """Construye el JSON serializable que alimenta el visualizador D3.

    Las posiciones reutilizan ``_posiciones_cajas`` / ``_agrupar_por_semestre``
    (columnas fijas por semestre). No incluye microdatos de estudiantes.
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

    semestres = [
        {
            "id": int(semestre),
            "etiqueta": _ROMANOS.get(int(semestre), str(semestre)),
            "x": float(_x_columna(int(semestre))),
            "color": _COLORES_COLUMNA[(int(semestre) - 1) % len(_COLORES_COLUMNA)],
        }
        for semestre in por_semestre
    ]

    nodos_payload: list[dict] = []
    for nodo, (x, y, _ancho, _alto) in cajas.items():
        datos = grafo.nodes[nodo]
        codigo = int(nodo)
        extra = datos_extra.get(codigo, {})
        creditos = datos.get("creditos")
        nodos_payload.append(
            {
                "id": codigo,
                "nombre": str(datos.get("nombre") or codigo),
                "creditos": None if creditos is None else int(creditos),
                "semestre": int(datos.get("semestre") or 0),
                "clasificacion": str(datos.get("clasificacion") or ""),
                "x": float(x),
                "y": float(y),
                "color": (colores or {}).get(codigo) or _color_area(datos),
                "tasa": extra.get("tasa"),
                "bloqueo": extra.get("bloqueo"),
                "retraso": extra.get("retraso"),
                "complejidad": extra.get("complejidad"),
                "posponimiento": extra.get("posponimiento"),
                "intermediacion": extra.get("intermediacion"),
                "motivo_cuello": extra.get("motivo_cuello"),
                "cuello": codigo in destacados,
                "camino": codigo in ids_camino,
                "ancestros": sorted(int(a) for a in nx.ancestors(grafo, nodo)),
                "descendientes": sorted(int(d) for d in nx.descendants(grafo, nodo)),
                "previos": [int(p) for p in grafo.predecessors(nodo)],
                "siguientes": [int(s) for s in grafo.successors(nodo)],
            }
        )

    aristas_payload: list[dict] = []
    for origen, destino, attrs in grafo.edges(data=True):
        if origen not in cajas or destino not in cajas:
            continue
        estricto = bool(attrs.get("debe_aprobado", True))
        aristas_payload.append(
            {
                "source": int(origen),
                "target": int(destino),
                "tipo": "estricto" if estricto else "debil",
                "en_camino": (int(origen), int(destino)) in aristas_camino,
            }
        )

    svg_ancho = _MARGEN_SVG * 2 + (_x_columna(10) + _ANCHO_CAJA / 2) * _ESCALA_SVG
    svg_alto = (
        _MARGEN_SVG * 2
        + (_y_superior(max_filas) - _y_inferior(max_filas) + 2.2) * _ESCALA_SVG
    )
    return {
        "meta": {
            "ancho_caja": _ANCHO_CAJA,
            "alto_caja": _ALTO_CAJA,
            "escala": _ESCALA_SVG,
            "margen": _MARGEN_SVG,
            "svg_ancho": svg_ancho,
            "svg_alto": svg_alto,
            "max_filas": max_filas,
            "y_superior": _y_superior(max_filas),
            "gap_x": _GAP_X,
            "colores": {
                "arista": _COLOR_ARISTA,
                "camino": _COLOR_CAMINO,
                "cuello": _COLOR_CUELLO,
                "halo": "rgba(92, 86, 87, 0.2)",
                "texto_ui": _COLOR_ENCABEZADO,
                "fondo": _COLOR_FONDO,
                "columnas": list(_COLORES_COLUMNA),
            },
        },
        "semestres": semestres,
        "nodos": nodos_payload,
        "aristas": aristas_payload,
    }


def _leer_static(nombre: str) -> str:
    """Lee un asset del visualizador embebido junto al paquete."""
    return (_STATIC_DIR / nombre).read_text(encoding="utf-8")


def html_de_la_red(
    red: RedPrerrequisitos,
    titulo: str = "Plan de estudios · red de prerrequisitos",
    *,
    embebido: bool = False,
    oscuro: bool = False,
    resaltar: frozenset[int] | set[int] | tuple[int, ...] | None = None,
    camino: frozenset[int] | set[int] | tuple[int, ...] | None = None,
    metricas: dict[int, dict[str, float | int | str | None]] | None = None,
    colores: dict[int, str] | None = None,
) -> str:
    """Devuelve el HTML interactivo de la red (D3 v7 por CDN).

    Con ``embebido=True`` omite el título de página y activa zoom/pan.
    ``oscuro`` fija colores legibles dentro del iframe.
    ``resaltar`` marca cuellos de botella; ``camino`` el camino más largo.
    ``metricas`` aporta tasa, bloqueo, etc. al panel y al tooltip.
    ``colores`` reemplaza el color de área (ver ``colores_por_valor``).

    Siempre es un documento completo: ``st.iframe`` lo necesita;
    ``st.html`` sanitiza SVG/JS y deja la red en blanco.
    """
    destacados = frozenset(int(x) for x in (resaltar or ()))
    en_camino = tuple(int(x) for x in (camino or ()))
    payload = payload_de_la_red(
        red,
        metricas=metricas,
        colores=colores,
        resaltar=destacados,
        camino=en_camino,
    )
    if oscuro and embebido:
        fondo = "#1A1A1A"
        color_texto = "#FFFFFF"
        color_detalle_bg = "#242424"
        color_detalle_borde = "#373435"
        color_scheme = "dark"
        payload["meta"]["colores"]["texto_ui"] = color_texto
        payload["meta"]["colores"]["fondo"] = fondo
        payload["meta"]["colores"]["halo"] = "rgba(255, 255, 255, 0.2)"
        payload["meta"]["columna_alpha"] = 0.16
    elif embebido:
        fondo = _COLOR_FONDO
        color_texto = _COLOR_ENCABEZADO
        color_detalle_bg = _COLOR_FONDO_SEC
        color_detalle_borde = "#C9BFB4"
        color_scheme = "light"
        payload["meta"]["columna_alpha"] = 0.12
    else:
        fondo = _COLOR_FONDO
        color_texto = _COLOR_ENCABEZADO
        color_detalle_bg = _COLOR_FONDO
        color_detalle_borde = "#C9BFB4"
        color_scheme = "light"
        payload["meta"]["columna_alpha"] = 0.12

    svg_ancho = payload["meta"]["svg_ancho"]
    svg_alto = payload["meta"]["svg_alto"]
    titulo_html = "" if embebido else f"<h1>{html.escape(titulo)}</h1>"
    zoom_bar = ""
    if embebido:
        zoom_bar = """
    <div class="zoom-flotante">
      <button type="button" id="z-out" title="Alejar">−</button>
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
    altura_vista = (
        _ALTURA_EMBEBIDO_PX - _ALTURA_PANEL_ARRIBA_PX if embebido else _ALTURA_EMBEBIDO_PX
    )
    altura_cuerpo = f"{_ALTURA_EMBEBIDO_PX}px" if embebido else "auto"
    svg_attrs = (
        f'width="100%" height="{altura_vista}" '
        f'viewBox="0 0 {svg_ancho:.0f} {svg_alto:.0f}" '
        f'preserveAspectRatio="xMidYMid meet"'
        if embebido
        else (
            f'width="{svg_ancho:.0f}" height="{svg_alto:.0f}" '
            f'viewBox="0 0 {svg_ancho:.0f} {svg_alto:.0f}"'
        )
    )

    leyenda_extra = ""
    if destacados:
        leyenda_extra += (
            '<span><i class="swatch cuello-swatch"></i> Cuello de botella</span>'
        )
    if en_camino:
        leyenda_extra += (
            '<span><i class="swatch camino-swatch"></i> Camino más largo</span>'
        )

    tema_extra = f"""
.pensunet-red {{
  background: {fondo};
  color: {color_texto};
  color-scheme: {color_scheme};
}}
.pensunet-red .cuerpo {{
  height: {altura_cuerpo};
  padding: {"0" if embebido else "0.5rem"};
}}
.pensunet-red .vista {{ background: {fondo}; }}
.pensunet-red .panel-arriba {{
  background: {color_detalle_bg};
  color: {color_texto};
  border-bottom-color: {color_detalle_borde};
  max-height: {_ALTURA_PANEL_ARRIBA_PX}px;
}}
.pensunet-red .panel-arriba .dato {{ border-left-color: {color_detalle_borde}; }}
.pensunet-red .zoom-flotante {{
  background: {color_detalle_bg};
  border: 1px solid {color_detalle_borde};
}}
.pensunet-red .zoom-flotante button {{ border-color: {color_detalle_borde}; }}
.pensunet-red svg {{ background: {fondo}; }}
.pensunet-red .tooltip {{
  background: {color_detalle_bg};
  color: {color_texto};
  border-color: {color_detalle_borde};
}}
.pensunet-red .leyenda {{ color: {color_texto}; }}
"""
    css = _leer_static("red_curricular.css") + tema_extra
    js = _leer_static("red_curricular.js")
    payload_json = json.dumps(payload, ensure_ascii=False)
    payload_attr = html.escape(payload_json, quote=True)

    fills_semilla = "".join(
        f'<rect data-id="{n["id"]}" fill="{html.escape(str(n["color"]))}" '
        f'width="0" height="0" opacity="0"/>'
        for n in payload["nodos"]
    )

    cuerpo = f"""
  {titulo_html}
  <div class="cuerpo">
    <aside class="panel-arriba">
      <h2>Materia seleccionada</h2>
      <div id="detalle" class="detalle-grid">Pasa el cursor sobre una materia para
        ver la cadena; haz clic para fijar el detalle aquí arriba.</div>
    </aside>
    <div class="vista">
      {zoom_bar}
      <div class="lienzo" id="viewport">
        <svg id="red" {svg_attrs}>
          <g id="semilla-fills" aria-hidden="true">{fills_semilla}</g>
        </svg>
        <div class="tooltip" id="tooltip" role="tooltip"></div>
      </div>
      <div class="leyenda">
        <span><i class="swatch linea"></i> Prerrequisito estricto</span>
        <span><i class="swatch linea debil"></i> Prerrequisito débil</span>
        <span><i class="swatch linea cadena"></i> Cadena al pasar el cursor</span>
        <span><i class="swatch" style="background:{_COLOR_BASICAS}"></i> Básicas</span>
        <span><i class="swatch" style="background:{_COLOR_PROFESION}"></i> Profesión</span>
        <span><i class="swatch" style="background:{_COLOR_TRANSVERSAL}"></i> Transversal</span>
        <span><i class="swatch" style="background:{_COLOR_LINEA}"></i> Línea / grado</span>
        {leyenda_extra}
      </div>
    </div>
  </div>
"""
    fragmento = (
        f'<div class="{clase_raiz}" data-payload="{payload_attr}">\n'
        f"<style>{css}</style>\n"
        f"{cuerpo}\n"
        f'<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>\n'
        f"<script>\n{js}\n</script>\n"
        f"</div>"
    )
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="color-scheme" content="{color_scheme}"/>
  <title>{html.escape(titulo)}</title>
</head>
<body style="margin:0;background:{fondo};">
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


# Escalas de color para las cajas (texto blanco legible en todos los tonos).
ESCALAS_COLOR: dict[str, tuple[str, ...]] = {
    # Tasa baja (rojo) → media (ámbar oscuro) → alta (verde).
    "tasa": ("#A93226", "#B9770E", "#1E8449"),
    # Complejidad baja (azul grisáceo) → alta (azul noche).
    "complejidad": ("#7FA1B8", "#2E5E82", "#0B2545"),
}
COLOR_SIN_DATO = "#7F8C8D"


def colores_por_valor(
    valores: dict[int, float | int | None],
    escala: str = "tasa",
    minimo: float | None = None,
    maximo: float | None = None,
) -> dict[int, str]:
    """Asigna a cada asignatura un color interpolado según su valor.

    ``escala`` es una clave de ``ESCALAS_COLOR``. Los valores ``None`` o
    NaN reciben ``COLOR_SIN_DATO`` (gris), para que una tasa faltante no
    se confunda con una tasa baja. Por defecto el rango es el mínimo y el
    máximo observados; para tasas conviene fijar ``minimo=0, maximo=1``.
    """
    if escala not in ESCALAS_COLOR:
        raise KeyError(f"Escala {escala!r} desconocida. Opciones: {sorted(ESCALAS_COLOR)}.")
    paradas = [_hex_a_rgb(c) for c in ESCALAS_COLOR[escala]]
    validos = [
        float(v) for v in valores.values() if v is not None and float(v) == float(v)
    ]
    lo = minimo if minimo is not None else (min(validos) if validos else 0.0)
    hi = maximo if maximo is not None else (max(validos) if validos else 1.0)
    resultado: dict[int, str] = {}
    for codigo, valor in valores.items():
        if valor is None or float(valor) != float(valor):
            resultado[int(codigo)] = COLOR_SIN_DATO
            continue
        t = 0.0 if hi <= lo else (float(valor) - lo) / (hi - lo)
        resultado[int(codigo)] = _interpolar(paradas, min(1.0, max(0.0, t)))
    return resultado


def _hex_a_rgb(color: str) -> tuple[int, int, int]:
    limpio = color.lstrip("#")
    return int(limpio[0:2], 16), int(limpio[2:4], 16), int(limpio[4:6], 16)


def _interpolar(paradas: list[tuple[int, int, int]], t: float) -> str:
    tramos = len(paradas) - 1
    posicion = t * tramos
    i = min(int(posicion), tramos - 1)
    local = posicion - i
    a, b = paradas[i], paradas[i + 1]
    r, g, bl = (round(a[k] + (b[k] - a[k]) * local) for k in range(3))
    return f"#{r:02X}{g:02X}{bl:02X}"


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
