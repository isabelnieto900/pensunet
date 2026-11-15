"""Carga el pensum de Física e imprime un resumen de la red.

Sección II.A y sección II.B de Molontay et al. (2020): construye el DAG
y muestra bloqueo, posponimiento e intermediación. No simula.
"""

from pathlib import Path

from pensunet.datos.fabrica import FabricaLectores
from pensunet.facade import SimuladorPensum

RAIZ = Path(__file__).resolve().parents[1]


def main() -> None:
    """Carga los CSV de data/ y escribe el resumen por salida estándar."""
    lector = FabricaLectores.crear(
        "csv",
        ruta_pensum=RAIZ / "data" / "reference" / "pensum_fisica.csv",
        ruta_prerequisitos=RAIZ / "data" / "reference" / "prerequisitos_fisica.csv",
        ruta_tasas=RAIZ / "data" / "processed" / "tasas_aprobacion_fisica.csv",
    )
    simulador = SimuladorPensum(lector)
    red = simulador.cargar()
    indicadores = simulador.indicadores()
    nombres = dict(zip(simulador.pensum["id_asignatura"], simulador.pensum["nombre"], strict=True))

    print(f"Asignaturas: {red.grafo.number_of_nodes()}")
    print(f"Prerrequisitos estrictos: {red.grafo.number_of_edges()}")
    print(f"Es un DAG: {red.es_aciclico()}")
    print(f"Duración nominal: {red.duracion_nominal} semestres")
    print(f"Inconsistencias registradas: {len(red.inconsistencias)}")
    for texto in red.inconsistencias:
        print(f"  - {texto}")

    print("Mayor factor de bloqueo (sección II.B):")
    ordenados = sorted(indicadores.factor_bloqueo.items(), key=lambda par: par[1], reverse=True)
    for identificador, bloqueo in ordenados[:5]:
        print(f"  {identificador} {nombres[identificador]}: {bloqueo}")


if __name__ == "__main__":
    main()
