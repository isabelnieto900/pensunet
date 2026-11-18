# Manual de usuario

## Interfaz Streamlit

```bash
pip install -e ".[ui]"
python examples/ejecutar_interfaz.py
# o: python -m streamlit run src/pensunet/ui/app.py
```

Sin instalar Python, con Docker:

```bash
docker compose up --build
# abrir http://localhost:8501
```

El tema (claro u oscuro) se cambia en el menú ⋮ → *Settings*; los dos
usan la paleta de Pensunet definida en `.streamlit/config.toml`.

Arriba de cada sección se ven las tarjetas del plan: asignaturas,
aristas estrictas, créditos, semestres, tasa media p̄ (promedio simple de
las asignaturas con histórico), complejidad curricular y número de
cuellos de botella.

En la barra lateral elige la carrera (Física, Química, Biología,
Matemáticas). Hay tres secciones:

1. **Red de prerrequisitos** — grafo interactivo con ajustes documentados.
2. **Indicadores** — bloqueo, posponimiento, intermediación, cuellos y
   camino más largo. El control *Color de las cajas* pinta la red por
   área del plan (colores del PDF), por tasa de aprobación (rojo → verde;
   gris = sin histórico) o por complejidad estructural h(v) = retraso +
   bloqueo. La tabla trae las columnas `retraso` y `complejidad`.
3. **Tiempo de grado** — Monte Carlo; edita tasas antes de simular.
   Trabajo de Grado y las demás filas de juicio experto llegan con
   p = 1 documentado (ver `data/reference/trabajo_de_grado.csv` y
   `juicio_experto.csv`). Las opciones de un cupo
   (idiomas, énfasis, profundizaciones) son excluyentes: basta aprobar
   una. En *Supuestos del escenario* están el cupo de créditos
   electivos (por defecto el del plan: Física 18, Química 10, Biología 18, Matemáticas 12), el tope de créditos
   por semestre (0 = sin tope) y el interruptor de cupos de opciones.
   Tras simular aparecen E(X), la proporción graduada en la duración
   nominal y con dos semestres de rezago, el histograma y la tabla de
   *asignaturas que más frenan* (reprobaciones medias por estudiante).

También puedes cargar desde Python o el CLI
`examples/ejemplo_cargar_red.py --programa …` (ver `README.md`).

## Modelo y ecuaciones

La red de prerrequisitos, los indicadores topológicos (bloqueo,
posponimiento, intermediación, cuellos de botella) y el Monte Carlo del
tiempo de grado siguen las definiciones y ecuaciones de:

> Molontay, R., Horváth, N., Bergmann, J., Szekrényes, D. y Szabó, M. (2020).
> Characterizing Curriculum Prerequisite Networks by a Student Flow Approach.
> *IEEE Transactions on Learning Technologies*, 13(3), 491–501.
> DOI: [10.1109/TLT.2020.2981331](https://doi.org/10.1109/TLT.2020.2981331).

En resumen:

- **Tasa de aprobación** \(p_i\): proporción de inscritos que aprueban la
  asignatura \(i\) en el histórico agregado.
- **Tiempo de grado** \(X\): semestre en el que un estudiante representativo
  cumple obligatorias, cupos y el mínimo de créditos electivos.
- **Distribución y esperanza**: \(p(x) = P(X = x)\) y \(E(X)\) se estiman
  por Monte Carlo (estudiantes simulados con las \(p_i\) del escenario).

El detalle de implementación y la correspondencia con las secciones del
artículo están en `docs/manual_tecnico.md`.
