# Datos de Pensunet

En este directorio solo hay catálogo del pensum y tasas **agregadas por
asignatura**. No hay microdatos, códigos de estudiante ni historiales
individuales. Si más adelante hiciera falta un extracto con registros de
estudiante, debe vivir en `data/private/` (está en `.gitignore`) y no debe
commitearse.

Los CSV de pensum y prerrequisitos salen del parser determinista de Cóndor
(`scripts/condor_a_pensunet.py`) a partir de las vistas del SGA. **No se
corrige ninguna celda del SGA en silencio.** Las correcciones viven en
`reference/ajustes_prerrequisitos.csv` y se aplican en código al cargar.

## Archivos

| Archivo | Papel |
| --- | --- |
| `reference/pensum_<programa>.csv` | Asignaturas del plan (sin filas de cupo sin `id_asignatura`). |
| `reference/prerequisitos_<programa>.csv` | Aristas del SGA (`fl_debe_aprobado` = estricto/débil). |
| `processed/tasas_aprobacion_<programa>.csv` | Tasas agregadas 2023-2 a 2025-2 (esquema Pensunet). |
| `reference/ajustes_prerrequisitos.csv` | Correcciones/documentación con justificación; aplicadas por código. |
| `reference/cupos_sin_asignatura.csv` | Cupos del plan sin código (p. ej. Electiva VI/VII de Química) para la suma de créditos. |
| `reference/trabajo_de_grado.csv` | Códigos de TG por carrera; tasa vacía marcada como juicio experto. |

Programas: `fisica` (plan 327), `quimica` (328), `biologia` (329),
`matematicas` (298).

## Origen

- Vistas del SGA «Plan de estudios» y «Requisitos del Plan de Estudios»,
  guardadas desde Chrome y parseadas de forma determinista en el repo
  privado OATI (`data/reference/condor/<programa>_<plan>/`).
- Tasas curadas en OATI (`data/curated/tasas/`); la de Física es idéntica
  a la que ya estaba en Pensunet.
- Ventana del histórico agregado: **2023-2 a 2025-2**. El periodo 2026-1
  está incompleto en la base y **no entra**.
- Criterio de aprobación: `fl_aprobada` verdadero. La tasa es el cociente
  de la ecuación (7) de Molontay et al. (2020), *IEEE TLT* 13(3):491–501,
  DOI 10.1109/TLT.2020.2981331:

```text
tasa_aprobacion ≈ n_aprobados / n_inscritos
```

- `n_bajo` es verdadero si `n_inscritos < 5`.

Conversión: `nombre` → `ds_nombre_asignatura` y `ds_nombre_pensum`;
`periodo` → `nu_periodo_formacion`; `creditos` → `nu_creditos`;
`clasificacion` → `ds_clasificacion`; `slot` → `ds_grupo_slot` y
`ds_bloque_electivo`. `ds_linea_tematica` solo se conserva en Física
desde el pensum previo (por `id_asignatura`); en las demás queda vacía.
Se quitan las filas de cupo sin `id_asignatura`.

## Conteos tras la conversión (extracto crudo)

| Programa | Pensum | Prerrequisitos | Tasas | Créditos del plan |
| --- | ---: | ---: | ---: | ---: |
| Física | 91 | 48 | 115 | 145 |
| Química | 86 | 39 | 126 | 145 |
| Biología | 88 | 22 | 174 | 144 |
| Matemáticas | 57 | 21 | 90 | 140 |

Los créditos cuentan cada cupo una vez (opciones de lengua/electiva no
se suman). Química aporta 4 créditos extra desde
`cupos_sin_asignatura.csv` (Electiva VI y VII sin opciones con código).

## Ajustes documentados (`ajustes_prerrequisitos.csv`)

Se aplican con `SimuladorPensum.cargar(aplicar_ajustes_documentados=True)`
(por defecto si el simulador conoce el programa).

### Física

- **Agregar** 25140 → 25145 (Mecánica Cuántica Avanzada), estricta. No
  está en el SGA; confirmada por el programa; cumplida por el 89,6 %
  (43/48) en el histórico.
- **Excluir nodo** 25176 (Simulación computacional de biosistemas):
  materia discontinuada; el prerrequisito débil desde 25145 es un cierre
  administrativo (0/5 lo cumplen) y va contra el orden de semestres.
- **Excluir arista** 25132 → 25139: el cupo genérico Línea de Aplicación I
  no tiene `id_asignatura` en Cóndor; evita un nodo huérfano.
- **Agregar** 25149 → 25154 (TG I → TG II), estricta, **salvo modalidad
  pasantía** (pueden cursarse a la vez). La excepción queda documentada;
  no se modela como arista débil.

Con ajustes: **90 nodos, 48 aristas estrictas**, sin inconsistencias
residuales en el grafo.

### Química

- Se **mantienen** las aristas 25233 → 6079 y 25224 → 25226 aunque
  invierten semestres en el plan; se cumplen en la práctica (98–100 %).
  Quedan anotadas como `documentar` y siguen apareciendo en
  `red.inconsistencias`.
- **No** se agrega TG I → TG II: el SGA pide Profundización I (25234) a
  ambos; 13/23 los cursan a la vez.

### Biología y Matemáticas

- **No** se agregan los candidatos faltantes de la auditoría (n pequeño
  en semestres altos). Quedan pendientes de confirmar con el programa;
  el detalle está en la auditoría OATI
  (`docs/auditoria_prerrequisitos.md`).

## Trabajo de Grado (tasas)

Códigos: Física 25149/25154; Química 25149/25242; Biología 22540/25345;
Matemáticas 19924/19925.

La nota de TG **no** está en `fact_rendimiento_academico` (todas 0,
ningún aprobado en la ventana). Las tasas de TG **no** entran al CSV
procesado: quedan vacías y marcadas como juicio experto en
`trabajo_de_grado.csv`. **Nunca** se usa 0 ni 1 por defecto.

## Cómo cargar

```python
from pensunet import SimuladorPensum

simulador = SimuladorPensum.desde_programa("quimica")
simulador.cargar()  # aplica ajustes documentados
# extracto crudo del SGA:
# simulador.cargar(aplicar_ajustes_documentados=False)
```

CLI: `python examples/ejemplo_cargar_red.py --programa fisica`.
