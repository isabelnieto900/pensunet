"""Payload JSON de la red curricular (visualizador D3)."""

from __future__ import annotations

import json

import networkx as nx
import pandas as pd

from pensunet.dominio.red import construir_red
from pensunet.dominio.visualizacion import payload_de_la_red


def test_payload_incluye_todos_los_nodos_y_aristas(simulador):
    payload = payload_de_la_red(simulador.red)
    ids = {n["id"] for n in payload["nodos"]}
    assert ids == {int(n) for n in simulador.red.grafo.nodes}
    aristas = {(a["source"], a["target"]) for a in payload["aristas"]}
    assert aristas == {(int(u), int(v)) for u, v in simulador.red.grafo.edges}


def test_payload_nodo_tiene_semestre_xy_y_cadenas(simulador):
    payload = payload_de_la_red(simulador.red)
    grafo = simulador.red.grafo
    for nodo in payload["nodos"]:
        assert "semestre" in nodo and nodo["semestre"] >= 0
        assert isinstance(nodo["x"], float)
        assert isinstance(nodo["y"], float)
        codigo = nodo["id"]
        assert set(nodo["ancestros"]) == {int(a) for a in nx.ancestors(grafo, codigo)}
        assert set(nodo["descendientes"]) == {
            int(d) for d in nx.descendants(grafo, codigo)
        }
        assert set(nodo["previos"]) == {int(p) for p in grafo.predecessors(codigo)}
        assert set(nodo["siguientes"]) == {int(s) for s in grafo.successors(codigo)}


def test_payload_metricas_viajan_si_se_pasan(simulador):
    codigo = int(next(iter(simulador.red.grafo)))
    payload = payload_de_la_red(
        simulador.red,
        metricas={
            codigo: {
                "tasa": 0.91,
                "bloqueo": 4,
                "retraso": 2,
                "complejidad": 6,
                "motivo_cuello": "prueba",
            }
        },
        resaltar=frozenset({codigo}),
    )
    nodo = next(n for n in payload["nodos"] if n["id"] == codigo)
    assert nodo["tasa"] == 0.91
    assert nodo["bloqueo"] == 4
    assert nodo["retraso"] == 2
    assert nodo["complejidad"] == 6
    assert nodo["motivo_cuello"] == "prueba"
    assert nodo["cuello"] is True


def test_payload_aristas_debiles_de_fisica():
    """Con solo_estrictos=False, las dos aristas débiles de Física quedan tipadas."""
    pensum = pd.read_csv("data/reference/pensum_fisica.csv")
    prereq = pd.read_csv("data/reference/prerequisitos_fisica.csv")
    # Normalizar columnas al esquema de construir_red.
    pensum = pensum.rename(
        columns={
            "ds_nombre_asignatura": "nombre",
            "nu_periodo_formacion": "semestre",
            "nu_creditos": "creditos",
            "ds_clasificacion": "clasificacion",
        }
    )
    prereq = prereq.rename(
        columns={
            "ds_nombre_asignatura": "nombre",
            "ds_nombre_prerequisito": "nombre_prerequisito",
            "nu_orden": "orden",
            "fl_debe_aprobado": "debe_aprobado",
        }
    )
    red = construir_red(pensum, prereq, solo_prerrequisitos_estrictos=False)
    payload = payload_de_la_red(red)
    debiles = {
        (a["source"], a["target"]) for a in payload["aristas"] if a["tipo"] == "debil"
    }
    assert (25132, 25139) in debiles
    assert (25145, 25176) in debiles


def test_payload_es_json_serializable(simulador):
    payload = payload_de_la_red(simulador.red)
    texto = json.dumps(payload, ensure_ascii=False)
    assert '"nodos"' in texto
    assert '"aristas"' in texto
    recuperado = json.loads(texto)
    assert len(recuperado["nodos"]) == len(payload["nodos"])
