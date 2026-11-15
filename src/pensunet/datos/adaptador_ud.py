"""Traduce las columnas del sistema académico de la Universidad Distrital."""

from collections.abc import Mapping

import pandas as pd

_COLUMNAS_PENSUM = {
    "id_asignatura": "id_asignatura",
    "ds_nombre_asignatura": "nombre",
    "ds_nombre_pensum": "nombre_pensum",
    "nu_periodo_formacion": "semestre",
    "nu_creditos": "creditos",
    "ds_clasificacion": "clasificacion",
    "ds_grupo_slot": "grupo_slot",
    "ds_linea_tematica": "linea_tematica",
    "ds_bloque_electivo": "bloque_electivo",
}

_COLUMNAS_PRERREQUISITOS = {
    "id_asignatura": "id_asignatura",
    "ds_nombre_asignatura": "nombre",
    "id_prerequisito": "id_prerequisito",
    "ds_nombre_prerequisito": "nombre_prerequisito",
    "nu_orden": "orden",
    "fl_debe_aprobado": "debe_aprobado",
}

_COLUMNAS_TASAS = {
    "id_asignatura": "id_asignatura",
    "ds_nombre_asignatura": "nombre",
    "n_inscritos": "n_inscritos",
    "n_aprobados": "n_aprobados",
    "tasa_aprobacion": "tasa_aprobacion",
    "n_bajo": "n_bajo",
}


class AdaptadorUD:
    """Adapta el esquema de la Universidad Distrital al modelo interno.

    No modifica cifras ni identificadores. Solo renombra y tipa, para que
    el grafo de la sección II.A y la estimación de la ecuación (7) no
    dependan de los nombres ``ds_`` y ``nu_`` del sistema académico.
    """

    def adaptar_pensum(self, tabla: pd.DataFrame) -> pd.DataFrame:
        """Adapta el pensum. Sección II.A: cada fila será un nodo."""
        adaptada = _renombrar(tabla, _COLUMNAS_PENSUM, "pensum")
        adaptada["id_asignatura"] = _entero(adaptada["id_asignatura"])
        adaptada["nombre"] = _texto_obligatorio(adaptada["nombre"])
        adaptada["nombre_pensum"] = _texto_opcional(adaptada["nombre_pensum"])
        adaptada["semestre"] = _entero(adaptada["semestre"])
        adaptada["creditos"] = _entero(adaptada["creditos"])
        adaptada["clasificacion"] = _texto_opcional(adaptada["clasificacion"])
        adaptada["grupo_slot"] = _texto_opcional(adaptada["grupo_slot"])
        adaptada["linea_tematica"] = _texto_opcional(adaptada["linea_tematica"])
        adaptada["bloque_electivo"] = _texto_opcional(adaptada["bloque_electivo"])
        return adaptada

    def adaptar_prerequisitos(self, tabla: pd.DataFrame) -> pd.DataFrame:
        """Adapta las aristas. Sección II.A: i prerrequisito de j.

        ``debe_aprobado`` conserva el criterio estricto o débil. El
        artículo no usa los prerrequisitos débiles al armar el grafo.
        """
        adaptada = _renombrar(tabla, _COLUMNAS_PRERREQUISITOS, "prerrequisitos")
        adaptada["id_asignatura"] = _entero(adaptada["id_asignatura"])
        adaptada["nombre"] = _texto_obligatorio(adaptada["nombre"])
        adaptada["id_prerequisito"] = _entero(adaptada["id_prerequisito"])
        adaptada["nombre_prerequisito"] = _texto_obligatorio(adaptada["nombre_prerequisito"])
        adaptada["orden"] = _entero(adaptada["orden"])
        adaptada["debe_aprobado"] = _booleano(adaptada["debe_aprobado"])
        return adaptada

    def adaptar_tasas(self, tabla: pd.DataFrame) -> pd.DataFrame:
        """Adapta las tasas agregadas. Ecuación (7).

        ``n_bajo`` se conserva: es verdadero cuando hay menos de 5
        inscritos y la estimación de p_i es inestable. No se recalcula
        la tasa a partir de los conteos.
        """
        adaptada = _renombrar(tabla, _COLUMNAS_TASAS, "tasas de aprobación")
        adaptada["id_asignatura"] = _entero(adaptada["id_asignatura"])
        adaptada["nombre"] = _texto_obligatorio(adaptada["nombre"])
        adaptada["n_inscritos"] = _entero(adaptada["n_inscritos"])
        adaptada["n_aprobados"] = _entero(adaptada["n_aprobados"])
        adaptada["tasa_aprobacion"] = adaptada["tasa_aprobacion"].astype(float)
        adaptada["n_bajo"] = _booleano(adaptada["n_bajo"])
        return adaptada


def _renombrar(tabla: pd.DataFrame, columnas: Mapping[str, str], nombre: str) -> pd.DataFrame:
    """Deja solo las columnas conocidas, ya con el nombre interno."""
    faltan = [columna for columna in columnas if columna not in tabla.columns]
    if faltan:
        lista = ", ".join(faltan)
        raise ValueError(f"A la tabla de {nombre} le faltan columnas: {lista}.")
    return tabla.loc[:, list(columnas)].rename(columns=columnas).copy()


def _entero(serie: pd.Series) -> pd.Series:
    """Convierte identificadores y conteos a enteros de Python."""
    return serie.map(lambda valor: int(valor))


def _texto_obligatorio(serie: pd.Series) -> pd.Series:
    """Exige un texto no vacío."""

    def convertir(valor: object) -> str:
        texto = _a_texto(valor)
        if texto is None:
            raise ValueError("Hay un nombre de asignatura vacío.")
        return texto

    return serie.map(convertir)


def _texto_opcional(serie: pd.Series) -> pd.Series:
    """Convierte vacíos en None, sin inventar un texto.

    En pandas 3, ``map`` sobre una columna de texto vuelve a guardar el
    vacío como NaN. Se reconstruye la serie desde Python para que el
    hueco quede en None.
    """
    return pd.Series(
        [_a_texto(valor) for valor in serie.tolist()],
        index=serie.index,
        dtype=object,
    )


def _a_texto(valor: object) -> str | None:
    if _ausente(valor):
        return None
    texto = str(valor).strip()
    if texto == "" or texto.lower() == "nan":
        return None
    return texto


def _ausente(valor: object) -> bool:
    """Reconoce None, pd.NA y los NaN de numpy, que no son float de Python."""
    if valor is None:
        return True
    try:
        return bool(pd.isna(valor))
    except (TypeError, ValueError):
        return False


def _booleano(serie: pd.Series) -> pd.Series:
    """Acepta bool de pandas y los textos true/false del CSV."""

    def convertir(valor: object) -> bool:
        if isinstance(valor, bool):
            return bool(valor)
        if _ausente(valor):
            raise ValueError("Falta un valor booleano.")
        texto = str(valor).strip().lower()
        if texto in {"true", "1", "si", "sí", "verdadero"}:
            return True
        if texto in {"false", "0", "no", "falso"}:
            return False
        raise ValueError(f"No se pudo interpretar como booleano: {valor!r}.")

    return serie.map(convertir)
