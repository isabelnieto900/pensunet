"""Carga un pensum FCMN e imprime un resumen de la red.

Construye el DAG
y muestra bloqueo, posponimiento e intermediación. No simula.

Uso::

    python examples/ejemplo_cargar_red.py
    python examples/ejemplo_cargar_red.py --programa quimica
    python examples/ejemplo_cargar_red.py --programa biologia --sin-ajustes
"""

from __future__ import annotations

import argparse

from pensunet.datos.creditos import sumar_creditos_plan
from pensunet.datos.programas import PROGRAMAS
from pensunet.facade import SimuladorPensum


def main() -> None:
    """Carga los CSV de data/ y escribe el resumen por salida estándar."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--programa",
        default="fisica",
        choices=sorted(PROGRAMAS),
        help="Carrera FCMN a cargar (default: fisica).",
    )
    parser.add_argument(
        "--sin-ajustes",
        action="store_true",
        help="Conserva el extracto crudo del SGA sin ajustes_prerrequisitos.csv.",
    )
    args = parser.parse_args()

    simulador = SimuladorPensum.desde_programa(args.programa)
    red = simulador.cargar(aplicar_ajustes_documentados=not args.sin_ajustes)
    indicadores = simulador.indicadores()
    assert simulador.pensum is not None
    nombres = dict(
        zip(simulador.pensum["id_asignatura"], simulador.pensum["nombre"], strict=True)
    )
    creditos = sumar_creditos_plan(simulador.pensum, programa=args.programa)
    programa = simulador.programa
    assert programa is not None

    print(f"Programa: {programa.nombre} (plan {programa.id_plan})")
    print(f"Asignaturas: {red.grafo.number_of_nodes()}")
    print(f"Prerrequisitos estrictos: {red.grafo.number_of_edges()}")
    print(f"Créditos del plan (cupos una vez): {creditos}")
    print(f"Es un DAG: {red.es_aciclico()}")
    print(f"Duración nominal: {red.duracion_nominal} semestres")
    print(f"Inconsistencias registradas: {len(red.inconsistencias)}")
    for texto in red.inconsistencias:
        print(f"  - {texto}")
    if simulador.ajustes_aplicados:
        print(f"Ajustes documentados: {len(simulador.ajustes_aplicados)}")
        for texto in simulador.ajustes_aplicados:
            print(f"  - {texto}")

    print("Mayor factor de bloqueo:")
    ordenados = sorted(indicadores.factor_bloqueo.items(), key=lambda par: par[1], reverse=True)
    for identificador, bloqueo in ordenados[:5]:
        print(f"  {identificador} {nombres[identificador]}: {bloqueo}")


if __name__ == "__main__":
    main()
