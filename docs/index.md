# Pensunet

Simulador de la red de prerrequisitos de los pensum de la Facultad de
Ciencias Matemáticas y Naturales (Física, Química, Biología y
Matemáticas) de la Universidad Distrital Francisco José de Caldas.

Pensunet representa el pensum como un grafo dirigido de prerrequisitos,
calcula los indicadores de Molontay et al. (2020) y la complejidad
curricular de Curricular Analytics, y estima el tiempo de grado con un
Monte Carlo sobre tasas de aprobación agregadas.

> Molontay, R., Horváth, N., Bergmann, J., Szekrényes, D. y Szabó, M. (2020).
> Characterizing Curriculum Prerequisite Networks by a Student Flow Approach.
> *IEEE Transactions on Learning Technologies*, 13(3), 491–501.
> DOI: [10.1109/TLT.2020.2981331](https://doi.org/10.1109/TLT.2020.2981331).

## Uso rápido

```bash
pip install -e ".[ui]"
streamlit run src/pensunet/ui/app.py
```

```python
from pensunet import SimuladorPensum
from pensunet.dominio.escenario import Escenario

simulador = SimuladorPensum.desde_programa("fisica")
simulador.cargar()
resultado = simulador.simular(Escenario(n_estudiantes=1000, semilla=1))
print(resultado.media)
```

```{toctree}
:maxdepth: 2
:caption: Contenido

manual_usuario
manual_tecnico
api
```
