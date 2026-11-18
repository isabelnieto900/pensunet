"""Tablas listas para la interfaz a partir de la fachada."""

from __future__ import annotations

import pandas as pd

from pensunet.dominio.complejidad import ComplejidadCurricular
from pensunet.dominio.indicadores import IndicadoresTopologicos
from pensunet.dominio.red import RedPrerrequisitos
from pensunet.simulacion.estrategia import ResultadoSimulacion


def tabla_resumen_red(red: RedPrerrequisitos) -> dict[str, int | float]:
    """Números que encabezan el panel de la red."""
    return {
        "asignaturas": red.grafo.number_of_nodes(),
        "aristas": red.grafo.number_of_edges(),
        "duracion_nominal": red.duracion_nominal,
        "reglas_aplicadas": len(red.reglas_aplicadas),
    }


def tabla_indicadores(
    red: RedPrerrequisitos,
    indicadores: IndicadoresTopologicos,
    complejidad: ComplejidadCurricular | None = None,
) -> pd.DataFrame:
    """Una fila por asignatura con bloqueo, posponimiento e intermediación.

    Con ``complejidad`` se añaden ``retraso`` y ``complejidad`` (Curricular
    Analytics, Heileman et al., 2018).
    """
    filas: list[dict] = []
    for nodo, datos in red.grafo.nodes(data=True):
        codigo = int(nodo)
        filas.append(
            {
                "id": codigo,
                "nombre": datos.get("nombre", ""),
                "semestre": datos.get("semestre"),
                "clasificacion": datos.get("clasificacion"),
                "bloqueo": indicadores.factor_bloqueo.get(codigo, 0),
                "posponimiento": indicadores.factor_posponimiento.get(codigo),
                "intermediacion": indicadores.intermediacion.get(codigo),
                "cuello_de_botella": codigo in indicadores.cuellos_de_botella,
            }
        )
        if complejidad is not None:
            filas[-1]["retraso"] = complejidad.retraso.get(codigo)
            filas[-1]["complejidad"] = complejidad.complejidad_estructural.get(codigo)
    tabla = pd.DataFrame(filas)
    return tabla.sort_values(
        by=["bloqueo", "intermediacion", "id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def tabla_tiempos(resultado: ResultadoSimulacion) -> pd.DataFrame:
    """Frecuencias de X para el histograma."""
    serie = pd.Series(resultado.tiempos, name="semestres")
    conteo = serie.value_counts().sort_index()
    return pd.DataFrame(
        {
            "semestres": conteo.index.astype(int),
            "estudiantes": conteo.to_numpy(),
            "proporcion": conteo.to_numpy() / len(resultado.tiempos),
        }
    )


def tabla_tasas_del_grafo(
    red: RedPrerrequisitos,
    tasas: pd.DataFrame,
) -> pd.DataFrame:
    """Tasas de las asignaturas del grafo, listas para editar en la UI."""
    ids = {int(nodo) for nodo in red.grafo.nodes}
    filas: list[dict] = []
    por_id = {
        int(fila["id_asignatura"]): fila
        for fila in tasas.to_dict(orient="records")
    }
    for codigo in sorted(ids):
        datos = red.grafo.nodes[codigo]
        fila = por_id.get(codigo)
        filas.append(
            {
                "id": codigo,
                "nombre": datos.get("nombre", ""),
                "semestre": datos.get("semestre"),
                "tasa_aprobacion": (
                    float(fila["tasa_aprobacion"]) if fila is not None else None
                ),
            }
        )
    return pd.DataFrame(filas)


def tasas_desde_editor(
    tasas_base: pd.DataFrame,
    editadas: pd.DataFrame,
) -> pd.DataFrame:
    """Copia ``tasas_base`` sustituyendo p_i con las del editor."""
    resultado = tasas_base.copy()
    for fila in editadas.to_dict(orient="records"):
        codigo = int(fila["id"])
        valor = fila.get("tasa_aprobacion")
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            continue
        probabilidad = float(valor)
        if not 0.0 <= probabilidad <= 1.0:
            raise ValueError(
                f"La tasa de {codigo} debe estar en [0, 1]; se recibió {probabilidad}."
            )
        mascara = resultado["id_asignatura"] == codigo
        if mascara.any():
            resultado.loc[mascara, "tasa_aprobacion"] = probabilidad
        else:
            resultado = pd.concat(
                [
                    resultado,
                    pd.DataFrame(
                        [
                            {
                                "id_asignatura": codigo,
                                "nombre": fila.get("nombre", ""),
                                "n_inscritos": 0,
                                "n_aprobados": 0,
                                "tasa_aprobacion": probabilidad,
                                "n_bajo": True,
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )
    return resultado.reset_index(drop=True)


def tasa_media(red: RedPrerrequisitos, tasas: pd.DataFrame) -> float | None:
    """Promedio simple de p_i sobre las asignaturas del grafo que tienen tasa.

    Las asignaturas sin histórico (p. ej. Trabajo de Grado) no entran: no
    se completan con 0 ni con 1. Devuelve None si ninguna tiene tasa.
    """
    nodos = {int(n) for n in red.grafo}
    filas = tasas.loc[tasas["id_asignatura"].astype(int).isin(nodos), "tasa_aprobacion"]
    filas = pd.to_numeric(filas, errors="coerce").dropna()
    if filas.empty:
        return None
    return float(filas.mean())


def tasas_por_asignatura(red: RedPrerrequisitos, tasas: pd.DataFrame) -> dict[int, float | None]:
    """p_i de cada nodo del grafo, o None si no hay histórico."""
    mapa = {
        int(fila["id_asignatura"]): fila["tasa_aprobacion"]
        for fila in tasas.to_dict(orient="records")
    }
    resultado: dict[int, float | None] = {}
    for nodo in red.grafo:
        valor = mapa.get(int(nodo))
        if valor is None or pd.isna(valor):
            resultado[int(nodo)] = None
        else:
            resultado[int(nodo)] = float(valor)
    return resultado
