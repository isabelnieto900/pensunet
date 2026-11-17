"""Reglas locales del programa de Física (validación experta).

Las correcciones están en ``data/reference/ajustes_prerrequisitos.csv``
(filas ``fisica``); esta clase solo fija el programa. Los CSV del SGA se
conservan sin cambios.
"""

from __future__ import annotations

import pandas as pd

from pensunet.dominio.reglas import ReglasDocumentadas, TablasAnalisis

# Constantes de la etapa 2 (PR #2). Son documentación y prueba: la fuente
# de verdad son las filas ``fisica`` de ``ajustes_prerrequisitos.csv`` y
# ``tests/test_reglas.py`` comprueba que ambas coinciden.

# Segunda lengua: un solo idioma en el modelo (inglés, el de más histórico).
IDIOMAS_MODELO = frozenset({9901, 9902, 9903})

# Cupos genéricos de línea de aplicación: no son materias cursables.
SLOTS_GENERICOS_LINEA = frozenset({25139, 25144, 25147, 25152})

# Confirmadas como no ofrecidas aunque tengan tasa en el histórico.
NO_OFRECIDAS = frozenset({25176})

# Electivas de línea sin inscritos en la ventana 2023-2 a 2025-2.
ELECTIVAS_SIN_OFERTA = frozenset(
    {25162, 25163, 25165, 25166, 25167, 25168, 25170, 25171, 25172, 25173, 25174}
)

# Aristas estrictas confirmadas y ausentes del extracto: (prerrequisito, asignatura).
ARISTAS_CONFIRMADAS = (
    (25140, 25145),  # Introducción a la mecánica cuántica → Cuántica avanzada
    (25149, 25154),  # Trabajo de grado I → Trabajo de grado II (salvo pasantía)
    (25141, 25146),  # Estado sólido → Ciencias de los materiales
    (25146, 25151),  # Ciencias de los materiales → Nanotecnología
    (25142, 25148),  # Modelos y gestión I → Modelos y gestión II
    (25148, 25153),  # Modelos y gestión II → Gestión tecnológica
    (4, 12),  # Cátedra F. J. de Caldas → Cátedra democracia y ciudadanía
    # Epistemología 25120 → 25127 ya viene en el CSV. 12 → 25115 (Historia
    # y filosofía de la ciencia I) sigue pendiente de confirmar.
)

# Cupo de créditos de línea de aplicación (I a IV).
CREDITOS_LINEA_APLICACION = 18


class ReglasFisica(ReglasDocumentadas):
    """Correcciones del plan de Física documentadas por quien cursa el programa."""

    def __init__(self) -> None:
        super().__init__("fisica")


def preparar_tablas_analisis(
    pensum: pd.DataFrame,
    prerrequisitos: pd.DataFrame,
    tasas: pd.DataFrame,
) -> TablasAnalisis:
    """Atajo compatible con la etapa 2: aplica ``ReglasFisica``."""
    return ReglasFisica().preparar(pensum, prerrequisitos, tasas)
