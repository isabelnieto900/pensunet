# Pensunet

Simulador de la red de prerrequisitos de los pensum FCMN (Física,
Química, Biología y Matemáticas) de la Universidad Distrital Francisco
José de Caldas (Bogotá).

Esta versión cubre la red de prerrequisitos, indicadores topológicos de
cuello de botella, complejidad curricular al estilo de Curricular
Analytics, Monte Carlo del tiempo de grado y una interfaz Streamlit
(también empaquetada en Docker).

## Objetivo

Pensunet modela el pensum como un grafo dirigido de prerrequisitos y
estima indicadores de bloqueo, posponimiento y tiempo esperado hasta el
grado a partir de tasas de aprobación agregadas.

## Instalación

Se requiere Python 3.10 o superior.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Interfaz Streamlit (opcional):

```bash
pip install -e ".[ui]"
```

## Uso

```python
from pensunet import SimuladorPensum

simulador = SimuladorPensum.desde_programa("fisica")  # o quimica, biologia, matematicas
simulador.cargar()
indicadores = simulador.indicadores()
complejidad = simulador.complejidad()  # retraso, bloqueo y h(v) por asignatura
```

Monte Carlo del tiempo de grado (usa las tasas cargadas; Trabajo de Grado
y juicios expertos ya vienen completados en `cargar()`):

```python
from pensunet.dominio.escenario import Escenario

resultado = simulador.simular(Escenario(n_estudiantes=2000, semilla=1))
resultado.resumen(semestres_a_tiempo=12)
resultado.tabla_asignaturas_que_frenan(simulador.red, n=5)
```

CLI: `python examples/ejemplo_cargar_red.py --programa quimica`.

Interfaz Streamlit:

```bash
pip install -e ".[ui]"
python examples/ejecutar_interfaz.py
```

Con Docker (sin Python local):

```bash
docker compose up --build
# abrir http://localhost:8501
```

Pruebas:

```bash
pytest
ruff check .
```

La CI (`.github/workflows/ci.yml`) corre `ruff` y `pytest` en Python 3.10
y 3.12, y construye la imagen Docker en cada push a `main` y en cada PR.

## Estructura

```
src/pensunet/
  facade.py                 Fachada SimuladorPensum
  datos/                    Lector CSV, fábrica y adaptador UD
  dominio/                  DAG, indicadores, complejidad, escenario y figura
  simulacion/               Estrategia y Monte Carlo del tiempo de grado
  ui/                       Interfaz Streamlit (app.py) y páginas
data/reference/             Pensum y prerrequisitos
data/processed/             Tasas de aprobación agregadas por asignatura
data/private/               Ignorado por git: no guardar microdatos
.streamlit/config.toml      Tema de la interfaz
Dockerfile, docker-compose.yml, .github/workflows/ci.yml
.github/workflows/docs.yml  Sphinx → GitHub Pages
docs/                       Sphinx, manuales y API
examples/
tests/
```

Los patrones de diseño se documentan en `docs/manual_tecnico.md`.

## Documentación

Manuales y API: <https://isabelnieto900.github.io/pensunet/>.

```bash
pip install -e ".[docs]"
sphinx-build -W -b html docs docs/_build/html
```

## Licencia

Licencia MIT provisional ([LICENSE](LICENSE)). Cómo citar: [CITATION.cff](CITATION.cff).
