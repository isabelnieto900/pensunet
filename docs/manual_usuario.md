# Manual de usuario

## Interfaz Streamlit

Desde la raíz del repositorio:

```bash
pip install -e ".[ui]"
streamlit run src/pensunet/ui/app.py
```

O bien `python examples/ejecutar_interfaz.py`.

En la barra lateral eliges la sección:

1. **Red de prerrequisitos** — plan completo encajado; zoom con rueda o
   botones y arrastre sobre el fondo para recorrer (clic en una materia
   la selecciona; clic en el fondo deselecciona).
2. **Indicadores** — cuellos de botella (naranja) y camino más largo
   (rojo) con interruptores; al hacer clic, el panel muestra tasa y
   métricas.
3. **Tiempo de grado** — editas tasas, n, semilla y el tope; **Simular**
   aplica todo de una vez (no hace falta cambiar la semilla para que
   cuenten las tasas nuevas). Si alguien no se gradúa a tiempo, la
   trayectoria se censura en el tope y se reporta cuántos censurados
   hubo. Los CSV no se modifican.

Siempre se aplican las reglas de Física (exclusiones, aristas confirmadas,
tasa 1 en trabajo de grado). El cupo de línea es 18 créditos; una electiva
reprobada no se repite.

## Uso desde Python

Resumido en el `README.md` y en `examples/ejemplo_cargar_red.py`.
La fachada es `SimuladorPensum`: `cargar`, `indicadores`, `simular`.
