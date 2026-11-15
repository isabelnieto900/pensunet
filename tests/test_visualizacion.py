"""Figura del DAG de análisis."""

from pensunet.dominio.visualizacion import dibujar_red


def test_dibujar_red_escribe_un_png(tmp_path, simulador):
    """Sección II.A: la figura se guarda sin abrir una ventana."""
    destino = tmp_path / "red.png"
    ruta = dibujar_red(simulador.red, ruta=destino, titulo="Prueba")
    assert ruta == destino
    assert destino.is_file()
    assert destino.stat().st_size > 0
