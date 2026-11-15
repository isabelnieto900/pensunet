"""Supuestos con los que se simulará el flujo de estudiantes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Escenario:
    """Supuestos de la sección III de Molontay et al. (2020).

    El artículo simula 10 000 estudiantes representativos. Cada supuesto
    de abajo está activo en ese modelo y se guarda aquí para que la
    etapa 3 no los deje implícitos:

    - una asignatura no se cursa antes de su semestre recomendado;
    - el estudiante intenta en el primer semestre en que los
      prerrequisitos ya se lo permiten;
    - todas las asignaturas se abren cada semestre;
    - la probabilidad de aprobar es constante entre intentos;
    - aprobar una asignatura no cambia la probabilidad de las demás;
    - se vuelve a inscribir la asignatura hasta aprobarla;
    - no hay semestres pasivos.

    El tiempo de grado es la variable aleatoria X de las ecuaciones (3)
    y (4). Este objeto no ejecuta la simulación.
    """

    n_estudiantes: int = 10_000
    semilla: int | None = None
    respetar_semestre_recomendado: bool = True
    intentar_en_el_primer_semestre_posible: bool = True
    cursos_cada_semestre: bool = True
    probabilidad_constante: bool = True
    exitos_independientes: bool = True
    reintenta_hasta_aprobar: bool = True
    sin_semestres_pasivos: bool = True

    def __post_init__(self) -> None:
        """Exige al menos un estudiante. Ecuaciones (3) y (4): X necesita una muestra."""
        if self.n_estudiantes < 1:
            raise ValueError("El escenario necesita al menos un estudiante representativo.")
