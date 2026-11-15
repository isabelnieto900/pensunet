"""Genera la figura PNG y la vista HTML interactiva de la red."""

from pathlib import Path

from pensunet import SimuladorPensum
from pensunet.datos.fabrica import FabricaLectores
from pensunet.dominio.visualizacion import dibujar_red, exportar_red_html


def main() -> None:
    raiz = Path(__file__).resolve().parents[1]
    lector = FabricaLectores.crear(
        "csv",
        ruta_pensum=raiz / "data/reference/pensum_fisica.csv",
        ruta_prerequisitos=raiz / "data/reference/prerequisitos_fisica.csv",
        ruta_tasas=raiz / "data/processed/tasas_aprobacion_fisica.csv",
    )
    simulador = SimuladorPensum(lector)
    red = simulador.cargar(aplicar_reglas=True)
    titulo = (
        "Plan de estudios de Física · red de prerrequisitos "
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
    main()
