"""Currículos pequeños tomados del artículo, para no depender solo de Física."""

import pandas as pd

from pensunet.dominio.red import RedPrerrequisitos, construir_red


def curriculo_figura_1() -> RedPrerrequisitos:
    """Segundo currículo de la figura 1: A bloquea a B y a C, y B bloquea a D.

    Sección II.A y sección II.B de Molontay et al. (2020).
    """
    pensum = pd.DataFrame(
        [
            {"id_asignatura": 1, "nombre": "A", "semestre": 1},
            {"id_asignatura": 2, "nombre": "B", "semestre": 2},
            {"id_asignatura": 3, "nombre": "C", "semestre": 2},
            {"id_asignatura": 4, "nombre": "D", "semestre": 3},
        ]
    )
    prerrequisitos = pd.DataFrame(
        [
            {"id_asignatura": 2, "id_prerequisito": 1, "debe_aprobado": True, "orden": 1},
            {"id_asignatura": 4, "id_prerequisito": 2, "debe_aprobado": True, "orden": 1},
            {"id_asignatura": 3, "id_prerequisito": 1, "debe_aprobado": True, "orden": 1},
        ]
    )
    return construir_red(pensum, prerrequisitos)
