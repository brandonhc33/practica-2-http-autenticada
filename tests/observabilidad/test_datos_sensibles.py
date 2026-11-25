"""Los datos reconocidos no llegan al proveedor ni a los archivos."""

import unittest
from typing import cast

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from scripts.logging_rag import LIMPIO, IndiceDePrueba
from src.gobernanza.prompts import prompt_activo
from src.observabilidad.datos_sensibles import detectar_datos_sensibles, ocultar_datos_sensibles
from src.rag.servicio import responder
from src.rag.simulado import ModeloQueCita


class EmbeddingsQueAnotan(Embeddings):
    def __init__(self):
        self.consultas: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        self.consultas.append(text)
        return [1.0]


class TestDatosSensibles(unittest.TestCase):
    def test_oculta_cada_tipo(self):
        casos = {
            "correo": "ana.perez@example.com", "rut": "12.345.678-5", "telefono": "+56 9 1234 5678",
            "clave": "AIza" + "x" * 30,
        }
        for tipo, valor in casos.items():
            with self.subTest(tipo=tipo):
                texto, total = ocultar_datos_sensibles(f"Dato {valor} aquí")
                self.assertEqual((texto, total), (f"Dato [{tipo} oculto] aquí", 1))
                self.assertEqual(detectar_datos_sensibles(texto), {})

    def test_no_altera_una_pregunta_normativa(self):
        pregunta = "¿Qué dice el artículo 21 del DS 12/2020 sobre 300 kilogramos y 1.000 UTM?"
        self.assertEqual(ocultar_datos_sensibles(pregunta), (pregunta, 0))

    def test_el_proveedor_recibe_la_pregunta_sin_el_dato(self):
        embeddings = EmbeddingsQueAnotan()
        r = responder(
            "¿Quién se inscribe? ana.perez@example.com", cast(Chroma, IndiceDePrueba([LIMPIO])),
            embeddings, ModeloQueCita(), "simulado", prompt_activo(),
        )
        self.assertEqual(r["estado"], "ok")
        self.assertEqual(embeddings.consultas, ["¿Quién se inscribe? [correo oculto]"])
        self.assertEqual(r["auditoria"][0]["datos_ocultados"], 1)
