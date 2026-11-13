"""Tasas agregadas de la ecuación (7) y huecos respecto del pensum."""


def test_la_tasa_es_el_cociente_de_aprobados_sobre_inscritos(simulador):
    """Ecuación (7). No se reemplaza la tasa publicada por otro redondeo."""
    tasas = simulador.tasas
    assert len(tasas) == 115
    assert set(tasas.columns) >= {
        "id_asignatura",
        "nombre",
        "n_inscritos",
        "n_aprobados",
        "tasa_aprobacion",
        "n_bajo",
    }
    for fila in tasas.to_dict(orient="records"):
        assert bool(fila["n_bajo"]) is (fila["n_inscritos"] < 5)
        if fila["n_inscritos"]:
            cociente = fila["n_aprobados"] / fila["n_inscritos"]
            assert abs(cociente - fila["tasa_aprobacion"]) < 5e-5

    matematica = tasas.loc[tasas["id_asignatura"] == 25103].iloc[0]
    assert matematica["n_inscritos"] == 406
    assert matematica["n_aprobados"] == 152
    assert matematica["tasa_aprobacion"] == 0.3744
    assert bool(matematica["n_bajo"]) is False
    assert simulador.tasa_de(25103) == 0.3744


def test_los_cruces_fallidos_se_conservan(simulador):
    """Ecuación (7): sin fila no hay probabilidad, y lo ajeno al pensum no entra al grafo."""
    assert simulador.tasa_de(25149) is None
    assert simulador.tasa_de(25154) is None
    assert simulador.tasa_de(25175) == 1.0
    fila_baja = simulador.tasas.loc[simulador.tasas["id_asignatura"] == 25175].iloc[0]
    assert fila_baja["n_inscritos"] == 4
    assert bool(fila_baja["n_bajo"]) is True

    ids_pensum = set(simulador.pensum["id_asignatura"])
    ids_tasas = set(simulador.tasas["id_asignatura"])
    assert 25149 in ids_pensum - ids_tasas
    assert 1 in ids_tasas - ids_pensum
    assert 1 not in simulador.red.grafo
    fisica = simulador.tasas.loc[simulador.tasas["id_asignatura"] == 25102].iloc[0]
    assert bool(fisica["n_bajo"]) is False
    assert fisica["tasa_aprobacion"] == 0.5013
