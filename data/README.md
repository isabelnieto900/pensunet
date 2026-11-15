# Datos de Pensunet

En este directorio solo hay catálogo del pensum y tasas **agregadas por
asignatura**. No hay microdatos, códigos de estudiante ni historiales
individuales. Si más adelante hiciera falta un extracto con registros de
estudiante, debe vivir en `data/private/` (está en `.gitignore`) y no debe
commitearse.

Los tres CSV se copiaron tal como se entregaron para la etapa 1. No se
corrigió ninguna celda. Las inconsistencias de abajo quedan registradas
para revisarlas con el programa; el código no las “arregla” en silencio.

## Archivos

| Archivo | Papel |
| --- | --- |
| `reference/pensum_fisica.csv` | Asignaturas del plan: semestre, créditos, clasificación y slot. 95 filas, sin identificadores repetidos. |
| `reference/prerequisitos_fisica.csv` | Aristas de prerrequisito. 53 filas. `fl_debe_aprobado` indica si el prerrequisito es estricto. |
| `processed/tasas_aprobacion_fisica.csv` | Tasas agregadas por `id_asignatura`. 115 filas. |

## Origen y criterio de aprobación

- Programa: Física, Universidad Distrital Francisco José de Caldas.
- Ventana del histórico agregado: **2023-2 a 2025-2**. Fuera de esa
  ventana no hay información en estas tablas.
- Una inscripción cuenta como aprobada cuando en el histórico
  `fl_aprobada` es verdadero. La tasa de la tabla procesada es el
  cociente de la ecuación (7) de Molontay et al. (2020):

```text
tasa_aprobacion ≈ n_aprobados / n_inscritos
```

- `n_bajo` es verdadero si `n_inscritos < 5`. Se comprobó fila por fila:
  la bandera coincide con ese umbral y `tasa_aprobacion` coincide con el
  cociente redondeado a 4 decimales. No se borraron las materias con
  pocos inscritos; la bandera solo advierte que la estimación es inestable.

En el pensum, las materias con `n_bajo` son:

| id | Asignatura | Inscritos |
| --- | --- | --- |
| 9911 | Segunda lengua II - italiano | 3 |
| 9912 | Segunda lengua III - italiano | 3 |
| 25175 | Mecánica analítica | 4 |

## Cómo se relacionan las tablas

El pensum identifica cada fila con `id_asignatura`. La tabla de
prerrequisitos usa ese mismo identificador en `id_asignatura` (la
asignatura) y en `id_prerequisito`. Todos los identificadores de la
tabla de prerrequisitos existen en el pensum: no hay aristas colgando.

El pensum también incluye electivas intrínsecas y segundas lenguas. Varias
no tienen prerrequisito, y eso puede ser correcto (cátedras, primeras
lenguas, algunos seminarios). El detalle a revisar es otro: hay
obligatorias de semestres altos, y casi todas las lenguas distintas del
inglés, sin ninguna arista. No se inventaron esas aristas.

Los slots no son asignaturas que un estudiante curse todas a la vez:

- Segunda lengua I, II y III: cinco idiomas por nivel (`ds_grupo_slot`).
  Son alternativas.
- Línea de aplicación I a IV: hay una fila genérica
  (`LÍNEA DE APLICACIÓN …`) y, además, las electivas concretas del mismo
  slot.

Por eso la suma de `nu_creditos` de las 95 filas (271) **no** es el
número de créditos del grado. El grafo de la etapa 1 conserva cada fila
como un nodo distinto y no colapsa los slots.

## Reglas confirmadas del programa

Revisión de Isabel Nieto, 13 de noviembre de 2026. Describe cómo
funciona el plan, no lo que dicen los CSV. El grafo de esta etapa sigue
leyendo solo las aristas del archivo: estas reglas no se escribieron
dentro de las tablas.

### Obligatorias

- Mecánica cuántica avanzada (25145) sí exige cuántica 1. En este
  pensum esa materia es Introducción a la mecánica cuántica (25140,
  semestre 8). Parte de los estudiantes la vio en Licenciatura en
  Física, con otro código, así que la condición puede cumplirse fuera
  de este plan. La arista no está en el CSV y no se agregó. En las
  tasas hay un código ajeno al pensum, 24328 Mecánica cuántica I (2
  inscritos): es un candidato a ese código de licenciatura, sin
  confirmar.
- Trabajo de grado II (25154) exige Trabajo de grado I (25149). La
  excepción es la pasantía: en esa modalidad se pueden ver al tiempo.
  La pasantía no es una fila del pensum.
- Óptica general (25116) no tiene prerrequisito. Eso queda cerrado:
  la tabla está bien.
- Física moderna (25134) es, en teoría, prerrequisito de Física
  atómica y nuclear (25135). Por razones administrativas se ven en el
  mismo semestre; las dos están en el 7. No debe entrar como arista
  estricta, porque eso obligaría a cursar atómica un semestre después.
  Hoy la tabla no trae ni siquiera la relación débil.

### Segundas lenguas

La cadena I → II → III no está cargada en el sistema, pero es la regla
en los cinco idiomas. El estudiante cursa un solo idioma. También se
puede homologar por examen: la nota del examen queda como nota de la
materia, y el examen se puede presentar para cualquier nivel (por
ejemplo primero el I y después el III).

Para una simulación, el requisito son tres materias de 2 créditos de
un idioma, no las 15 filas del pensum. La homologación es otro camino.

### Simulación computacional de biosistemas

25176 solo se dictó una vez y hoy no está disponible. El prerrequisito
débil hacia Mecánica cuántica avanzada (25145, semestre 9) se puso
para que nadie pudiera inscribirla, no porque la materia lo necesite.
En el modelo es un cierre administrativo, no una arista curricular. La
tasa que aparece (5 inscritos, todos aprobados) corresponde a esa
única oferta.

### Línea de aplicación

Hay cinco líneas: astronomía, física computacional, física médica,
instrumentación y energías renovables. Se pueden mezclar y se pueden
ver varias al tiempo. El requisito es sumar 18 créditos de estas
electivas.

En el plan, los niveles I y III valen 4 créditos y los II y IV valen
5. Una línea completa suma 4 + 5 + 4 + 5 = 18, pero no hay que
permanecer en la misma línea.

El extracto no trae exactamente dos materias de 4 créditos y dos de 5
por línea:

- Física computacional tiene cuatro opciones de 4 créditos en el nivel
  I (minería de datos, procesamiento de imágenes, mecánica analítica
  y biosistemas) y una de 4 créditos en el nivel III.
- Física médica tiene dos opciones de 4 créditos en el nivel III
  (dosimetría e instrumentación biomédica).
- Instrumentación no tiene materia de nivel III en el CSV.

Las filas genéricas 25139, 25144, 25147 y 25152 («LÍNEA DE APLICACIÓN
… (A,B,C,D,E)») son el cupo del slot, no una electiva más. Contarlas
junto con las materias concretas duplicaría créditos.

### Electivas sin tasa

Varias electivas no tienen tasa porque la carrera es nueva, muy poca
gente las ha cursado y no hay profesor que las dicte: no están
disponibles. En esos casos la tasa ausente significa que la materia no
se ofrece. No se les debe asignar probabilidad 1. Trabajo de grado I
y II también están sin tasa, y esta explicación no los cubre.

## Inconsistencias que no se corrigieron

Lo que sigue describe los archivos tal como están. Donde el programa ya
aclaró el sentido, la sección anterior manda. Los CSV no se editaron.

### 1. Nombres distintos para el mismo identificador

En el pensum, `ds_nombre_asignatura` repite «ECUACIONES DIFERENCIALES»
para dos códigos. El nombre que los distingue está en `ds_nombre_pensum`
y en la tabla de prerrequisitos:

| id | `ds_nombre_asignatura` (pensum y tasas) | `ds_nombre_pensum` | Nombre en prerrequisitos |
| --- | --- | --- | --- |
| 4719 | ECUACIONES DIFERENCIALES | Ecuaciones Diferenciales I | ECUACIONES DIFERENCIALES I |
| 25122 | ECUACIONES DIFERENCIALES | Ecuaciones Diferenciales II | ECUACIONES DIFERENCIALES II |

La arista sí existe: 25122 exige 4719. El código usa el identificador,
no el nombre, para construir el grafo.

Aparte, el propio pensum escribe `SEGUNDA LENGUA II - INGLES` sin tilde,
mientras I y III llevan «INGLÉS». La tasa de 9902 usa la misma cadena
sin tilde. No es un cruce fallido; es un nombre heterogéneo.

### 2. Prerrequisito ubicado después de la asignatura

`25176` Simulación computacional de biosistemas está en el semestre 7 y
declara como prerrequisito `25145` Mecánica cuántica avanzada, del
semestre 9. `fl_debe_aprobado` es falso (prerrequisito débil: el artículo,
sección II.A, permite verlas en paralelo, pero no explica que el
prerrequisito esté dos semestres después).

El grafo por defecto **no** incluye esa arista, porque Molontay et al.
dejan fuera los prerrequisitos débiles. Aun así `construir_red` la
reporta en `inconsistencias`. Incluir las aristas débiles tampoco crea un
ciclo.

Las otras seis aristas débiles van de Física computacional I (25132,
semestre 6) a electivas del semestre 7: 25155, 25156, 25163, 25166,
25169 y 25175. Esas sí respetan el orden de semestres. También quedan
fuera del grafo estricto.

### 3. Cadenas de lengua incompletas

Solo el inglés tiene prerrequisitos: 9901 → 9902 → 9903. Francés, alemán,
italiano y portugués no tienen aristas entre niveles, así que en el grafo
un nivel II o III no exige el nivel I.

### 4. Obligatorias sin prerrequisito

54 asignaturas del pensum no aparecen como destino de ninguna arista.
Entre las obligatorias de tercer semestre en adelante están:

| Semestre | id | Asignatura |
| --- | --- | --- |
| 3 | 25115 | Historia y filosofía de la ciencia I |
| 4 | 25116 | Óptica general y laboratorio |
| 4 | 25120 | Epistemología de la física |
| 7 | 25135 | Física atómica y nuclear |
| 8 | 25141 | Estado sólido y dispositivos semiconductores |
| 8 | 25142 | Modelos y gestión I |
| 8 | 25143 | Seminario de investigación |
| 9 | 25145 | Mecánica cuántica avanzada |
| 9 | 25146 | Ciencias de los materiales |
| 9 | 25148 | Modelos y gestión II |
| 9 | 25149 | Trabajo de grado I |
| 10 | 25150 | Teoría general de la relatividad |
| 10 | 25151 | Nanotecnología y nuevos materiales |
| 10 | 25153 | Gestión tecnológica y compromiso social |
| 10 | 25154 | Trabajo de grado II |

Óptica (25116) y Física atómica y nuclear (25135) sí son prerrequisito de
otras, pero nadie las precede en la tabla. Trabajo de grado II no exige
trabajo de grado I. Mecánica cuántica avanzada no exige la introducción
del semestre 8. Puede que el plan real tenga esas condiciones y no hayan
llegado a la tabla. Pensunet no las agrega.

Con solo las aristas estrictas el camino más largo tiene 7 asignaturas
(6 aristas), por ejemplo Física I → … → Introducción a la mecánica
cuántica. El plan dura 10 semestres. No hay ciclos, ni con las aristas
débiles incluidas.

Consecuencia: el **nivel** (semestre mínimo impuesto por prerrequisitos)
de Relatividad o de Trabajo de grado II es 1, porque la tabla no las
conecta con nada. El semestre del pensum sigue siendo 10. Los indicadores
de posponimiento usan el mayor de los dos, no reemplazan el semestre del
plan por el nivel del grafo.

### 5. Tasas que no cruzan con el pensum

19 asignaturas del pensum no tienen fila en las tasas:

| Semestre | id | Asignatura | Clasificación |
| --- | --- | --- | --- |
| 1 | 9913 | Segunda lengua I - portugués | Obligatorio complementario |
| 2 | 9914 | Segunda lengua II - portugués | Obligatorio complementario |
| 3 | 9906 | Segunda lengua III - francés | Obligatorio complementario |
| 3 | 9915 | Segunda lengua III - portugués | Obligatorio complementario |
| 7 | 25163 | Procesamiento de imágenes | Electivo intrínseco |
| 7 | 25166 | Microcontroladores | Electivo intrínseco |
| 8 | 25167 | Electrónica digital | Electivo intrínseco |
| 8 | 25170 | Energía eólica y aerogeneradores | Electivo intrínseco |
| 9 | 25147 | Línea de aplicación III (A,B,C,D,E) | Electivo intrínseco |
| 9 | 25149 | Trabajo de grado I | Obligatorio |
| 9 | 25172 | Dosimetría de radiaciones | Electivo intrínseco |
| 9 | 25173 | Instrumentación biomédica | Electivo intrínseco |
| 9 | 25174 | Bioenergía | Electivo intrínseco |
| 10 | 25152 | Línea de aplicación IV (A,B,C,D,E) | Electivo intrínseco |
| 10 | 25154 | Trabajo de grado II | Obligatorio |
| 10 | 25162 | Cosmología | Electivo intrínseco |
| 10 | 25165 | Protección radiológica | Electivo intrínseco |
| 10 | 25168 | Comunicaciones y redes industriales | Electivo intrínseco |
| 10 | 25171 | Hidrógeno y celdas de combustible | Electivo intrínseco |

Trabajo de grado I y II, obligatorios, no tienen tasa en esta ventana.
En la etapa 3 no debe asumirse en silencio la convención del artículo de
poner probabilidad 1 a las electivas: aquí faltan también obligatorias.

39 filas de tasas no están en el pensum vigente. Son asignaturas que
aparecen en el histórico de Física (otros planes, electivas de otros
programas o códigos antiguos), no nodos de esta red. Se conservan en el
CSV procesado y no se agregan al grafo. Entre ellas hay códigos con muy
pocos inscritos (varias con `n_inscritos` 1) y también materias con más
masa, por ejemplo Cálculo diferencial (id 1, 14 inscritos), Sucesiones y
series numéricas (4949, 34), Cátedra de contexto (25246, 22) y
Epistemología de la física I (4728, 22), que no es la epistemología
25120 del pensum actual.

## Qué usa el código

`LectorCSV` lee los tres archivos y `AdaptadorUD` renombra las columnas
al modelo interno. `construir_red` arma el DAG solo con
`fl_debe_aprobado = True`. Las tasas se consultan por `id_asignatura`;
si el identificador no está, la probabilidad estimada queda ausente.
