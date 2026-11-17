"""Chroma real en temporales y embeddings deterministas solo para comprobar conexiones."""

import tempfile
import unittest
from pathlib import Path

from langchain_core.embeddings import DeterministicFakeEmbedding, Embeddings

from src.rag.indice import abrir_indice, indexar_corpus, preparar_indice


class EmbeddingsDePrueba(Embeddings):
    def __init__(self):
        self.base = DeterministicFakeEmbedding(size=16)
        self.documentos = 0
        self.consultas = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.documentos += 1
        return self.base.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        self.consultas += 1
        return self.base.embed_query(text)


class PruebaRAG(unittest.TestCase):
    def setUp(self):
        self.temporal = self.enterContext(tempfile.TemporaryDirectory())
        self.ruta = Path(self.temporal) / "indice"
        self.embeddings = EmbeddingsDePrueba()
        self.chunks, self.datos = preparar_indice(
            "ejemplo", 150, 20, modelo_embeddings="determinista-pruebas", dimensiones=16,
        )
        indexar_corpus(self.chunks, self.datos, self.embeddings, self.ruta)
        self.indice, self.manifiesto = abrir_indice(self.ruta)
