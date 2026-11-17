# Manual de usuario

## Interfaz Streamlit

```bash
pip install -e ".[ui]"
python examples/ejecutar_interfaz.py
# o: python -m streamlit run src/pensunet/ui/app.py
```

En la barra lateral elige la carrera (Física, Química, Biología,
Matemáticas). Hay tres secciones:

1. **Red de prerrequisitos** — grafo interactivo con ajustes documentados.
2. **Indicadores** — bloqueo, posponimiento, intermediación, cuellos y
   camino más largo.
3. **Tiempo de grado** — Monte Carlo; edita tasas antes de simular.
   Trabajo de grado y materias sin histórico aparecen sin tasa: hay que
   completarlas en el editor (no se usa 0 ni 1 por defecto).

También puedes cargar desde Python o el CLI
`examples/ejemplo_cargar_red.py --programa …` (ver `README.md`).
