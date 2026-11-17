"""Supuestos con los que se simulará el flujo de estudiantes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Escenario:
    """Supuestos de la sección III de Molontay et al. (2020), más políticas locales.

    El artículo simula 10 000 estudiantes representativos. Cada supuesto
    de abajo está activo en ese modelo y se guarda aquí para que no
    queden implícitos:

    - una asignatura no se cursa antes de su semestre recomendado;
    - el estudiante intenta en el primer semestre en que los
      prerrequisitos ya se lo permiten;
    - todas las asignaturas se abren cada semestre;
    - la probabilidad de aprobar es constante entre intentos;
    - aprobar una asignatura no cambia la probabilidad de las demás;
    - las obligatorias se vuelven a inscribir hasta aprobarlas;
    - no hay semestres pasivos.

    Políticas de Física (no del artículo BME):

    - ``creditos_electivas_minimos``: cupo de línea de aplicación; las
      electivas del grafo no son todas obligatorias, basta acumular ese
      mínimo de créditos. Con ``None`` se exige aprobar todos los nodos
      (comportamiento más cercano al paper).
    - ``electivas_sin_reintento``: si se reprueba una electiva, no se
      vuelve a cursar; el crédito no cuenta y se puede elegir otra.
    - ``max_semestres``: tope de la trayectoria; si no hay grado a tiempo
      la observación se censura en ese valor (no aborta la muestra).

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
    creditos_electivas_minimos: int | None = 18
    electivas_sin_reintento: bool = True
    max_semestres: int = 40

    def __post_init__(self) -> None:
        """Exige al menos un estudiante. Ecuaciones (3) y (4): X necesita una muestra."""
        if self.n_estudiantes < 1:
            raise ValueError("El escenario necesita al menos un estudiante representativo.")
        if self.max_semestres < 1:
            raise ValueError("El escenario necesita al menos un semestre de simulación.")
        if self.creditos_electivas_minimos is not None and self.creditos_electivas_minimos < 0:
            raise ValueError("El mínimo de créditos electivos no puede ser negativo.")
