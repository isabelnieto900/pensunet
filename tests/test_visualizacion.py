"""Figura PNG y vista HTML de la red."""

from pensunet.dominio.visualizacion import dibujar_red, exportar_red_html


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
