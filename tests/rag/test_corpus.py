"""La preparación no necesita API y mantiene trazabilidad del corpus de origen."""

import unittest

from langchain_core.documents import Document

from src.rag.corpus import (
    cargar_corpus,
    comparar_chunking,
    fragmentar_documentos,
    verificar_integridad,
)
from src.rag.evaluacion import cargar_casos
from src.rag.indice import preparar_indice


class TestCorpus(unittest.TestCase):
    def test_ley_tiene_50_documentos_y_99_chunks_con_fuentes(self):
        documentos = cargar_corpus()
        chunks, datos = preparar_indice()
        self.assertEqual(len(documentos), 50)
        self.assertEqual(len(chunks), 99)
        self.assertEqual(datos["integridad"]["caracteres_sin_cubrir"], 0)
        self.assertEqual(datos["integridad"]["textos_duplicados"], 0)
        self.assertEqual(len({c.id for c in chunks}), 99)
        for c in chunks:
            with self.subTest(id=c.id):
                self.assertTrue(c.page_content.strip())
                self.assertIn("sha256_pdf", c.metadata)
                self.assertEqual(c.metadata["version"], "2016-06-01")
                self.assertTrue(c.metadata["paginas"])

    def test_compara_dos_estrategias_y_dos_tamanos(self):
        resultados = comparar_chunking(cargar_corpus())
        self.assertEqual([r["chunks"] for r in resultados], [164, 95, 187, 99])
        self.assertTrue(all(r["caracteres_sin_cubrir"] == 0 for r in resultados))
        self.assertTrue(all(r["ejemplo_articulo_9"] for r in resultados))

    def test_replica_tiene_5_chunks_sin_mezclar_ley(self):
        chunks, datos = preparar_indice("ejemplo", 150, 20)
        self.assertEqual(len(chunks), 5)
        self.assertEqual(datos["integridad"]["caracteres_corpus"], 490)
        self.assertEqual(datos["integridad"]["caracteres_chunks"], 490)
        self.assertTrue(all(str(c.id).startswith("tienda-") for c in chunks))

    def test_configuraciones_invalidas_fallan_antes_de_fragmentar(self):
        for size, overlap in ((0, 0), (20, 20), (20, -1), (-10, 0)):
            with self.subTest(size=size, overlap=overlap), self.assertRaises(ValueError):
                fragmentar_documentos(cargar_corpus(), size, overlap)

    def test_integridad_detecta_perdida_de_texto_y_metadatos(self):
        documentos = cargar_corpus("ejemplo")
        chunks = fragmentar_documentos(documentos, 150, 20)
        with self.assertRaisesRegex(ValueError, "perdió"):
            verificar_integridad(documentos, chunks[:-1])
        chunks[0].metadata.pop("fuente")
        with self.assertRaisesRegex(ValueError, "metadata"):
            verificar_integridad(documentos, chunks)

    def test_integridad_rechaza_ids_duplicados_y_texto_ajeno(self):
        documentos = cargar_corpus("ejemplo")
        chunks = fragmentar_documentos(documentos, 150, 20)
        chunks[1].id = chunks[0].id
        with self.assertRaisesRegex(ValueError, "IDs únicos"):
            verificar_integridad(documentos, chunks)
        chunks[0].page_content = "Texto inventado."
        with self.assertRaisesRegex(ValueError, "distinto"):
            verificar_integridad(documentos, chunks)

    def test_ids_y_huella_repetibles_etiquetas_anteriores_al_retrieval(self):
        chunks, datos = preparar_indice()
        otros, otra = preparar_indice()
        self.assertEqual(chunks, otros)
        self.assertEqual(datos, otra)
        casos = cargar_casos(datos, {str(c.id) for c in chunks})
        self.assertEqual(len(casos), 10)
        self.assertEqual(casos[-1]["ids_relevantes"], [])
        with self.assertRaisesRegex(ValueError, "ausentes"):
            cargar_casos(datos, set())

    def test_no_mezcla_articulos_aunque_sean_cortos(self):
        documentos = cargar_corpus("ejemplo")
        chunks = fragmentar_documentos(documentos, 2000, 100)
        self.assertEqual(len(chunks), 5)
        self.assertEqual(chunks[0].page_content, documentos[0].page_content)

    def test_documento_vacio_no_pasa_integridad(self):
        documento = Document(id="vacio", page_content="", metadata={"id_documento": "vacio"})
        with self.assertRaises(ValueError):
            verificar_integridad([documento], [])
