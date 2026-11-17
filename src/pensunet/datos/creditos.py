"""Suma de créditos del plan contando cada cupo una sola vez."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pensunet.datos.programas import RUTA_CUPOS_SIN_ASIGNATURA


def sumar_creditos_plan(
    pensum: pd.DataFrame,
    programa: str | None = None,
    cupos_sin_asignatura: pd.DataFrame | None = None,
) -> int:
    """Créditos del grado: un cupo (slot) aporta una vez; las opciones no se suman.

    Si el pensum ya trae columnas internas (``semestre``, ``creditos``,
    ``grupo_slot``), se usan. Los cupos del plan sin código de asignatura
    (p. ej. Electiva VI/VII de Química) se leen de
    ``cupos_sin_asignatura.csv`` cuando se indica ``programa``.
    """
    semestre_col = "semestre" if "semestre" in pensum.columns else "nu_periodo_formacion"
    creditos_col = "creditos" if "creditos" in pensum.columns else "nu_creditos"
    slot_col = "grupo_slot" if "grupo_slot" in pensum.columns else "ds_grupo_slot"

    total = 0
    for _, grupo in pensum.groupby(semestre_col, dropna=False):
        total += _creditos_del_periodo(grupo, creditos_col, slot_col)

    if programa is not None:
        cupos = cupos_sin_asignatura
        if cupos is None and RUTA_CUPOS_SIN_ASIGNATURA.is_file():
            cupos = pd.read_csv(RUTA_CUPOS_SIN_ASIGNATURA, encoding="utf-8")
        if cupos is not None and not cupos.empty:
            del_programa = cupos.loc[
                cupos["programa"].map(lambda valor: str(valor).strip().lower())
                == programa.strip().lower()
            ]
            total += int(del_programa["nu_creditos"].sum()) if not del_programa.empty else 0
    return int(total)


def _creditos_del_periodo(
    grupo: pd.DataFrame,
    creditos_col: str,
    slot_col: str,
) -> int:
    usados: set[str] = set()
    creditos = 0
    for fila in grupo.to_dict(orient="records"):
        slot = fila.get(slot_col)
        if slot is not None and not (isinstance(slot, float) and pd.isna(slot)):
            texto = str(slot).strip()
            if texto and texto.lower() != "nan":
                if texto in usados:
                    continue
                usados.add(texto)
                creditos += int(fila[creditos_col])
                continue
        creditos += int(fila[creditos_col])
    return creditos


def cargar_cupos_sin_asignatura(ruta: str | Path | None = None) -> pd.DataFrame:
    """Lee los cupos del plan que no tienen fila con ``id_asignatura``."""
    path = Path(ruta) if ruta is not None else RUTA_CUPOS_SIN_ASIGNATURA
    if not path.is_file():
        return pd.DataFrame(
            columns=["programa", "nu_periodo_formacion", "ds_nombre_cupo", "nu_creditos"]
        )
    return pd.read_csv(path, encoding="utf-8")
