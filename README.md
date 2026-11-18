# Pensunet

Simulador de la red de prerrequisitos de los pensum FCMN (Física,
Química, Biología y Matemáticas) de la Universidad Distrital Francisco
José de Caldas (Bogotá).
Esta versión cubre la red de
prerrequisitos, los indicadores topológicos, la complejidad
curricular al estilo de Curricular Analytics, el Monte Carlo del tiempo
de grado y una interfaz Streamlit, empaquetada también en Docker.

## Objetivo

Pensunet representa el pensum como un grafo dirigido de prerrequisitos y
calcula indicadores de cuello de botella curricular

## Instalación

Se requiere Python 3.10 o superior.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

La interfaz gráfica Streamlit es una dependencia opcional:

```bash
pip install -e ".[ui]"
```

## Uso

```python
from pensunet import SimuladorPensum

simulador = SimuladorPensum.desde_programa("fisica")  # o quimica, biologia, matematicas
simulador.cargar()
indicadores = simulador.indicadores()
complejidad = simulador.complejidad()      # retraso, bloqueo y h(v) por asignatura
```

Monte Carlo del tiempo de grado (sección III.B). Toda asignatura del
grafo necesita p_i; las que no tienen histórico (p. ej. Trabajo de Grado)
se completan explícitamente:

```python
from pensunet.dominio.escenario import Escenario

resultado = simulador.simular(
    Escenario(n_estudiantes=2000, semilla=1, max_creditos_semestre=None),
    tasas=tasas_completas,  # DataFrame con id_asignatura y tasa_aprobacion
)
resultado.media, resultado.tasa_grado_en(12), resultado.asignaturas_que_frenan(5)
```

CLI: `python examples/ejemplo_cargar_red.py --programa quimica`.

Interfaz Streamlit (selector de carrera en la barra lateral):

```bash
pip install -e ".[ui]"
python examples/ejecutar_interfaz.py
```

Con Docker (no requiere Python local):

```bash
docker compose up --build        # o: docker build -t pensunet . && docker run -p 8501:8501 pensunet
# abrir http://localhost:8501
```

Para ejecutar las pruebas:

```bash
pytest
ruff check .
```

La integración continua (`.github/workflows/ci.yml`) corre `ruff` y
`pytest` en Python 3.10 y 3.12 y construye la imagen Docker en cada push
a `main` y en cada pull request.

## Estructura

```
src/pensunet/
  facade.py                 Fachada SimuladorPensum
  datos/                    Lector CSV, fábrica y adaptador UD
  dominio/                  DAG, indicadores, complejidad, escenario y figura
  simulacion/               Estrategia y Monte Carlo de Molontay
  ui/                       Interfaz Streamlit (app.py) y tablas
data/reference/             Pensum y prerrequisitos
data/processed/             Tasas de aprobación agregadas por asignatura
data/private/               Ignorado por git: no guardar microdatos
.streamlit/config.toml      Tema claro/oscuro de la interfaz
Dockerfile, docker-compose.yml, .github/workflows/ci.yml
.github/workflows/docs.yml  Sphinx → GitHub Pages
docs/                       Sphinx (conf.py, index, API) y manuales
examples/
tests/
```

Los patrones (fachada, fábrica, adaptador y estrategia) se justifican en
`docs/manual_tecnico.md`.

## Documentación

La documentación (manuales y referencia de la API generada desde los
docstrings) se publica en <https://isabelnieto900.github.io/pensunet/>.
Para construirla en local:

```bash
pip install -e ".[docs]"
sphinx-build -W -b html docs docs/_build/html
```

El flujo `.github/workflows/docs.yml` la construye y la publica en cada
push a `main`.


## Licencia

Se incluye una licencia MIT provisional
([LICENSE](LICENSE)). 
