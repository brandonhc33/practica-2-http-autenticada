"""Los comandos distinguen preparación gratuita, consentimiento y evidencia de una corrida."""

import io
import json
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage

from scripts import evaluacion_recuperacion, indexar_corpus, registro_rag
from scripts.rag_comun import exigir_consumo
from tests.rag.soporte import PruebaRAG


class TestComandosRAG(PruebaRAG):
    def setUp(self):
        super().setUp()
        self.enterContext(redirect_stdout(io.StringIO()))
        self.enterContext(redirect_stderr(io.StringIO()))

    def test_comparar_no_crea_modelos_ni_requiere_clave(self):
        ruta = Path(self.temporal) / "comparacion.json"
        with patch("scripts.indexar_corpus.crear_embeddings") as crear:
            self.assertEqual(indexar_corpus.main(["--comparar", "--salida", str(ruta)]), 0)
        crear.assert_not_called()
        self.assertEqual(len(json.loads(ruta.read_text())), 4)

    def test_verificar_y_reutilizar_no_requieren_embeddings(self):
        with patch("scripts.indexar_corpus.crear_embeddings") as crear:
            self.assertEqual(indexar_corpus.main(["--verificar", "--directorio", str(self.ruta)]), 0)
        crear.assert_not_called()

    def test_sin_confirmar_o_sin_clave_no_hace_llamadas(self):
        with self.assertRaisesRegex(ValueError, "confirmar-consumo"):
            exigir_consumo(False)
        with patch.dict(os.environ, {}, clear=True), patch("scripts.rag_comun.load_dotenv"):
            with self.assertRaisesRegex(ValueError, "Falta GEMINI_API_KEY"):
                exigir_consumo(True)

    def test_indexacion_sin_consentimiento_no_crea_indice(self):
        ruta = Path(self.temporal) / "sin-consentimiento"
        with patch("scripts.indexar_corpus.crear_embeddings") as crear:
            with self.assertRaises(SystemExit) as error:
                indexar_corpus.main(["--directorio", str(ruta)])
        self.assertEqual(error.exception.code, 1)
        crear.assert_not_called()
        self.assertFalse(ruta.exists())

    def preparar_mocks_registro(self, *, fallo=False):
        modulo = "scripts.registro_rag"
        self.enterContext(patch(f"{modulo}.exigir_embeddings_reales"))
        self.enterContext(patch(f"{modulo}.exigir_consumo"))
        self.enterContext(patch(f"{modulo}.crear_embeddings", return_value=self.embeddings))
        casos = [
            {"pregunta": f"Pregunta de prueba {i}", "ids_relevantes": []} for i in range(10)
        ]
        self.enterContext(patch(f"{modulo}.cargar_casos", return_value=casos))
        modelo = Mock()
        respuesta = AIMessage(
            content="Dato de prueba [1].",
            usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110},
        )
        modelo.invoke.side_effect = [respuesta, TimeoutError] if fallo else None
        modelo.invoke.return_value = respuesta
        self.enterContext(patch(f"{modulo}.crear_modelo", return_value=modelo))
        return modelo

    def test_actividad_28_escribe_cuatro_lineas_con_tres_preguntas_y_k_3_6(self):
        modelo = self.preparar_mocks_registro()
        ruta = Path(self.temporal) / "actividad.jsonl"
        codigo = registro_rag.main([
            "--actividad-28", "--directorio", str(self.ruta),
            "--salida", str(ruta), "--confirmar-consumo",
        ])
        registros = [json.loads(linea) for linea in ruta.read_text().splitlines()]
        self.assertEqual(codigo, 0)
        self.assertEqual(len(registros), 4)
        self.assertEqual(len({r["pregunta"] for r in registros}), 3)
        self.assertEqual([r["k"] for r in registros], [3, 3, 3, 6])
        self.assertEqual(registros[0]["pregunta"], registros[-1]["pregunta"])
        self.assertEqual(modelo.invoke.call_count, 4)
        self.assertEqual(self.embeddings.consultas, 4)

    def test_fallo_de_segunda_corrida_conserva_primera_y_no_sigue_gastando(self):
        modelo = self.preparar_mocks_registro(fallo=True)
        ruta = Path(self.temporal) / "fallo.jsonl"
        codigo = registro_rag.main([
            "--actividad-28", "--directorio", str(self.ruta),
            "--salida", str(ruta), "--confirmar-consumo",
        ])
        registros = [json.loads(linea) for linea in ruta.read_text().splitlines()]
        self.assertEqual(codigo, 1)
        self.assertEqual([r["estado"] for r in registros], ["ok", "error"])
        self.assertEqual(registros[1]["tipo_error"], "TimeoutError")
        self.assertEqual(modelo.invoke.call_count, 2)

    def test_archivo_existente_se_conserva_y_no_inicia_modelos(self):
        self.preparar_mocks_registro()
        ruta = Path(self.temporal) / "existente.jsonl"
        ruta.write_text("Evidencia anterior\n")
        with patch("scripts.registro_rag.crear_modelo") as crear:
            with self.assertRaises(SystemExit):
                registro_rag.main([
                    "Pregunta", "--directorio", str(self.ruta),
                    "--salida", str(ruta), "--confirmar-consumo",
                ])
        self.assertEqual(ruta.read_text(), "Evidencia anterior\n")
        crear.assert_not_called()
        self.assertEqual(self.embeddings.consultas, 0)

    def test_cli_rechaza_indice_falso_sin_permitir_fallback(self):
        with patch("scripts.registro_rag.crear_embeddings") as crear:
            with self.assertRaises(SystemExit):
                registro_rag.main([
                    "Pregunta", "--directorio", str(self.ruta),
                    "--salida", str(Path(self.temporal) / "no.jsonl"), "--confirmar-consumo",
                ])
        crear.assert_not_called()

    def test_evaluacion_guarda_txt_y_json_con_configuracion(self):
        modulo = "scripts.evaluacion_recuperacion"
        self.enterContext(patch(f"{modulo}.exigir_embeddings_reales"))
        self.enterContext(patch(f"{modulo}.exigir_consumo"))
        self.enterContext(patch(f"{modulo}.crear_embeddings", return_value=self.embeddings))
        casos = [{"pregunta": "Pregunta de prueba", "ids_relevantes": ["tienda-0-c000"]}]
        self.enterContext(patch(f"{modulo}.cargar_casos", return_value=casos))
        ruta = Path(self.temporal) / "resultados.txt"
        codigo = evaluacion_recuperacion.main([
            "--directorio", str(self.ruta), "--salida", str(ruta),
            "--repeticiones", "2", "--confirmar-consumo",
        ])
        self.assertEqual(codigo, 0)
        datos = json.loads(ruta.with_suffix(".json").read_text())
        self.assertTrue(datos["repeticiones_identicas"])
        self.assertEqual(datos["configuracion_indice"], self.manifiesto["configuracion"])
        self.assertIn("Promedios:", ruta.read_text())
        self.assertEqual(self.embeddings.consultas, 2)
