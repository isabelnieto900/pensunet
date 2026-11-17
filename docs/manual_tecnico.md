# Manual técnico

Estado: describe la arquitectura que ya está en el código y el método de
Molontay et al. (2020) que implementa: red, indicadores, complejidad
curricular y Monte Carlo del tiempo de grado.

Referencia:

> Molontay, R., Horváth, N., Bergmann, J., Szekrényes, D. y Szabó, M. (2020).
> Characterizing Curriculum Prerequisite Networks by a Student Flow Approach.
> *IEEE Transactions on Learning Technologies*, 13(3), 491–501.
> DOI: 10.1109/TLT.2020.2981331.

El artículo no publica código. Pensunet es una implementación original
de sus definiciones. Las citas de ecuación en los docstrings apuntan a
esa numeración.

## Alcance

Entra en esta versión:

- leer el pensum, los prerrequisitos y las tasas agregadas;
- construir el grafo dirigido y rechazarlo si tiene un ciclo;
- calcular el semestre mínimo impuesto por los prerrequisitos;
- calcular el factor de bloqueo, el factor de posponimiento y la
  intermediación.

Entra también la interfaz Streamlit (`src/pensunet/ui/app.py`) con
selector de carrera FCMN, la figura/HTML de la red, los cuellos de
botella de la ecuación (2) y el Monte Carlo del tiempo de grado
(tasas editables; TG sin valor por defecto).

No entra: el efecto de atravesar una asignatura, probabilidades
distintas por estudiante ni un modelo SIR.

## Arquitectura

```text
SimuladorPensum                 fachada (selector de programa FCMN)
    │
    ├── LectorDatos             solo CSV en esta versión
    │     └── AdaptadorUD       columnas de la Universidad Distrital
    ├── ajustes                 correcciones documentadas por programa
    ├── RedPrerrequisitos       DAG con networkx
    ├── indicadores             bloqueo, posponimiento, intermediación
    ├── complejidad             retraso y complejidad (Curricular Analytics)
    └── EstrategiaSimulacion    MonteCarloMolontay (sección III.B)
```

El dominio no importa la capa de datos. Recibe dataframes con nombres
internos (`id_asignatura`, `semestre`, `debe_aprobado`, `tasa_aprobacion`).
La interfaz habla con `SimuladorPensum` y ofrece un selector entre
Física, Química, Biología y Matemáticas.

## Patrones y por qué están

**Fachada (`SimuladorPensum`).** Cargar datos, armar el grafo, pedir
indicadores y, más adelante, lanzar la simulación son pasos que la
interfaz y los ejemplos van a repetir. La fachada los ofrece juntos
para que ese código no dependa de networkx ni de los nombres de columna
de la universidad.

**Fábrica (`FabricaLectores`).** El modelo necesita las mismas tres
tablas. Quien llama pide `"csv"` y recibe un `LectorDatos`. Si más
adelante hubiera otro origen, el grafo no tendría que enterarse; en
esta versión el único tipo admitido es CSV.

**Adaptador (`AdaptadorUD`).** El extracto usa `nu_periodo_formacion`,
`ds_nombre_asignatura`, `fl_debe_aprobado`. El dominio habla de
`semestre`, `nombre` y `debe_aprobado`. El adaptador traduce ese esquema
y no corrige cifras. Si el sistema académico renombra una columna, el
cambio se concentra en un solo módulo.

**Estrategia de reglas (`ReglasCarrera`).** Las correcciones locales
(etapa 2) son propias de cada carrera. La fachada solo conoce el
contrato `ReglasCarrera.preparar(pensum, prerrequisitos, tasas)` y
`FabricaReglas.crear(clave)` elige la implementación:
`ReglasDocumentadas` aplica las filas del programa en
`ajustes_prerrequisitos.csv` (`ReglasFisica` es la de Física) y
`ReglasSoloExtracto` deja el CSV tal cual para auditar el dato crudo.
Las reglas viven como datos con justificación, no como constantes en el
código.

**Estrategia (`EstrategiaSimulacion`).** La sección III.B es un
algoritmo intercambiable. Hoy la única estrategia es
`MonteCarloMolontay`.
Cuando haya probabilidades por estudiante u otra dinámica, se escribe
otra estrategia sin rehacer la fachada ni el grafo.

Hacen falta porque el artículo describe un método y no entrega un
programa, y porque las fases siguientes (tasas por estudiante, otra
dinámica de propagación, interfaz) tienen que poder entrar sin mezclarse
con el DAG.

## Metodología

### Representación (sección II.A)

El pensum es un grafo dirigido G = (V, E). Cada nodo es una asignatura.
Hay una arista de i a j, y la matriz de adyacencia cumple M_ij = 1,
cuando i es prerrequisito de j. El grafo tiene que ser acíclico: un
ciclo diría que i se exige para cursar j y j se exige para cursar i.

El artículo deja fuera los prerrequisitos débiles, los que permiten
inscribir las dos asignaturas en el mismo semestre. En los datos eso es
`debe_aprobado = False`. `construir_red` los omite por defecto y los
lista en `prerrequisitos_debiles_excluidos`. No los borra del CSV.

El nivel, o semestre mínimo, de una asignatura sin prerrequisitos es 1.
Si los tiene, es uno más que el mayor nivel de sus prerrequisitos. El
semestre escrito en el plan puede ser mayor: la tabla de Física no
conecta varias obligatorias de los últimos semestres, y su nivel de
grafo queda en 1 aunque el plan las ubique en el semestre 10. Las dos
cifras se conservan.

### Indicadores topológicos (sección II.B)

**Factor de bloqueo.** Una asignatura tiene factor de bloqueo n si tiene
exactamente n descendientes. Cuentan los indirectos, no solo el grado de
salida. La asignatura misma no entra en la cuenta.

**Factor de posponimiento.** El artículo lo llama *deferment factor* y
lo define como 1/(k + 1). k es el máximo número de veces que se puede
reprobar la asignatura sin aumentar el tiempo de grado; a la reprobación
k + 1 hace falta al menos un semestre más. Si el factor es 1/3, se puede
reprobar dos veces (k = 2) y a la tercera el grado se alarga. En el
segundo currículo de la figura 1, A, B y D tienen factor 1 y C tiene
factor 1/2.

Pensunet calcula esa k así. T es la duración nominal, el máximo semestre
del plan. s(v) es el mayor entre el semestre del plan y el nivel por
prerrequisitos: no se puede empezar antes de ninguno de los dos (el
límite del semestre recomendado es un supuesto de la sección III, y el
de los prerrequisitos es la sección II.A). d(v) es el número de aristas
del camino más largo que sale de v; cada una reserva un semestre para un
descendiente.

```text
k(v) = max(0, T - s(v) - d(v))
factor(v) = 1 / (k(v) + 1)
```

El tope en cero cubre un plan cuya cadena ya no cabe en T: no hay
reprobaciones “gratis”. En el ejemplo del programa de ingeniería
eléctrica del artículo, el camino más largo tiene seis asignaturas y el
plan dura siete semestres, así que en esa cadena se puede reprobar una
sola vez y el factor es 1/2. La misma cuenta reproduce el segundo
currículo de la figura 1. Hay una prueba con ese currículo.

**Intermediación.** Ecuación (1):

```text
b_v = suma sobre s ≠ v, t ≠ v de  sigma_st(v) / sigma_st
```

`sigma_st` es el número de caminos más cortos de s a t y `sigma_st(v)`
cuántos pasan por v. `intermediacion` devuelve esa suma. La tabla III
del artículo muestra valores pequeños, del orden de 10^-3, que cuadran
con la intermediación normalizada de un grafo dirigido (la ecuación (1)
dividida por (n - 1)(n - 2)). Ese valor se pide con `normalizada=True`.
El artículo mismo advierte que, en un DAG curricular, la intermediación
se interpreta con cuidado.

**Ecuación (2), cuellos de botella.** El artículo cuenta asignaturas
cuyo grado de entrada, de salida o total supera unos umbrales a, b y c.
No está implementada. No hace falta para los indicadores de esta etapa.

Estos indicadores solo miran la forma del grafo. No usan la tasa de
aprobación. Eso es deliberado: la sección II.C y la sección III meten
las tasas, y esa parte es la simulación que falta.

### Tiempo de grado (secciones II.C y III)

El tiempo de grado X es el número de semestres que se necesitan para
aprobar todas las asignaturas exigidas. Su función de masa y su
esperanza son

```text
p(x) = P(X = x)                         (3)
E(X) = suma de x * p(x)                 (4)
```

El artículo escribe E(X) = f(p_1, ..., p_n), con p_i la probabilidad de
aprobar la asignatura i, y define el efecto de atravesar la asignatura i
como la derivada parcial de f respecto de p_i (ecuación (5)) y la
elasticidad correspondiente (ecuación (6)). Ninguna de las dos está
calculada.

La probabilidad se estima con el histórico, ecuación (7):

```text
p_i ≈ (estudiantes que aprueban i) / (estudiantes que inscriben i)
```

En los CSV eso es `n_aprobados / n_inscritos`, ya guardado en
`tasa_aprobacion`. Una inscripción del histórico de Física cuenta como
aprobada cuando `fl_aprobada` es verdadero. La ventana es 2023-2 a
2025-2.

Supuestos de la sección III, guardados en `Escenario` y todavía sin
ejecutar:

- no se cursa una asignatura antes de su semestre recomendado;
- el estudiante intenta todas las que ya le permite la red, en el
  primer semestre posible;
- todas las asignaturas se abren cada semestre;
- p_i no cambia con el número de intento;
- aprobar una asignatura no cambia la probabilidad de las otras;
- se reintenta hasta aprobar;
- no hay semestres pasivos.

Con intentos independientes, el número de intentos X_i sigue una
geométrica de parámetro p_i y E(X_i) = 1/p_i. El semestre en que se
termina una asignatura depende del máximo de los semestres en que se
terminan sus prerrequisitos. La esperanza de ese máximo tiene forma
cerrada si las geométricas son independientes (ecuaciones (8) y (9)),
pero al anidar los caminos el máximo deja de ser geométrico y la cuenta
analítica se vuelve intratable. Por eso el artículo simula.

### Monte Carlo (sección III.B)

`MonteCarloMolontay.simular` estima p(x) y E(X) con estudiantes
representativos. Exige una tasa para cada nodo del grafo. Electivas y
Trabajo de grado sin histórico quedan vacíos en el CSV; la interfaz
permite completarlos antes de simular y no asigna 0 ni 1 por defecto.

Además de la muestra de X, `ResultadoSimulacion` guarda:

- `censurados`: qué trayectorias no se graduaron antes del tope
  `max_semestres`; `tasa_grado_en(n)` da la proporción graduada en a lo
  sumo n semestres (las censuradas no cuentan);
- `reprobaciones` e `inscripciones` por asignatura en toda la muestra;
  `asignaturas_que_frenan(n)` ordena por reprobaciones medias por
  estudiante. Es la versión dinámica (con tasas reales) del cuello de
  botella estructural de la ecuación (2).

Cupos: las asignaturas no electivas con el mismo `grupo_slot` son
opciones excluyentes (`Escenario.opciones_excluyentes`, por defecto
verdadero): el estudiante elige al azar una opción elegible con p_i
conocida y la cursa hasta aprobarla. Las electivas se cubren por
créditos; `creditos_electivos_del_plan` suma un cupo electivo por
`grupo_slot` (Física: 18). Las opciones y electivas sin tasa no se
eligen; las obligatorias sin tasa impiden simular.

`Escenario.max_creditos_semestre` (por defecto `None`, sin tope, como el
artículo) limita los créditos inscritos por semestre. Con tope se
inscriben primero las obligatorias de semestre recomendado más bajo
(desempate por código) y luego la electiva si cabe; una asignatura que
sola supera el tope se permite si es la primera del semestre. Sin tope,
la muestra es idéntica a la de la versión anterior con la misma semilla.

Las ecuaciones (10), (11) y (12) (efecto de atravesar la asignatura) y
la (13) quedan fuera de esta versión.

### Complejidad curricular (Curricular Analytics)

`dominio/complejidad.py` implementa las métricas de Heileman et al.
(2018), *Curricular Analytics: A Framework for Quantifying the Impact of
Curricular Reforms and Pedagogical Innovations* (arXiv:1811.09676), que
usa curricularanalytics.org:

- factor de bloqueo b(v): asignaturas alcanzables desde v (coincide con
  el *blocking factor* de Molontay);
- factor de retraso d(v): vértices del camino más largo del DAG que pasa
  por v;
- complejidad estructural h(v) = d(v) + b(v), y complejidad curricular
  del plan = Σ h(v).

Son medidas estructurales: no usan tasas. En la figura 1 del artículo
(A→B→D, A→C) dan h = 6, 4, 2, 3 y un total de 15 (prueba en
`tests/test_complejidad.py`).

## Datos que entran al grafo

Los cuatro programas FCMN, el origen Cóndor/SGA, la ventana de tasas
2023-2 a 2025-2, los ajustes documentados y el tratamiento de Trabajo
de Grado están en `data/README.md`.

Física con ajustes documentados: **67 nodos, 53 aristas estrictas**,
DAG, duración nominal 10 (incluye las reglas de la etapa 2: solo
inglés, sin electivas no ofrecidas y las cadenas de materiales, gestión
y cátedras). El extracto crudo del SGA tiene 91 asignaturas
y 46 aristas estrictas (más inconsistencias anotadas, p. ej. el cupo
25139 sin código).

Resumen de ajustes (nunca silenciosos; ver
`data/reference/ajustes_prerrequisitos.csv`):

- Física: se agregan 25140 → 25145, TG I → TG II (salvo pasantía),
  25141 → 25146 → 25151, 25142 → 25148 → 25153 y 4 → 12; se excluyen
  biosistemas (25176), los idiomas distintos del inglés, las electivas
  no ofrecidas y la arista al cupo 25139.
- Química: se conservan las aristas que invierten semestre; no se agrega
  TG I → TG II.
- Biología y Matemáticas: candidatos faltantes de la auditoría quedan
  pendientes; no se agregan.

Trabajo de Grado: tasa vacía / juicio experto en las cuatro carreras;
no se usa 0 ni 1 por defecto.

## Pruebas

`pytest` cubre la carga y el adaptador, el DAG (regresión de Física y
casos parametrizados por carrera: ids únicos, aciclicidad, créditos del
plan, códigos de prerrequisito), los indicadores (incluido el currículo
de la figura 1), la complejidad curricular, el Monte Carlo
(reproducibilidad con semilla, tope de créditos, reprobaciones y tasa de
grado), las tablas de la interfaz y las tasas. `ruff check` cubre el
estilo.

## Reproducibilidad: Docker e integración continua

- `Dockerfile`: imagen `python:3.12-slim` que instala el paquete en modo
  editable con el extra `ui` (el paquete ubica `data/` relativo a
  `src/`), copia solo los CSV agregados (`data/reference`,
  `data/processed`; nunca `data/private`), corre como usuario sin
  privilegios y expone Streamlit en el puerto 8501 con *healthcheck* en
  `/_stcore/health`.
- `docker-compose.yml`: `docker compose up --build` levanta la interfaz.
- `.dockerignore`: deja fuera `.git`, entornos, cachés y microdatos.
- `.github/workflows/ci.yml`: `ruff check .` y `pytest` en Python 3.10 y
  3.12; luego construye la imagen y comprueba el *health check*.
