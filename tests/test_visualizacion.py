"""Figura PNG y vista HTML de la red."""

from pensunet.dominio.visualizacion import dibujar_red, exportar_red_html, html_de_la_red


def test_dibujar_red_escribe_un_png(tmp_path, simulador):
    """Sección II.A: la figura se guarda sin abrir una ventana."""
    destino = tmp_path / "red.png"
    ruta = dibujar_red(simulador.red, ruta=destino, titulo="Prueba")
    assert ruta == destino
    assert destino.is_file()
    assert destino.stat().st_size > 0


def test_exportar_red_html_incluye_nodos_y_aristas(tmp_path, simulador):
    """La página permite explorar prerrequisitos sin dependencias nuevas."""
    destino = tmp_path / "red.html"
    ruta = exportar_red_html(simulador.red, ruta=destino, titulo="Prueba HTML")
    assert ruta == destino
    texto = destino.read_text(encoding="utf-8")
    assert "25102" in texto
    assert "arista" in texto
    assert "seleccionar" in texto


def test_html_embebido_sin_titulo_de_pagina(simulador):
    """La versión embebida se integra en Streamlit sin título duplicado."""
    texto = html_de_la_red(simulador.red, titulo="Solo archivo", embebido=True)
    assert "pensunet-red" in texto and "embebido" in texto
    assert "#ffffff" in texto or "background:" in texto
    assert "<h1>Solo archivo</h1>" not in texto
    assert "<!DOCTYPE html>" in texto


def test_html_embebido_oscuro_usa_texto_claro(simulador):
    """En tema oscuro el fragmento no deja letras negras sobre fondo oscuro."""
    texto = html_de_la_red(
        simulador.red,
        titulo="Oscuro",
        embebido=True,
        oscuro=True,
    )
    assert "embebido" in texto and "oscuro" in texto
    assert "#e8eeeb" in texto
    assert "#1c2421" in texto


def test_html_embebido_incluye_zoom_cuellos_y_camino(simulador):
    """Vista compacta con zoom, cuellos y camino más largo."""
    indicadores = simulador.indicadores()
    cuellos = indicadores.cuellos_de_botella
    camino = indicadores.camino_mas_largo
    assert camino
    texto = html_de_la_red(
        simulador.red,
        embebido=True,
        resaltar=cuellos,
        camino=camino,
        metricas={
            int(camino[0]): {
                "tasa": 0.9,
                "bloqueo": 3,
                "posponimiento": 0.5,
                "intermediacion": 0.1,
                "motivo_cuello": "prueba",
            }
        },
    )
    assert 'id="z-fit"' in texto
    assert "panel-lado" in texto
    assert "pointer-events: none" in texto
    if cuellos:
        assert "nodo cuello" in texto
        assert "Cuello de botella" in texto
    assert "Camino más largo" in texto
    assert "#c0392b" in texto
