"""Persistencia real de Chroma sin generar embeddings al recargar o repetir."""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.rag.indice import (
    MANIFIESTO,
    abrir_indice,
    crear_embeddings,
    exigir_embeddings_reales,
    indexar_corpus,
    preparar_indice,
)
from tests.rag.soporte import PruebaRAG


class TestIndice(PruebaRAG):
    def test_conector_real_usa_tareas_compatibles_y_timeout_sin_llamar_api(self):
        modulo = GoogleGenerativeAIEmbeddings.__module__
        with patch.dict(os.environ, {"GEMINI_API_KEY": "clave-ficticia"}, clear=True):
            with patch(f"{modulo}.Client") as cliente:
                vector = [0.5] * 3072
                cliente.return_value.models.embed_content.return_value = SimpleNamespace(
                    embeddings=[SimpleNamespace(values=vector)],
                )
                embeddings = crear_embeddings()
                self.assertEqual(embeddings.embed_documents(["documento"]), [vector])
                self.assertEqual(embeddings.embed_query("pregunta"), vector)
        opciones = cliente.call_args.kwargs["http_options"]
        self.assertEqual(opciones.client_args["timeout"], 30)
        llamadas = cliente.return_value.models.embed_content.call_args_list
        self.assertEqual(len(llamadas), 2)
        self.assertEqual(llamadas[0].kwargs["config"].task_type, "RETRIEVAL_DOCUMENT")
        self.assertEqual(llamadas[1].kwargs["config"].task_type, "RETRIEVAL_QUERY")
        self.assertTrue(all(c.kwargs["config"].output_dimensionality == 3072 for c in llamadas))

    def test_recarga_en_otro_proceso_sin_embedders_ni_red(self):
        codigo = """
import socket, sys
def impedir(*args, **kwargs):
    raise AssertionError("No debe llamar a la red al recargar.")
socket.socket.connect = impedir
socket.getaddrinfo = impedir
from pathlib import Path
from src.rag.indice import abrir_indice
indice, datos = abrir_indice(Path(sys.argv[1]))
assert len(indice.get()["ids"]) == 5
print(datos["huella_indice"])
"""
        resultado = subprocess.run(
            [sys.executable, "-c", codigo, str(self.ruta)],
            capture_output=True, text=True, timeout=20, check=True,
        )
        self.assertEqual(resultado.stdout.strip(), self.datos["huella_indice"])
        self.assertEqual(self.embeddings.documentos, 1)
        self.assertEqual(self.embeddings.consultas, 0)

    def test_repetir_indexacion_no_duplica_ni_calcula_vectores(self):
        no_usar = Mock(side_effect=AssertionError("No recalcular."))
        with patch.object(self.embeddings, "embed_documents", no_usar):
            resultado = indexar_corpus(self.chunks, self.datos, self.embeddings, self.ruta)
        self.assertTrue(resultado["reutilizado"])
        self.assertEqual(len(self.indice.get()["ids"]), 5)
        no_usar.assert_not_called()

    def test_otro_chunking_no_modifica_indice_existente(self):
        chunks, datos = preparar_indice(
            "ejemplo", 100, 10, modelo_embeddings="determinista-pruebas", dimensiones=16,
        )
        with self.assertRaisesRegex(ValueError, "otro índice"):
            indexar_corpus(chunks, datos, self.embeddings, self.ruta)
        self.assertEqual(self.embeddings.documentos, 1)
        self.assertEqual(len(self.indice.get()["ids"]), 5)

    def test_ruta_ausente_no_se_crea_al_consultar(self):
        ruta = Path(self.temporal) / "ausente"
        with self.assertRaisesRegex(ValueError, "ausente"):
            abrir_indice(ruta)
        self.assertFalse(ruta.exists())

    def test_manifiesto_falso_y_coleccion_alterada_no_se_aceptan(self):
        ruta = self.ruta / MANIFIESTO
        original = ruta.read_text()
        datos = json.loads(original)
        datos["configuracion"]["dimensiones"] = 999
        ruta.write_text(json.dumps(datos))
        with self.assertRaisesRegex(ValueError, "manifiesto inválido"):
            abrir_indice(self.ruta)
        ruta.write_text(original)
        self.indice.delete(ids=[str(self.chunks[0].id)])
        with self.assertRaisesRegex(ValueError, "íntegro"):
            abrir_indice(self.ruta)

    def test_error_de_embedding_deja_indice_incompleto_no_reutilizable(self):
        ruta = Path(self.temporal) / "interrumpido"
        with patch.object(self.embeddings, "embed_documents", side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                indexar_corpus(self.chunks, self.datos, self.embeddings, ruta)
        self.assertFalse((ruta / MANIFIESTO).exists())
        with self.assertRaisesRegex(ValueError, "incompleto"):
            abrir_indice(ruta)

    def test_dimensiones_incorrectas_no_dejan_manifiesto_exitoso(self):
        ruta = Path(self.temporal) / "dimensiones"
        with patch.object(self.embeddings, "embed_documents", return_value=[[1.0]] * 5):
            with self.assertRaisesRegex(ValueError, "dimensiones"):
                indexar_corpus(self.chunks, self.datos, self.embeddings, ruta)
        self.assertFalse((ruta / MANIFIESTO).exists())

    def test_cli_real_no_acepta_indice_de_pruebas(self):
        with self.assertRaisesRegex(ValueError, "modelo y dimensiones"):
            exigir_embeddings_reales(self.manifiesto)
