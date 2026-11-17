"""Aplica correcciones documentadas sobre el extracto del SGA.

Los CSV de referencia se conservan fieles al SGA. Este módulo lee
``data/reference/ajustes_prerrequisitos.csv`` y produce las tablas de
análisis. Cada fila del archivo de ajustes trae justificación: no hay
correcciones silenciosas.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from pensunet.datos.programas import RUTA_AJUSTES


class ResultadoAjustes:
    """Tablas tras aplicar ajustes y bitácora de lo hecho."""

    def __init__(
        self,
        pensum: pd.DataFrame,
        prerrequisitos: pd.DataFrame,
        notas: list[str],
    ) -> None:
        self.pensum = pensum
        self.prerrequisitos = prerrequisitos
        self.notas = list(notas)


def aplicar_ajustes(
    pensum: pd.DataFrame,
    prerrequisitos: pd.DataFrame,
    programa: str,
    ruta_ajustes: str | Path | None = None,
) -> ResultadoAjustes:
    """Aplica las filas de ajustes del ``programa`` indicado.

    Acciones reconocidas:

    - ``agregar``: inserta una arista si no estaba.
    - ``excluir_nodo``: saca la asignatura del pensum y sus aristas.
    - ``excluir_arista``: elimina una arista concreta.
    - ``documentar``: no cambia tablas; solo deja la justificación en notas.
    """
    ruta = Path(ruta_ajustes) if ruta_ajustes is not None else RUTA_AJUSTES
    notas: list[str] = []
    if not ruta.is_file():
        notas.append(f"No hay archivo de ajustes en {ruta}.")
        return ResultadoAjustes(pensum.copy(), prerrequisitos.copy(), notas)

    ajustes = pd.read_csv(ruta, encoding="utf-8")
    del_programa = ajustes.loc[
        ajustes["programa"].map(lambda valor: str(valor).strip().lower())
        == programa.strip().lower()
    ]
    pensum_out = pensum.copy()
    prerreq_out = prerrequisitos.copy()

    for fila in del_programa.to_dict(orient="records"):
        accion = str(fila["accion"]).strip().lower()
        justificacion = str(fila.get("justificacion") or "").strip()
        if accion == "documentar":
            notas.append(_nota_documentar(fila, justificacion))
            continue
        if accion == "agregar":
            pensum_out, prerreq_out, mensaje = _agregar_arista(
                pensum_out, prerreq_out, fila, justificacion
            )
            notas.append(mensaje)
            continue
        if accion == "excluir_nodo":
            pensum_out, prerreq_out, mensaje = _excluir_nodo(
                pensum_out, prerreq_out, fila, justificacion
            )
            notas.append(mensaje)
            continue
        if accion == "excluir_arista":
            prerreq_out, mensaje = _excluir_arista(prerreq_out, fila, justificacion)
            notas.append(mensaje)
            continue
        raise ValueError(f"Acción de ajuste desconocida: {accion!r}.")

    return ResultadoAjustes(
        pensum=pensum_out.reset_index(drop=True),
        prerrequisitos=prerreq_out.reset_index(drop=True),
        notas=notas,
    )


def _nota_documentar(fila: dict, justificacion: str) -> str:
    id_asig = _entero_opcional(fila.get("id_asignatura"))
    id_prev = _entero_opcional(fila.get("id_prerequisito"))
    if id_asig is not None and id_prev is not None:
        return (
            f"Documentado (sin cambio de tablas): {id_prev} → {id_asig}. "
            f"{justificacion}"
        )
    return f"Documentado (sin cambio de tablas): {justificacion}"


def _agregar_arista(
    pensum: pd.DataFrame,
    prerrequisitos: pd.DataFrame,
    fila: dict,
    justificacion: str,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    id_asignatura = int(fila["id_asignatura"])
    id_prerequisito = int(fila["id_prerequisito"])
    debe = _booleano(fila.get("fl_debe_aprobado", True))
    ids = {int(valor) for valor in pensum["id_asignatura"]}
    if id_asignatura not in ids or id_prerequisito not in ids:
        return (
            pensum,
            prerrequisitos,
            (
                f"No se agregó {id_prerequisito} → {id_asignatura}: "
                f"falta un extremo en el pensum. {justificacion}"
            ),
        )
    ya = (
        (prerrequisitos["id_asignatura"] == id_asignatura)
        & (prerrequisitos["id_prerequisito"] == id_prerequisito)
    )
    if ya.any():
        return (
            pensum,
            prerrequisitos,
            f"La arista {id_prerequisito} → {id_asignatura} ya estaba. {justificacion}",
        )
    nombre_asig = pensum.loc[pensum["id_asignatura"] == id_asignatura, "nombre"].iloc[0]
    nombre_prev = pensum.loc[pensum["id_asignatura"] == id_prerequisito, "nombre"].iloc[0]
    nueva = pd.DataFrame(
        [
            {
                "id_asignatura": id_asignatura,
                "nombre": nombre_asig,
                "id_prerequisito": id_prerequisito,
                "nombre_prerequisito": nombre_prev,
                "orden": int(fila["nu_orden"]) if _presente(fila.get("nu_orden")) else 1,
                "debe_aprobado": debe,
            }
        ]
    )
    prerrequisitos = pd.concat([prerrequisitos, nueva], ignore_index=True)
    tipo = "estricta" if debe else "débil"
    return (
        pensum,
        prerrequisitos,
        (
            f"Se agregó la arista {tipo} {id_prerequisito} → {id_asignatura}. "
            f"{justificacion}"
        ),
    )


def _excluir_nodo(
    pensum: pd.DataFrame,
    prerrequisitos: pd.DataFrame,
    fila: dict,
    justificacion: str,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    identificador = int(fila["id_asignatura"])
    if identificador not in set(int(v) for v in pensum["id_asignatura"]):
        return (
            pensum,
            prerrequisitos,
            f"No estaba el nodo {identificador} para excluir. {justificacion}",
        )
    nombre = pensum.loc[pensum["id_asignatura"] == identificador, "nombre"].iloc[0]
    pensum = pensum.loc[pensum["id_asignatura"] != identificador].copy()
    prerrequisitos = prerrequisitos.loc[
        (prerrequisitos["id_asignatura"] != identificador)
        & (prerrequisitos["id_prerequisito"] != identificador)
    ].copy()
    return (
        pensum,
        prerrequisitos,
        f"Se excluyó el nodo {identificador} ({nombre}). {justificacion}",
    )


def _excluir_arista(
    prerrequisitos: pd.DataFrame,
    fila: dict,
    justificacion: str,
) -> tuple[pd.DataFrame, str]:
    id_asignatura = int(fila["id_asignatura"])
    id_prerequisito = int(fila["id_prerequisito"])
    mascara = (prerrequisitos["id_asignatura"] == id_asignatura) & (
        prerrequisitos["id_prerequisito"] == id_prerequisito
    )
    if not mascara.any():
        return (
            prerrequisitos,
            (
                f"No estaba la arista {id_prerequisito} → {id_asignatura} "
                f"para excluir. {justificacion}"
            ),
        )
    return (
        prerrequisitos.loc[~mascara].copy(),
        (
            f"Se excluyó la arista {id_prerequisito} → {id_asignatura}. "
            f"{justificacion}"
        ),
    )


def _entero_opcional(valor: object) -> int | None:
    if not _presente(valor):
        return None
    return int(valor)


def _presente(valor: object) -> bool:
    if valor is None:
        return False
    try:
        if bool(pd.isna(valor)):
            return False
    except (TypeError, ValueError):
        pass
    texto = str(valor).strip()
    return texto != "" and texto.lower() != "nan"


def _booleano(valor: object) -> bool:
    if isinstance(valor, bool):
        return bool(valor)
    if not _presente(valor):
        return True
    texto = str(valor).strip().lower()
    if texto in {"true", "1", "si", "sí", "verdadero"}:
        return True
    if texto in {"false", "0", "no", "falso"}:
        return False
    raise ValueError(f"No se pudo interpretar como booleano: {valor!r}.")


def listar_ajustes(programa: str | None = None, ruta: str | Path | None = None) -> pd.DataFrame:
    """Lee el CSV de ajustes, opcionalmente filtrado por programa."""
    tabla = pd.read_csv(Path(ruta) if ruta is not None else RUTA_AJUSTES, encoding="utf-8")
    if programa is None:
        return tabla
    return tabla.loc[
        tabla["programa"].map(lambda valor: str(valor).strip().lower())
        == programa.strip().lower()
    ].copy()


def notas_de_ajustes(notas: Iterable[str]) -> list[str]:
    """Copia defensiva de la bitácora."""
    return list(notas)
