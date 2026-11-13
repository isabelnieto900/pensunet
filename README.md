# Pensunet

Simulador de la red de prerrequisitos del pensum de Física de la
Universidad Distrital Francisco José de Caldas (Bogotá).

Titular de los derechos de autor: **Laura Isabel Nieto Parroyo**, 2026.
El software se presenta en la materia Desarrollo de Software Científico
(profesor Carlos Andrés Gómez Vasco). La versión 1 cubre solo la red de
prerrequisitos y los indicadores topológicos; la simulación Monte Carlo
del tiempo de grado queda esbozada.

## Objetivo

Pensunet representa el pensum como un grafo dirigido de prerrequisitos y
calcula indicadores de cuello de botella curricular. La referencia de
método es:

> Molontay, R., Horváth, N., Bergmann, J., Szekrényes, D. y Szabó, M. (2020).
> Characterizing Curriculum Prerequisite Networks by a Student Flow Approach.
> *IEEE Transactions on Learning Technologies*.
> DOI: [10.1109/TLT.2020.2981331](https://doi.org/10.1109/TLT.2020.2981331).

El artículo no publica código. Esta es una implementación original a partir
de sus definiciones y ecuaciones (secciones II y III). Cada función del
paquete indica en su docstring la ecuación o la sección que implementa.

Fases que **no** forman parte de esta versión: probabilidades distintas por
estudiante, el modelo SIR de Zhang, el enfoque de Castaldi y la
retroalimentación entre las escalas macro y micro.

## Instalación

Se requiere Python 3.10 o superior.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

La interfaz gráfica, prevista con Streamlit, es una dependencia opcional:

```bash
pip install -e ".[ui]"
```

## Uso

```python
from pathlib import Path

from pensunet.datos.fabrica import FabricaLectores
from pensunet import SimuladorPensum

raiz = Path(".")
lector = FabricaLectores.crear(
    "csv",
    ruta_pensum=raiz / "data/reference/pensum_fisica.csv",
    ruta_prerequisitos=raiz / "data/reference/prerequisitos_fisica.csv",
    ruta_tasas=raiz / "data/processed/tasas_aprobacion_fisica.csv",
)
simulador = SimuladorPensum(lector)
simulador.cargar()
indicadores = simulador.indicadores()
```

Un script equivalente está en `examples/ejemplo_cargar_red.py`.
La llamada `simulador.simular(...)` lanza `NotImplementedError`: el Monte
Carlo de la sección III.B se implementa en una etapa posterior.

Para ejecutar las pruebas:

```bash
pytest
ruff check src tests examples
```

## Estructura

```
src/pensunet/
  facade.py                 Fachada SimuladorPensum
  datos/                    Lectores CSV y stub de Redshift, adaptador UD
  dominio/                  DAG, indicadores y escenario
  simulacion/               Estrategia y esqueleto Monte Carlo
  ui/                       Placeholder de la interfaz
data/reference/             Pensum y prerrequisitos
data/processed/             Tasas de aprobación agregadas por asignatura
data/private/               Ignorado por git: no guardar microdatos
docs/                       Manual técnico y manual de usuario
examples/
tests/
```

Los patrones (fachada, fábrica, adaptador y estrategia) se justifican en
`docs/manual_tecnico.md`.

## Datos

En el repositorio solo hay tablas agregadas o de catálogo:

- `data/reference/pensum_fisica.csv`
- `data/reference/prerequisitos_fisica.csv`
- `data/processed/tasas_aprobacion_fisica.csv`

No hay registros individuales ni códigos de estudiante. Las tasas vienen del
histórico **2023-2 a 2025-2** de Física y una asignatura cuenta como
aprobada cuando `fl_aprobada` es verdadero. El detalle de cobertura, de
materias con pocos inscritos y de las inconsistencias entre las tres tablas
está en [`data/README.md`](data/README.md). Esas inconsistencias se
documentan; no se corrigen dentro de los archivos.

## Licencia

Se incluye una licencia MIT provisional
([LICENSE](LICENSE)). **La licencia definitiva está por confirmar con el
director del proyecto y con la Universidad Distrital** antes del registro
del 18 de noviembre de 2026. Hasta esa confirmación, no debe asumirse que
la MIT es la licencia institucional del trabajo.

Cómo citar el software y el artículo: [CITATION.cff](CITATION.cff).
