import re
import unittest
from pathlib import Path
from unittest.mock import patch

from src.orquestacion.herramientas import (
    LIMITE_CARACTERES,
    buscar_en_ley,
    extraer_palabras,
    obtener_articulo,
)
from src.prompts.contexto_ley_rep import obtener_fragmento_ley_rep

CORPUS = "src.prompts.contexto_ley_rep.RUTA_CORPUS"


def referencias(texto: str) -> list[str]:
    """Referencias de los artículos devueltos, en orden: "[Artículo 20]" -> "Artículo 20"."""
    return re.findall(r"^\[(.+?)\]$", texto, re.MULTILINE)


class TestBuscarEnLey(unittest.TestCase):
    def test_buscar_en_ley_devuelve_hasta_tres_articulos(self):
        resultado = buscar_en_ley.invoke({"consulta": "sistemas colectivos de gestión"})

        self.assertEqual(referencias(resultado), ["Artículo 20", "Artículo 19", "Artículo 22"])
        # El artículo 20 tiene 1.870 caracteres: se recorta y se avisa cómo leerlo completo.
        texto_20 = resultado.split("[Artículo 19]")[0]
        self.assertIn(obtener_fragmento_ley_rep(20)["texto"][:LIMITE_CARACTERES], texto_20)
        self.assertNotIn(obtener_fragmento_ley_rep(20)["texto"][LIMITE_CARACTERES:], texto_20)
        self.assertIn('Para leerlo completo, usa obtener_articulo con "20"', texto_20)
        self.assertIn("se muestran 1500 de 1870 caracteres", texto_20)

    def test_buscar_en_ley_prefiere_el_titulo_y_tolera_tildes_y_plurales(self):
        casos = (
            ("metas de recolección y valorización", "Artículo 12"),
            ("¿Qué obligaciones tienen los consumidores?", "Artículo 34"),
            ("neumaticos", "Artículo 10"),
            ("gestor de residuos", "Artículo 6"),
            ("recicladores de base", "Artículo 32"),
            ("plazo para dictar los reglamentos", "Artículo tercero transitorio"),
        )
        for consulta, primera in casos:
            with self.subTest(consulta=consulta):
                encontrados = referencias(buscar_en_ley.invoke({"consulta": consulta}))
                self.assertEqual(encontrados[0], primera)
                self.assertLessEqual(len(encontrados), 3)

    def test_buscar_en_ley_sin_resultados_devuelve_texto(self):
        casos = (
            ("xilófono cuántico", "No encontré artículos sobre 'xilófono cuántico'"),
            # Un número o la palabra "artículo" no son un tema: eso es de obtener_articulo.
            ("artículo 9", "usa obtener_articulo"),
            ("Art. 12º de la Ley 20.920", "usa obtener_articulo"),
            ("", "La búsqueda necesita un tema"),
        )
        for consulta, aviso in casos:
            with self.subTest(consulta=consulta):
                resultado = buscar_en_ley.invoke({"consulta": consulta})
                self.assertIn(aviso, resultado)
                self.assertEqual(referencias(resultado), [])

        with patch(CORPUS, Path("/no/existe/ley_20920.json")):
            resultado = buscar_en_ley.invoke({"consulta": "sanciones"})
        self.assertIn("No pude buscar en la ley", resultado)
        self.assertIn("No se pudo cargar", resultado)

    def test_extraer_palabras_ignora_numeros_y_palabras_sin_tema(self):
        self.assertEqual(
            extraer_palabras("¿Qué dice el Artículo 9 de la Ley REP sobre los Gestores?"),
            {"gestor"},
        )


class TestObtenerArticulo(unittest.TestCase):
    def test_obtener_articulo_devuelve_texto_o_aviso(self):
        for numero, referencia in (("12", "Artículo 12"), (" 3 ", "Artículo 3")):
            with self.subTest(numero=numero):
                resultado = obtener_articulo.invoke({"numero": numero})
                fragmento = obtener_fragmento_ley_rep(numero.strip())
                # Completo, sin recorte: el artículo 3 tiene 6.982 caracteres.
                self.assertEqual(resultado, f"[{referencia}]\n{fragmento['texto']}")

        resultado = obtener_articulo.invoke({"numero": "primero"})
        self.assertTrue(resultado.startswith("[Artículo primero transitorio]\n"))

        for numero in ("99", "9 bis", ""):
            with self.subTest(numero=numero):
                resultado = obtener_articulo.invoke({"numero": numero})
                self.assertIn(f"No pude leer el artículo {numero}", resultado)
                self.assertIn("Usa 1 a 46, o primero a cuarto transitorio", resultado)

    def test_obtener_articulo_sin_copia_local_devuelve_texto(self):
        with patch(CORPUS, Path("/no/existe/ley_20920.json")):
            resultado = obtener_articulo.invoke({"numero": "9"})

        self.assertIn("No se pudo cargar datos/ley_rep/ley_20920.json", resultado)


class TestDescripciones(unittest.TestCase):
    def test_cada_herramienta_dice_cuando_usarla(self):
        for herramienta in (buscar_en_ley, obtener_articulo):
            with self.subTest(herramienta=herramienta.name):
                self.assertIn("Usar cuando", herramienta.description)
