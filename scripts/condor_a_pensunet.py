#!/usr/bin/env python3
"""Convierte el extracto de Cóndor (OATI) al esquema de AdaptadorUD.

No aplica correcciones del SGA: esas viven en
``data/reference/ajustes_prerrequisitos.csv`` y se aplican en código al cargar.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
OATI_CONDOR = Path.home() / "code" / "OATI" / "data" / "reference" / "condor"
OATI_TASAS = Path.home() / "code" / "OATI" / "data" / "curated" / "tasas"

PROGRAMAS = {
    "fisica": ("fisica_327", 327),
    "quimica": ("quimica_328", 328),
    "biologia": ("biologia_329", 329),
    "matematicas": ("matematicas_298", 298),
}

COLUMNAS_PENSUM = [
    "nu_periodo_formacion",
    "id_asignatura",
    "ds_nombre_asignatura",
    "ds_nombre_pensum",
    "nu_creditos",
    "ds_clasificacion",
    "ds_grupo_slot",
    "ds_linea_tematica",
    "ds_bloque_electivo",
]

TG = {
    "fisica": ((25149, "Trabajo de Grado I"), (25154, "Trabajo de Grado II")),
    "quimica": ((25149, "Trabajo de Grado I"), (25242, "Trabajo de Grado II")),
    "biologia": ((22540, "Trabajo de Grado I"), (25345, "Trabajo de Grado II")),
    "matematicas": ((19924, "Trabajo de Grado I"), (19925, "Trabajo de Grado II")),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--condor",
        type=Path,
        default=OATI_CONDOR,
        help="Directorio con subcarpetas <programa>_<plan>/",
    )
    parser.add_argument(
        "--tasas",
        type=Path,
        default=OATI_TASAS,
        help="Directorio con tasas_aprobacion_<programa>.csv",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=RAIZ / "data",
        help="Raíz data/ de Pensunet",
    )
    parser.add_argument(
        "--programas",
        nargs="+",
        default=list(PROGRAMAS),
        choices=list(PROGRAMAS),
    )
    args = parser.parse_args()

    lineas = _lineas_fisica_actuales(args.salida / "reference" / "pensum_fisica.csv")
    cupos_vacios: list[dict] = []
    filas_tg: list[dict] = []

    for clave in args.programas:
        carpeta, id_plan = PROGRAMAS[clave]
        origen = args.condor / carpeta
        pensum, cupos = convertir_pensum(
            origen / "pensum.csv",
            lineas_tematicas=lineas if clave == "fisica" else {},
        )
        for cupo in cupos:
            cupo["programa"] = clave
            cupos_vacios.append(cupo)
        prerreq = convertir_prerrequisitos(origen / "prerrequisitos.csv")
        tasas_origen = args.tasas / f"tasas_aprobacion_{clave}.csv"
        tasas_destino = args.salida / "processed" / f"tasas_aprobacion_{clave}.csv"
        tasas_destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tasas_origen, tasas_destino)

        pensum_path = args.salida / "reference" / f"pensum_{clave}.csv"
        prerreq_path = args.salida / "reference" / f"prerequisitos_{clave}.csv"
        pensum_path.parent.mkdir(parents=True, exist_ok=True)
        pensum.to_csv(pensum_path, index=False, encoding="utf-8")
        prerreq.to_csv(prerreq_path, index=False, encoding="utf-8")

        for codigo, nombre in TG[clave]:
            filas_tg.append(
                {
                    "programa": clave,
                    "id_plan": id_plan,
                    "id_asignatura": codigo,
                    "ds_nombre_asignatura": nombre,
                    "tasa_aprobacion": "",
                    "origen": "juicio_experto",
                    "justificacion": (
                        "La nota de TG no está en fact_rendimiento_academico "
                        "(todas 0 / ningún aprobado en 2023-2 a 2025-2). "
                        "No se usa 0 ni 1 por defecto; la tasa queda vacía "
                        "hasta otra fuente (actas / historia académica)."
                    ),
                }
            )
        print(
            f"{clave}: pensum={len(pensum)} prerreq={len(prerreq)} "
            f"tasas={len(pd.read_csv(tasas_destino))} cupos_vacios={len(cupos)}"
        )

    pd.DataFrame(cupos_vacios).to_csv(
        args.salida / "reference" / "cupos_sin_asignatura.csv",
        index=False,
        encoding="utf-8",
    )
    pd.DataFrame(filas_tg).to_csv(
        args.salida / "reference" / "trabajo_de_grado.csv",
        index=False,
        encoding="utf-8",
    )
    print("Listo.")


def convertir_pensum(
    ruta: Path,
    lineas_tematicas: dict[int, str] | None = None,
) -> tuple[pd.DataFrame, list[dict]]:
    """Mapea el pensum de Cóndor; descarta cupos sin id_asignatura."""
    crudo = pd.read_csv(ruta, encoding="utf-8")
    cupos_vacios: list[dict] = []
    for fila in crudo.to_dict(orient="records"):
        if not bool(fila.get("es_slot")):
            continue
        if _tiene_id(fila.get("id_asignatura")):
            continue
        # Cupo del plan sin opciones con código: sigue contando créditos.
        opciones = crudo.loc[
            (crudo["periodo"] == fila["periodo"])
            & (crudo["slot"].astype(str) == str(fila["nombre"]))
            & crudo["id_asignatura"].notna()
        ]
        if opciones.empty:
            cupos_vacios.append(
                {
                    "nu_periodo_formacion": int(fila["periodo"]),
                    "ds_nombre_cupo": str(fila["nombre"]),
                    "nu_creditos": int(fila["creditos"]),
                }
            )

    con_id = crudo.loc[crudo["id_asignatura"].map(_tiene_id)].copy()
    lineas = lineas_tematicas or {}
    filas = []
    for fila in con_id.to_dict(orient="records"):
        identificador = int(fila["id_asignatura"])
        nombre = str(fila["nombre"]).strip()
        slot = _texto_opcional(fila.get("slot"))
        filas.append(
            {
                "nu_periodo_formacion": int(fila["periodo"]),
                "id_asignatura": identificador,
                "ds_nombre_asignatura": nombre,
                "ds_nombre_pensum": nombre,
                "nu_creditos": int(fila["creditos"]),
                "ds_clasificacion": _texto_opcional(fila.get("clasificacion")) or "",
                "ds_grupo_slot": slot or "",
                "ds_linea_tematica": lineas.get(identificador, ""),
                "ds_bloque_electivo": slot or "",
            }
        )
    return pd.DataFrame(filas, columns=COLUMNAS_PENSUM), cupos_vacios


def convertir_prerrequisitos(ruta: Path) -> pd.DataFrame:
    """Los prerrequisitos de Cóndor ya traen el esquema de Pensunet."""
    tabla = pd.read_csv(ruta, encoding="utf-8")
    esperadas = [
        "id_asignatura",
        "ds_nombre_asignatura",
        "id_prerequisito",
        "ds_nombre_prerequisito",
        "nu_orden",
        "fl_debe_aprobado",
    ]
    faltan = [col for col in esperadas if col not in tabla.columns]
    if faltan:
        raise ValueError(f"A {ruta} le faltan columnas: {', '.join(faltan)}.")
    return tabla.loc[:, esperadas].copy()


def _lineas_fisica_actuales(ruta: Path) -> dict[int, str]:
    """Conserva ds_linea_tematica del pensum de Física vigente por id."""
    if not ruta.is_file():
        return {}
    tabla = pd.read_csv(ruta, encoding="utf-8")
    if "ds_linea_tematica" not in tabla.columns:
        return {}
    resultado: dict[int, str] = {}
    for fila in tabla.to_dict(orient="records"):
        valor = _texto_opcional(fila.get("ds_linea_tematica"))
        if valor is None:
            continue
        resultado[int(fila["id_asignatura"])] = valor
    return resultado


def _tiene_id(valor: object) -> bool:
    if valor is None:
        return False
    try:
        if bool(pd.isna(valor)):
            return False
    except (TypeError, ValueError):
        pass
    texto = str(valor).strip()
    return texto != "" and texto.lower() != "nan"


def _texto_opcional(valor: object) -> str | None:
    if valor is None:
        return None
    try:
        if bool(pd.isna(valor)):
            return None
    except (TypeError, ValueError):
        pass
    texto = str(valor).strip()
    if texto == "" or texto.lower() == "nan":
        return None
    return texto


if __name__ == "__main__":
    main()
