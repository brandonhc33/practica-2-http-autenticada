"""El decreto extraído conserva artículos, procedencia y las tablas que eran imágenes."""

import hashlib
import json
import unittest

from scripts.evaluar_normas import cargar_casos
from src.rag.normas import RAIZ, cargar_norma, preparar_norma

CARPETA = RAIZ / "datos" / "ds_12_2020"


class TestDS12(unittest.TestCase):
    def setUp(self):
        self.datos = json.loads((CARPETA / "ds_12_2020.json").read_text(encoding="utf-8"))
        self.tablas = json.loads((CARPETA / "tablas.json").read_text(encoding="utf-8"))["tablas"]

    def test_tiene_47_articulos_y_seis_transitorios(self):
        self.assertEqual(len(self.datos["fragmentos"]), 53)
        self.assertEqual(len({f["id_fragmento"] for f in self.datos["fragmentos"]}), 53)
        self.assertTrue(all(f["texto"].startswith("Artículo ") for f in self.datos["fragmentos"]))

    def test_las_huellas_corresponden_a_los_archivos(self):
        for archivo, campo in (
            (self.datos["archivo_pdf"], "sha256_pdf"),
            ("ds_12_2020.txt", "sha256_texto"),
            ("tablas.json", "sha256_tablas"),
        ):
            with self.subTest(archivo=archivo):
                contenido = (CARPETA / archivo).read_bytes()
                self.assertEqual(hashlib.sha256(contenido).hexdigest(), self.datos[campo])

    def test_cada_fila_de_las_tablas_esta_en_su_articulo(self):
        textos = {f["id_fragmento"]: f["texto"] for f in self.datos["fragmentos"]}
        for tabla in self.tablas:
            for fila in tabla["filas"]:
                with self.subTest(articulo=tabla["articulo"], fila=fila[0]):
                    self.assertIn(
                        tabla["fila"].format(*fila), textos[f"ds12-articulo-{tabla['articulo']}"]
                    )

    def test_las_metas_nunca_bajan_de_un_ano_al_siguiente(self):
        # No prueba la transcripción, pero detecta una celda intercambiada o mal leída.
        for tabla in self.tablas:
            valores = [
                [int("".join(c for c in celda if c.isdigit())) for celda in fila[1:]]
                for fila in tabla["filas"]
            ]
            for columna in zip(*valores, strict=True):
                baja = tabla["articulo"] == "35"
                with self.subTest(articulo=tabla["articulo"], columna=columna):
                    self.assertEqual(list(columna), sorted(columna, reverse=baja))

    def test_ninguna_fila_queda_cortada_entre_fragmentos(self):
        chunks = [c.page_content for c in preparar_norma("ds-12-2020")[0]]
        for tabla in self.tablas:
            for fila in tabla["filas"]:
                texto = tabla["fila"].format(*fila)
                self.assertTrue(any(texto in c for c in chunks), texto)

    def test_sin_encabezados_del_diario_oficial(self):
        texto = "\n".join(d.page_content for d in cargar_norma("ds-12-2020"))
        for resto in ("Director:", "Sitio Web", "CVE 1910141", "firmado electrónicamente"):
            self.assertNotIn(resto, texto)

    def test_etiquetas_de_evaluacion_vigentes(self):
        self.assertEqual(len(cargar_casos()), 27)
