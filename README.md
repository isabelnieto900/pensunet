# Pensunet

Simulador de la red de prerrequisitos de los pensum FCMN (Física,
Química, Biología y Matemáticas) de la Universidad Distrital Francisco
José de Caldas (Bogotá).

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
> *IEEE Transactions on Learning Technologies*, 13(3), 491–501.
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
from pensunet import SimuladorPensum

simulador = SimuladorPensum.desde_programa("fisica")  # o quimica, biologia, matematicas
simulador.cargar()
indicadores = simulador.indicadores()
```

CLI: `python examples/ejemplo_cargar_red.py --programa quimica`.

Interfaz Streamlit (selector de carrera en la barra lateral):

```bash
pip install -e ".[ui]"
python examples/ejecutar_interfaz.py
```

Para ejecutar las pruebas:

```bash
pytest
ruff check src tests examples
```

## Estructura

```
src/pensunet/
  facade.py                 Fachada SimuladorPensum
  datos/                    Lector CSV, fábrica y adaptador UD
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

En el repositorio solo hay tablas agregadas o de catálogo para las cuatro
carreras FCMN (`pensum_*.csv`, `prerequisitos_*.csv`,
`tasas_aprobacion_*.csv`), más `ajustes_prerrequisitos.csv` y el
catálogo de Trabajo de Grado sin tasa.

No hay registros individuales ni códigos de estudiante. Las tasas vienen
del histórico **2023-2 a 2025-2** (2026-1 no entra). El detalle de origen
Cóndor/SGA, ajustes y TG está en [`data/README.md`](data/README.md).

## Licencia

Se incluye una licencia MIT provisional
([LICENSE](LICENSE)). **La licencia definitiva está por confirmar con el
director del proyecto y con la Universidad Distrital** antes del registro
del 18 de noviembre de 2026. Hasta esa confirmación, no debe asumirse que
la MIT es la licencia institucional del trabajo.

Cómo citar el software y el artículo: [CITATION.cff](CITATION.cff).
