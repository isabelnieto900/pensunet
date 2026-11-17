"""Tasas agregadas de la ecuación (7) y huecos respecto del pensum."""


def test_la_tasa_es_el_cociente_de_aprobados_sobre_inscritos(simulador):
    """Ecuación (7). No se reemplaza la tasa publicada por otro redondeo."""
    tasas = simulador.tasas
    # 115 del histórico + trabajo de grado I y II por juicio experto.
    assert len(tasas) == 117
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


def test_trabajo_de_grado_tiene_tasa_uno_por_juicio_experto(simulador):
    """TG I/II: p_i = 1 (Física); no es la convención BME de electivas."""
    assert simulador.tasa_de(25149) == 1.0
    assert simulador.tasa_de(25154) == 1.0
    for codigo in (25149, 25154):
        fila = simulador.tasas.loc[simulador.tasas["id_asignatura"] == codigo].iloc[0]
        assert fila["n_inscritos"] == 0
        assert fila["tasa_aprobacion"] == 1.0
        assert bool(fila["n_bajo"]) is True
    assert any("juicio experto" in nota for nota in simulador.red.reglas_aplicadas)


def test_los_cruces_fallidos_se_conservan(simulador):
    """Ecuación (7): sin fila no hay probabilidad, y lo ajeno al pensum no entra al grafo."""
    assert simulador.tasa_de(25175) == 1.0
    fila_baja = simulador.tasas.loc[simulador.tasas["id_asignatura"] == 25175].iloc[0]
    assert fila_baja["n_inscritos"] == 4
    assert bool(fila_baja["n_bajo"]) is True

    ids_pensum = set(simulador.pensum["id_asignatura"])
    ids_tasas = set(simulador.tasas["id_asignatura"])
    assert 25149 in ids_pensum & ids_tasas
    assert 1 in ids_tasas - ids_pensum
    assert 1 not in simulador.red.grafo
    fisica = simulador.tasas.loc[simulador.tasas["id_asignatura"] == 25102].iloc[0]
    assert bool(fisica["n_bajo"]) is False
    assert fisica["tasa_aprobacion"] == 0.5013


def test_sin_reglas_el_trabajo_de_grado_sigue_sin_tasa(simulador_crudo):
    """El CSV crudo no inventa p_i; solo ReglasFisica añade el juicio."""
    assert simulador_crudo.tasa_de(25149) is None
    assert simulador_crudo.tasa_de(25154) is None
