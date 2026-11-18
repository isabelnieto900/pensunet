"""Estado, caché y helpers compartidos por las páginas del dashboard."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import streamlit as st

from pensunet import SimuladorPensum
from pensunet.datos.adaptador_ud import AdaptadorUD
from pensunet.datos.privacidad import UMBRAL_MIN_INSCRITOS, suprimir_celdas_pequenas
from pensunet.datos.programas import PROGRAMAS
from pensunet.dominio.escenario import Escenario
from pensunet.dominio.indicadores import (
    UMBRAL_ENTRADA_CUELLO,
    UMBRAL_SALIDA_CUELLO,
    UMBRAL_TOTAL_CUELLO,
    IndicadoresTopologicos,
    camino_mas_largo,
)
from pensunet.dominio.visualizacion import colores_por_valor, html_de_la_red
from pensunet.ui.estilo import COLORES_CARRERA
from pensunet.ui.tablas import (
    tasa_media,
    tasas_por_asignatura,
)

N_SIM_RESUMEN = 2_000
N_SIM_CONTRASTE = 1_000
SEMILLA_BASE = 1
CLAVE_FACULTAD = "facultad"


def tope_semestres_por_plan(duracion_nominal: int) -> int:
    """1,5 × renovaciones de matrícula previstas en el plan (mínimo = N)."""
    n = max(1, int(duracion_nominal))
    return max(n, int(math.ceil(1.5 * n)))


def nivel() -> str:
    """Nivel de navegación: ``facultad`` o ``carrera``."""
    clave = st.session_state.get("selector_programa", CLAVE_FACULTAD)
    if clave in PROGRAMAS:
        return "carrera"
    return "facultad"


def clave_carrera() -> str | None:
    """Clave del programa, o ``None`` en el nivel Facultad."""
    clave = st.session_state.get("selector_programa", CLAVE_FACULTAD)
    if clave in PROGRAMAS:
        return str(clave)
    return None


def definir_selector(valor: str, *, ir_a_default: bool = True) -> None:
    """Agenda un cambio de selector para el próximo rerun (antes del widget)."""
    st.session_state["_pending_selector"] = valor
    if ir_a_default:
        st.session_state["_ir_a_default_nivel"] = True


def aplicar_selector_pendiente() -> None:
    """Aplica ``_pending_selector`` antes de dibujar el selectbox."""
    if "_pending_selector" in st.session_state:
        st.session_state.selector_programa = st.session_state.pop("_pending_selector")


def modo_oscuro() -> bool:
    if "modo_oscuro" in st.session_state:
        return bool(st.session_state.modo_oscuro)
    try:
        return str(st.context.theme.type).lower() == "dark"
    except Exception:
        return False


def _firma_codigo_sim() -> str:
    firmas = []
    for relativo in (
        "simulacion/montecarlo.py",
        "simulacion/estrategia.py",
        "dominio/escenario.py",
        "datos/ajustes.py",
    ):
        ruta = Path(__file__).resolve().parents[1] / relativo
        firmas.append(f"{relativo}:{ruta.stat().st_mtime_ns}")
    return "|".join(firmas)


@st.cache_resource(show_spinner="Cargando el pensum…")
def cargar_simulador(clave: str, _firma: str) -> SimuladorPensum:
    del _firma
    modelo = SimuladorPensum.desde_programa(clave)
    modelo.cargar(aplicar_ajustes_documentados=True)
    return modelo


def simulador_actual() -> SimuladorPensum:
    clave = clave_carrera()
    if clave is None:
        raise RuntimeError("No hay carrera seleccionada (nivel Facultad).")
    return cargar_simulador(clave, _firma_codigo_sim())


@st.cache_data(show_spinner=False)
def indicadores_cacheados(clave: str, nodos: int, aristas: int, _firma: str):
    del nodos, aristas
    return cargar_simulador(clave, _firma).indicadores()


@st.cache_data(show_spinner=False)
def complejidad_cacheada(clave: str, nodos: int, aristas: int, _firma: str):
    del nodos, aristas
    return cargar_simulador(clave, _firma).complejidad()


@st.cache_data(show_spinner="Simulando…")
def simular_base(
    clave: str,
    n_estudiantes: int,
    semilla: int,
    _firma: str,
) -> object:
    """Monte Carlo base de la carrera (tasas históricas / juicio experto)."""
    modelo = cargar_simulador(clave, _firma)
    escenario = Escenario(
        n_estudiantes=int(n_estudiantes),
        semilla=int(semilla),
    )
    return modelo.simular(escenario)


@st.cache_data(show_spinner="Recalculando escenario…")
def simular_con_tasa(
    clave: str,
    id_asignatura: int,
    tasa: float,
    n_estudiantes: int,
    semilla: int,
    _firma: str,
) -> object:
    modelo = cargar_simulador(clave, _firma)
    assert modelo.tasas is not None
    tasas = modelo.tasas.copy()
    mascara = tasas["id_asignatura"].astype(int) == int(id_asignatura)
    if mascara.any():
        tasas.loc[mascara, "tasa_aprobacion"] = float(tasa)
    else:
        tasas = pd.concat(
            [
                tasas,
                pd.DataFrame(
                    [
                        {
                            "id_asignatura": int(id_asignatura),
                            "nombre": "",
                            "n_inscritos": 0,
                            "n_aprobados": 0,
                            "tasa_aprobacion": float(tasa),
                            "n_bajo": True,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    escenario = Escenario(n_estudiantes=int(n_estudiantes), semilla=int(semilla))
    return modelo.simular(escenario, tasas=tasas)


@st.cache_data(show_spinner=False)
def tasas_agregadas(clave: str) -> pd.DataFrame:
    """Tasas CSV agregadas, ya con celdas pequeñas suprimidas."""
    ruta = PROGRAMAS[clave].ruta_tasas
    cruda = pd.read_csv(ruta)
    adaptada = AdaptadorUD().adaptar_tasas(cruda)
    return suprimir_celdas_pequenas(adaptada, umbral=UMBRAL_MIN_INSCRITOS)


@st.cache_data(show_spinner=False)
def pensum_agregado(clave: str) -> pd.DataFrame:
    return AdaptadorUD().adaptar_pensum(pd.read_csv(PROGRAMAS[clave].ruta_pensum))


def tasa_ponderada(tasas: pd.DataFrame) -> float | None:
    """Media de p_i ponderada por inscritos (solo filas con dato)."""
    if tasas.empty:
        return None
    validas = tasas.dropna(subset=["tasa_aprobacion", "n_inscritos"]).copy()
    if "sin_dato_suficiente" in validas.columns:
        validas = validas.loc[~validas["sin_dato_suficiente"]]
    if validas.empty:
        return None
    pesos = pd.to_numeric(validas["n_inscritos"], errors="coerce")
    valores = pd.to_numeric(validas["tasa_aprobacion"], errors="coerce")
    mascara = pesos.notna() & valores.notna() & (pesos > 0)
    if not mascara.any():
        return None
    return float((valores[mascara] * pesos[mascara]).sum() / pesos[mascara].sum())


def kpis_carrera(clave: str) -> dict[str, float | int | None]:
    """Indicadores del resumen para una carrera."""
    modelo = cargar_simulador(clave, _firma_codigo_sim())
    assert modelo.red is not None and modelo.programa is not None
    resultado = simular_base(clave, N_SIM_RESUMEN, SEMILLA_BASE, _firma_codigo_sim())
    nominal = int(modelo.red.duracion_nominal)
    tasas = tasas_agregadas(clave)
    criticidad = modelo.complejidad().complejidad_total
    return {
        "ex": float(resultado.media),
        "pct_nominal_mas_2": float(resultado.tasa_grado_en(nominal + 2)),
        "materias": int(modelo.red.grafo.number_of_nodes()),
        "creditos": int(modelo.programa.creditos_plan),
        "tasa_ponderada": tasa_ponderada(tasas),
        "nominal": nominal,
        "tope_semestres": tope_semestres_por_plan(nominal),
        "tiempos": resultado.tiempos,
        "color": COLORES_CARRERA[clave],
        "nombre": modelo.programa.nombre,
        "criticidad_total": int(criticidad),
        "clave": clave,
    }


def kpis_facultad() -> dict[str, float | int | None]:
    """Promedios / totales de las cuatro carreras FCMN."""
    filas = [kpis_carrera(clave) for clave in sorted(PROGRAMAS)]
    tasas = pd.concat(
        [tasas_agregadas(clave).assign(clave=clave) for clave in sorted(PROGRAMAS)],
        ignore_index=True,
    )
    return {
        "ex": float(sum(float(f["ex"]) for f in filas) / len(filas)),
        "pct_nominal_mas_2": float(
            sum(float(f["pct_nominal_mas_2"]) for f in filas) / len(filas)
        ),
        "materias": int(sum(int(f["materias"]) for f in filas)),
        "creditos": int(sum(int(f["creditos"]) for f in filas)),
        "tasa_ponderada": tasa_ponderada(tasas),
        "n_programas": len(filas),
    }


def motivo_cuello(entrada: int, salida: int) -> str | None:
    motivos: list[str] = []
    if entrada > UMBRAL_ENTRADA_CUELLO:
        motivos.append(f"grado de entrada {entrada} > {UMBRAL_ENTRADA_CUELLO}")
    if salida > UMBRAL_SALIDA_CUELLO:
        motivos.append(f"grado de salida {salida} > {UMBRAL_SALIDA_CUELLO}")
    if entrada + salida > UMBRAL_TOTAL_CUELLO:
        motivos.append(f"grado total {entrada + salida} > {UMBRAL_TOTAL_CUELLO}")
    return "; ".join(motivos) if motivos else None


def metricas_nodos(
    simulador: SimuladorPensum,
    indicadores: IndicadoresTopologicos,
) -> dict[int, dict]:
    assert simulador.red is not None
    complejidad = simulador.complejidad()
    metricas: dict[int, dict] = {}
    for nodo in simulador.red.grafo:
        codigo = int(nodo)
        entrada = int(simulador.red.grafo.in_degree(nodo))
        salida = int(simulador.red.grafo.out_degree(nodo))
        metricas[codigo] = {
            "tasa": simulador.tasa_de(codigo),
            "bloqueo": indicadores.factor_bloqueo.get(codigo),
            "posponimiento": indicadores.factor_posponimiento.get(codigo),
            "intermediacion": indicadores.intermediacion.get(codigo),
            "retraso": complejidad.retraso.get(codigo),
            "complejidad": complejidad.complejidad_estructural.get(codigo),
            "motivo_cuello": (
                motivo_cuello(entrada, salida)
                if codigo in indicadores.cuellos_de_botella
                else None
            ),
        }
    return metricas


@st.cache_data(show_spinner=False)
def html_red_cacheado(
    clave: str,
    nodos: int,
    aristas: int,
    oscuro: bool,
    cuellos: tuple[int, ...],
    camino: tuple[int, ...],
    con_metricas: bool,
    modo_color: str = "area",
    _firma: str = "",
) -> str:
    del nodos, aristas, _firma
    simulador = cargar_simulador(clave, _firma_codigo_sim())
    assert simulador.red is not None and simulador.programa is not None
    indicadores = simulador.indicadores()
    metricas = metricas_nodos(simulador, indicadores) if con_metricas else None
    colores = None
    if modo_color == "tasa" and simulador.tasas is not None:
        colores = colores_por_valor(
            tasas_por_asignatura(simulador.red, simulador.tasas),
            escala="tasa",
            minimo=0.0,
            maximo=1.0,
        )
    elif modo_color == "complejidad":
        colores = colores_por_valor(
            dict(simulador.complejidad().complejidad_estructural),
            escala="complejidad",
        )
    return html_de_la_red(
        simulador.red,
        titulo=f"Red de prerrequisitos · {simulador.programa.nombre}",
        embebido=True,
        oscuro=oscuro,
        resaltar=cuellos,
        camino=camino,
        metricas=metricas,
        colores=colores,
    )


def camino_actual(simulador: SimuladorPensum) -> tuple[int, ...]:
    assert simulador.red is not None
    return tuple(int(c) for c in camino_mas_largo(simulador.red))


def firma_sim() -> str:
    return _firma_codigo_sim()


@st.cache_data(show_spinner=False)
def top_menor_aprobacion_facultad(n: int = 15) -> pd.DataFrame:
    """Top n materias con menor aprobación en las 4 carreras (ya suprimidas)."""
    filas: list[dict] = []
    for clave in sorted(PROGRAMAS):
        tasas = tasas_agregadas(clave)
        validas = tasas.loc[~tasas["sin_dato_suficiente"]].dropna(
            subset=["tasa_aprobacion"]
        )
        for fila in validas.to_dict(orient="records"):
            filas.append(
                {
                    "carrera": PROGRAMAS[clave].nombre,
                    "clave": clave,
                    "id_asignatura": int(fila["id_asignatura"]),
                    "nombre": fila["nombre"],
                    "tasa_aprobacion": float(fila["tasa_aprobacion"]),
                    "n_inscritos": int(fila["n_inscritos"]),
                }
            )
    if not filas:
        return pd.DataFrame(
            columns=[
                "carrera",
                "clave",
                "id_asignatura",
                "nombre",
                "tasa_aprobacion",
                "n_inscritos",
            ]
        )
    tabla = pd.DataFrame(filas)
    return tabla.nsmallest(int(n), "tasa_aprobacion").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def materias_compartidas() -> pd.DataFrame:
    """Materias con el mismo ``id_asignatura`` en 2+ pensum (tasas suprimidas)."""
    por_id: dict[int, dict] = {}
    for clave in sorted(PROGRAMAS):
        pensum = pensum_agregado(clave)
        tasas = tasas_agregadas(clave)
        tasa_por_id = {
            int(f["id_asignatura"]): f for f in tasas.to_dict(orient="records")
        }
        for fila in pensum.to_dict(orient="records"):
            codigo = int(fila["id_asignatura"])
            entrada = por_id.setdefault(
                codigo,
                {
                    "id_asignatura": codigo,
                    "nombre": fila.get("nombre", ""),
                    "carreras": [],
                    "claves": [],
                    "tasas": [],
                    "inscritos": [],
                },
            )
            entrada["carreras"].append(PROGRAMAS[clave].nombre)
            entrada["claves"].append(clave)
            tasa_fila = tasa_por_id.get(codigo)
            if tasa_fila is None or tasa_fila.get("sin_dato_suficiente"):
                entrada["tasas"].append(None)
                entrada["inscritos"].append(
                    int(tasa_fila["n_inscritos"]) if tasa_fila is not None else None
                )
            else:
                entrada["tasas"].append(float(tasa_fila["tasa_aprobacion"]))
                entrada["inscritos"].append(int(tasa_fila["n_inscritos"]))
            if not entrada["nombre"] and fila.get("nombre"):
                entrada["nombre"] = fila["nombre"]

    filas = []
    for codigo, datos in sorted(por_id.items()):
        if len(datos["carreras"]) < 2:
            continue
        tasas_ok = [t for t in datos["tasas"] if t is not None]
        inscritos_ok = [n for n in datos["inscritos"] if n is not None]
        if tasas_ok and inscritos_ok and sum(inscritos_ok) > 0:
            tasa_agregada = sum(
                t * n
                for t, n in zip(datos["tasas"], datos["inscritos"], strict=False)
                if t is not None and n is not None
            ) / sum(inscritos_ok)
            if sum(inscritos_ok) < UMBRAL_MIN_INSCRITOS:
                tasa_agregada = None
        else:
            tasa_agregada = None
        filas.append(
            {
                "id_asignatura": codigo,
                "nombre": datos["nombre"],
                "carreras": ", ".join(datos["carreras"]),
                "n_carreras": len(datos["carreras"]),
                "tasa_agregada": tasa_agregada,
                "n_inscritos": sum(inscritos_ok) if inscritos_ok else 0,
            }
        )
    return pd.DataFrame(filas).sort_values(
        ["n_carreras", "id_asignatura"],
        ascending=[False, True],
    ).reset_index(drop=True)


# Reexportes útiles en páginas
__all__ = [
    "CLAVE_FACULTAD",
    "N_SIM_CONTRASTE",
    "N_SIM_RESUMEN",
    "SEMILLA_BASE",
    "aplicar_selector_pendiente",
    "cargar_simulador",
    "camino_actual",
    "clave_carrera",
    "complejidad_cacheada",
    "definir_selector",
    "firma_sim",
    "html_red_cacheado",
    "indicadores_cacheados",
    "kpis_carrera",
    "kpis_facultad",
    "materias_compartidas",
    "metricas_nodos",
    "modo_oscuro",
    "nivel",
    "pensum_agregado",
    "simular_base",
    "simular_con_tasa",
    "simulador_actual",
    "tasa_media",
    "tasa_ponderada",
    "tasas_agregadas",
    "tope_semestres_por_plan",
    "top_menor_aprobacion_facultad",
]
