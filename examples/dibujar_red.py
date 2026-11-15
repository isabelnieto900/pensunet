"""Genera la figura del DAG de análisis del pensum de Física."""

from pathlib import Path

from pensunet import SimuladorPensum
from pensunet.datos.fabrica import FabricaLectores
from pensunet.dominio.visualizacion import dibujar_red


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
    destino = raiz / "docs" / "figuras" / "red_prerrequisitos.png"
    dibujar_red(
        red,
        ruta=destino,
        titulo=(
            "Plan de estudios de Física · red de prerrequisitos "
            f"({red.grafo.number_of_nodes()} asignaturas, "
            f"{red.grafo.number_of_edges()} aristas)"
        ),
        mostrar_aristas=True,
    )
    print(f"Figura guardada en {destino}")
    print(f"Reglas aplicadas: {len(red.reglas_aplicadas)} notas")


if __name__ == "__main__":
    main()
