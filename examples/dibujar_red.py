"""Genera la figura PNG y la vista HTML interactiva de la red."""

import sys
from pathlib import Path

from pensunet import SimuladorPensum
from pensunet.dominio.visualizacion import dibujar_red, exportar_red_html


def main(clave: str = "fisica") -> None:
    raiz = Path(__file__).resolve().parents[1]
    simulador = SimuladorPensum.desde_programa(clave)
    red = simulador.cargar()
    titulo = (
        f"Plan de estudios de {simulador.programa.nombre} · red de prerrequisitos "
        f"({red.grafo.number_of_nodes()} asignaturas, "
        f"{red.grafo.number_of_edges()} aristas)"
    )
    png = raiz / "docs" / "figuras" / "red_prerrequisitos.png"
    html_ruta = raiz / "docs" / "figuras" / "red_prerrequisitos.html"
    dibujar_red(red, ruta=png, titulo=titulo, mostrar_aristas=True)
    exportar_red_html(red, ruta=html_ruta, titulo=titulo)
    print(f"Figura PNG: {png}")
    print(f"Vista HTML: {html_ruta}")
    print(f"Reglas aplicadas: {len(red.reglas_aplicadas)} notas")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fisica")
