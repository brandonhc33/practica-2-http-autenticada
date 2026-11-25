"""El ensayo sin clave recupera por palabras y cita, pero no pretende entender."""

import unittest

from src.gobernanza.prompts import prompt_activo
from src.rag.simulado import (
    DIMENSIONES_LEXICO,
    EmbeddingsDePalabras,
    ModeloQueCita,
    palabras,
)


def coseno(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class TestSimulado(unittest.TestCase):
    def test_ignora_tildes_plurales_y_palabras_vacias(self):
        self.assertEqual(palabras("Los envases del Artículo"), palabras("envase articulo"))

    def test_textos_con_palabras_comunes_quedan_mas_cerca(self):
        e = EmbeddingsDePalabras()
        consulta = e.embed_query("metas de envases de vidrio")
        cerca, lejos = e.embed_documents(["La meta de vidrio para envases.", "Garantía en UTM."])
        self.assertGreater(coseno(consulta, cerca), coseno(consulta, lejos))
        self.assertEqual(len(consulta), DIMENSIONES_LEXICO)
        self.assertEqual(consulta, e.embed_query("metas de envases de vidrio"))

    def test_texto_sin_palabras_no_falla(self):
        self.assertAlmostEqual(sum(v * v for v in EmbeddingsDePalabras().embed_query("¿?")), 1.0)

    def test_modelo_cita_el_primer_fragmento(self):
        contexto = '[{"cita": 4, "texto": "Texto de prueba."}]'
        mensaje = ModeloQueCita().invoke(
            prompt_activo().plantilla().invoke({"pregunta": "x", "contexto": contexto})
        )
        self.assertEqual(mensaje.content, "Respuesta simulada: Texto de prueba. [4]")

    def test_modelo_rechaza_un_prompt_sin_contexto(self):
        with self.assertRaises(ValueError):
            ModeloQueCita().invoke("hola")
