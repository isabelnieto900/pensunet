"""Supuestos con los que se simulará el flujo de estudiantes."""

from dataclasses import dataclass


class _CupoDelPlan:
    """Sentinel: usar el cupo electivo calculado del plan."""

    def __repr__(self) -> str:
        return "CUPO_DEL_PLAN"


CUPO_DEL_PLAN = _CupoDelPlan()


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

    - ``creditos_electivas_minimos``: cupo de créditos electivos. Por
      defecto ``CUPO_DEL_PLAN``: se toma el del plan
      (``creditos_electivos_del_plan``: Física 18, Química 10, Biología
      18, Matemáticas 12). Un entero lo sustituye; con ``None`` se
      exige aprobar todos los nodos electivos (más cercano al paper).
    - ``electivas_sin_reintento``: si se reprueba una electiva, no se
      vuelve a cursar; el crédito no cuenta y se puede elegir otra.
    - ``max_semestres``: tope de la trayectoria; si no hay grado a tiempo
      la observación se censura en ese valor (no aborta la muestra).
    - ``opciones_excluyentes``: un cupo no electivo con varias opciones
      (mismo ``grupo_slot``: idiomas, énfasis, profundizaciones) se cumple
      aprobando una sola opción. Con ``False`` se exigen todas, como si
      fueran obligatorias independientes.
    - ``max_creditos_semestre``: tope de créditos inscritos por semestre.
      Con ``None`` (por defecto) no hay tope, como en el artículo. Con
      tope, se inscriben primero las obligatorias de semestre recomendado
      más bajo (desempate por código) y luego la electiva, mientras
      quepan; una asignatura que sola supera el tope se permite si es la
      primera del semestre, para no bloquear la trayectoria.

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
    creditos_electivas_minimos: int | None | _CupoDelPlan = CUPO_DEL_PLAN
    electivas_sin_reintento: bool = True
    max_semestres: int = 40
    max_creditos_semestre: int | None = None
    opciones_excluyentes: bool = True

    def __post_init__(self) -> None:
        """Exige al menos un estudiante. Ecuaciones (3) y (4): X necesita una muestra."""
        if self.n_estudiantes < 1:
            raise ValueError("El escenario necesita al menos un estudiante representativo.")
        if self.max_semestres < 1:
            raise ValueError("El escenario necesita al menos un semestre de simulación.")
        if self.max_creditos_semestre is not None and self.max_creditos_semestre < 1:
            raise ValueError("El tope de créditos por semestre debe ser positivo o None.")
        cupo = self.creditos_electivas_minimos
        if cupo is not CUPO_DEL_PLAN and cupo is not None:
            if not isinstance(cupo, int):
                raise ValueError(
                    "El mínimo de créditos electivos debe ser un entero, "
                    "None o CUPO_DEL_PLAN."
                )
            if cupo < 0:
                raise ValueError("El mínimo de créditos electivos no puede ser negativo.")
