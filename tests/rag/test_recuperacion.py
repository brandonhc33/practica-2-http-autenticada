"""El prompt y la instrumentación usan el resultado recuperado, sin afirmar veracidad."""

from decimal import Decimal
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage

from src.rag.recuperacion import PROMPT_RAG, formatear_contexto, revisar_citas
from src.rag.registro import registrar_consulta
from tests.rag.soporte import PruebaRAG

MODELO = "gemini-3.5-flash-lite"
USO = {"input_tokens": 1000, "output_tokens": 200, "total_tokens": 1200}


class TestRecuperacion(PruebaRAG):
    def setUp(self):
        super().setUp()
        self.modelo = Mock()
        self.modelo.invoke.return_value = AIMessage(
            content="Respuesta de prueba [1].", usage_metadata=USO,
        )

    def consultar(self, pregunta="¿Qué dice la política?", k=3):
        return registrar_consulta(
            pregunta, self.indice, self.manifiesto, self.embeddings, self.modelo, MODELO, k,
            tipo_ejecucion="prueba",
        )

    def test_un_embedding_una_generacion_y_tres_etapas(self):
        registro = self.consultar()
        self.assertEqual(registro["estado"], "ok")
        self.assertEqual(registro["tipo_ejecucion"], "prueba")
        self.assertEqual(self.embeddings.consultas, 1)
        self.assertEqual(self.embeddings.documentos, 1)
        self.modelo.invoke.assert_called_once()
        self.assertEqual(len(registro["fuentes"]), 3)
        self.assertTrue(all(t >= 0 for t in registro["tiempos_ms"].values()))
        self.assertGreaterEqual(registro["tiempo_total_ms"], registro["tiempo_etapas_ms"])
        self.assertEqual(registro["tokens"], USO)
        self.assertEqual(Decimal(registro["costo_generacion_usd"]), Decimal("0.0008"))
        self.assertIsNone(registro["costo_total_usd"])
        self.assertIsNone(registro["embeddings"]["tokens_reales"])
        self.assertIsNone(registro["embeddings"]["costo_real_usd"])

    def test_contexto_y_pregunta_llegan_al_modelo_sin_cambiar(self):
        pregunta = "¿Quién paga?\nNo cambies esta pregunta."
        registro = self.consultar(pregunta)
        prompt = self.modelo.invoke.call_args.args[0].to_messages()
        self.assertIn("Usa SOLO", prompt[0].content)
        self.assertIn("no hay información suficiente", prompt[0].content)
        self.assertIn(pregunta, prompt[1].content)
        for fuente in registro["fuentes"].values():
            self.assertIn(fuente["id_chunk"], prompt[1].content)
        self.assertTrue(registro["revision_citas"]["referencias_validas"])

    def test_citas_inexistentes_y_ausencia_se_avisan_sin_inventar_fuentes(self):
        fuentes = {1: {"id_chunk": "x"}}
        revision = revisar_citas("Dato [1]. Otro [99]. Repite [1].", fuentes)
        self.assertEqual(revision["numeros_citados"], [1, 99])
        self.assertEqual(revision["numeros_inexistentes"], [99])
        self.assertFalse(revision["referencias_validas"])
        self.assertTrue(revisar_citas("Información insuficiente.", fuentes)["sin_citas"])
        self.assertEqual(formatear_contexto([]), ("[]", {}))
        self.assertIn("cita", str(PROMPT_RAG))

    def test_sin_metadatos_de_uso_no_es_costo_cero(self):
        self.modelo.invoke.return_value = AIMessage(content="Dato [1].")
        registro = self.consultar()
        self.assertEqual(registro["estado"], "ok")
        self.assertIsNone(registro["tokens"])
        self.assertIsNone(registro["costo_conocido_usd"])
        self.assertIsNone(registro["costo_total_usd"])

    def test_error_de_embeddings_detiene_antes_de_busqueda_y_generacion(self):
        with patch.object(self.embeddings, "embed_query", side_effect=TimeoutError):
            registro = self.consultar()
        self.assertEqual(registro["estado"], "error")
        self.assertEqual(registro["etapa_error"], "embed_query")
        self.assertEqual(registro["tipo_error"], "TimeoutError")
        self.assertIsNone(registro["tiempos_ms"]["busqueda_vectorial"])
        self.assertIsNone(registro["tiempos_ms"]["generacion"])
        self.modelo.invoke.assert_not_called()

    def test_error_de_generacion_conserva_fuentes_y_tiempo_sin_reintentar(self):
        self.modelo.invoke.side_effect = RuntimeError("Dato privado que no debe persistir")
        registro = self.consultar()
        self.assertEqual(registro["etapa_error"], "generacion")
        self.assertEqual(len(registro["fuentes"]), 3)
        self.assertNotIn("Dato privado", str(registro))
        self.modelo.invoke.assert_called_once()
        self.assertIsNone(registro["tokens"])

    def test_respuesta_vacia_conserva_su_consumo(self):
        self.modelo.invoke.return_value = AIMessage(content="", usage_metadata=USO)
        registro = self.consultar()
        self.assertEqual(registro["estado"], "error")
        self.assertEqual(registro["tokens"], USO)
        self.assertEqual(registro["costo_conocido_usd"], "0.0008")

    def test_k_mayor_que_corpus_reporta_fuentes_reales_no_inventadas(self):
        registro = self.consultar(k=6)
        self.assertEqual(len(registro["fuentes"]), 5)
        self.assertEqual(registro["k"], 6)

    def test_entrada_invalida_no_consume(self):
        for pregunta, k in (("", 3), (" ", 3), ("hola", 0), ("hola", 21)):
            with self.subTest(pregunta=pregunta, k=k), self.assertRaises(ValueError):
                self.consultar(pregunta, k)
        self.assertEqual(self.embeddings.consultas, 0)
        self.modelo.invoke.assert_not_called()
