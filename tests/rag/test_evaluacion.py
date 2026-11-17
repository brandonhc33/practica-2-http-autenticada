"""Las métricas no se inflan con duplicados ni convierten recall indefinido en cero."""

import json
from pathlib import Path
from unittest.mock import patch

from src.rag.evaluacion import (
    cargar_casos,
    evaluar_recuperacion,
    formatear_resultados,
    precision_at_k,
    promediar,
    recall_at_k,
)
from tests.rag.soporte import PruebaRAG


class TestEvaluacion(PruebaRAG):
    def test_metricas_vacios_duplicados_y_promedio_indefinido(self):
        self.assertEqual(precision_at_k(["a", "a", "b"], {"a"}), 0.5)
        self.assertEqual(recall_at_k(["a", "a"], {"a", "b"}), 0.5)
        self.assertEqual(precision_at_k([], {"a"}), 0.0)
        self.assertIsNone(recall_at_k(["a"], set()))
        self.assertEqual(promediar([None, 0.5, 1.0]), 0.75)
        self.assertIsNone(promediar([None]))

    def test_evalua_ranking_real_de_chroma_y_repeticion_sin_generacion(self):
        casos = [
            {"pregunta": "Cancelación de pedidos", "ids_relevantes": ["tienda-0-c000"]},
            {"pregunta": "Impuesto 2027", "ids_relevantes": []},
        ]
        resultado = evaluar_recuperacion(
            self.indice, self.embeddings, casos, self.manifiesto, (3, 5), 2,
        )
        self.assertEqual(self.embeddings.consultas, 4)
        self.assertEqual(self.embeddings.documentos, 1)
        self.assertTrue(resultado["repeticiones_identicas"])
        self.assertEqual(len(resultado["corridas"]), 2)
        for r in resultado["corridas"][0]["resultados"]:
            self.assertEqual(r["por_k"]["3"]["ids_recuperados"], r["por_k"]["5"]["ids_recuperados"][:3])
            self.assertGreaterEqual(r["por_k"]["5"]["precision"], 0)
            if r["ids_relevantes"]:
                self.assertGreaterEqual(r["por_k"]["5"]["recall"], r["por_k"]["3"]["recall"])
            else:
                self.assertIsNone(r["por_k"]["3"]["recall"])
        texto = formatear_resultados(resultado)
        self.assertIn("n/a", texto)
        self.assertIn(self.manifiesto["huella_indice"], texto)
        self.assertIn("k=3", texto)
        self.assertIn("k=5", texto)

    def test_etiquetas_obsoletas_rechazadas_antes_de_embeddings(self):
        ruta = Path(self.temporal) / "casos.json"
        ruta.write_text(json.dumps({"huella_indice": "otra", "casos": []}))
        with self.assertRaisesRegex(ValueError, "otro corpus"):
            cargar_casos(self.manifiesto, set(), ruta)
        self.assertEqual(self.embeddings.consultas, 0)

    def test_error_de_retrieval_no_se_convierte_en_metricas_cero(self):
        with patch.object(self.embeddings, "embed_query", side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                evaluar_recuperacion(
                    self.indice, self.embeddings,
                    [{"pregunta": "Consulta", "ids_relevantes": []}], self.manifiesto,
                )
