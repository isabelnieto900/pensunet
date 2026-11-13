# Manual técnico

Estado: borrador de la etapa 1. Describe la arquitectura que ya está en
el código y el método de Molontay et al. (2020) que esa etapa alcanza a
implementar. La simulación Monte Carlo no está programada.

Referencia:

> Molontay, R., Horváth, N., Bergmann, J., Szekrényes, D. y Szabó, M. (2020).
> Characterizing Curriculum Prerequisite Networks by a Student Flow Approach.
> *IEEE Transactions on Learning Technologies*. DOI: 10.1109/TLT.2020.2981331.

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

No entra: la simulación del tiempo de grado, el efecto de atravesar una
asignatura, los cuellos de botella de la ecuación (2), probabilidades
distintas por estudiante, un modelo SIR, ni la interfaz gráfica.

## Arquitectura

```text
SimuladorPensum                 fachada
    │
    ├── LectorDatos             CSV hoy, Redshift después
    │     └── AdaptadorUD       columnas de la Universidad Distrital
    ├── RedPrerrequisitos       DAG con networkx
    ├── indicadores             bloqueo, posponimiento, intermediación
    └── EstrategiaSimulacion    Monte Carlo, todavía sin algoritmo
```

El dominio no importa la capa de datos. Recibe dataframes con nombres
internos (`id_asignatura`, `semestre`, `debe_aprobado`, `tasa_aprobacion`).
La interfaz, cuando exista, solo debería hablar con `SimuladorPensum`.

## Patrones y por qué están

**Fachada (`SimuladorPensum`).** Cargar datos, armar el grafo, pedir
indicadores y, más adelante, lanzar la simulación son pasos que la
interfaz y los ejemplos van a repetir. La fachada los ofrece juntos
para que ese código no dependa de networkx ni de los nombres de columna
de la universidad.

**Fábrica (`FabricaLectores`).** El modelo necesita las mismas tres
tablas venga de un CSV o, después, de Redshift. Quien llama pide
`"csv"` o `"redshift"` y recibe un `LectorDatos`. El grafo no se entera
del cambio de origen. El lector de Redshift es un stub a propósito: no
hay conexión a medio implementar ni una ruta para bajar microdatos.

**Adaptador (`AdaptadorUD`).** El extracto usa `nu_periodo_formacion`,
`ds_nombre_asignatura`, `fl_debe_aprobado`. El dominio habla de
`semestre`, `nombre` y `debe_aprobado`. El adaptador traduce ese esquema
y no corrige cifras. Si el sistema académico renombra una columna, el
cambio se concentra en un solo módulo.

**Estrategia (`EstrategiaSimulacion`).** La sección III.B es un
algoritmo intercambiable. Hoy la única estrategia es
`MonteCarloMolontay` y su método `simular` lanza `NotImplementedError`.
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

### Monte Carlo (sección III.B), no implementado

El algoritmo previsto está descrito en el docstring de
`MonteCarloMolontay.simular` y lanza `NotImplementedError`. En resumen:
se estiman las p_i con la ecuación (7), se avanza semestre a semestre
respetando la red y se resume la muestra con las ecuaciones (3) y (4).
El artículo usa 10 000 estudiantes representativos.

En el caso de ingeniería eléctrica el artículo pone probabilidad 1 a las
electivas. Aquí no se hace. Varias electivas no tienen tasa porque no
se ofrecen: la carrera es nueva y no hay quien las dicte. Ponerles
probabilidad 1 diría que se aprueban, cuando el hecho es que no se
abren. `tasa_de` devuelve `None` cuando no hay fila. Trabajo de grado
I y II tampoco tienen tasa, y ese hueco sigue abierto.

Las ecuaciones (10), (11) y (12) son tres formas de subir p_i para
aproximar el efecto de atravesar la asignatura, y la (13) es el cociente
de esperanzas simuladas. Quedan para cuando exista la simulación.

## Datos que entran al grafo

Los archivos, las inconsistencias y las reglas que el programa confirmó
el 13 de noviembre de 2026 están en `data/README.md`. El grafo de esta
etapa no las incorpora: sigue teniendo 95 nodos, 46 aristas estrictas,
es acíclico y su duración nominal es 10 semestres.

Esas reglas, para cuando se modele la trayectoria y no solo el extracto:

- cuántica avanzada exige cuántica 1 (25140 en este plan, u otra
  materia equivalente vista en Licenciatura en Física);
- trabajo de grado II exige el I, salvo en pasantía, donde van juntas;
- óptica no tiene prerrequisito;
- física moderna precede en teoría a física atómica, pero se ven en el
  mismo semestre;
- cada idioma es una cadena I → II → III, de un solo idioma, con
  homologación por examen;
- el prerrequisito de biosistemas es un cierre de inscripción, no una
  condición académica, y la materia no está disponible;
- la línea de aplicación pide 18 créditos, mezclando las cinco líneas
  y pudiendo ver varias materias a la vez.

## Pruebas

`pytest` cubre la carga y el adaptador, el DAG y su rechazo cuando hay
un ciclo, los niveles, los tres indicadores (incluido el currículo de la
figura 1) y las tasas. `ruff check` cubre el estilo.
