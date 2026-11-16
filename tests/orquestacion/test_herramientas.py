import io
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.utils.function_calling import convert_to_openai_tool

from src.orquestacion.herramientas import (
    LIMITE_CARACTERES,
    ArgumentosArticulo,
    ArgumentosInforme,
    buscar_en_ley,
    entregar_informe,
    extraer_palabras,
    obtener_articulo,
)
from src.orquestacion.supervision import esperar_aprobacion, registrar_aprobacion
from src.prompts.contexto_ley_rep import obtener_fragmento_ley_rep
from tests.orquestacion.soporte_agente import PruebaAgente

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
        self.assertIn('Para leerlo completo, usa obtener_articulo con numero="20".', texto_20)
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

        for numero in ("99", "9 bis", ""):
            with self.subTest(numero=numero):
                resultado = obtener_articulo.invoke({"numero": numero})
                self.assertIn(f"No pude leer el artículo {numero}", resultado)
                self.assertIn("Usa 1 a 46, o primero a cuarto transitorio", resultado)

    def test_obtener_articulo_sin_copia_local_devuelve_texto(self):
        with patch(CORPUS, Path("/no/existe/ley_20920.json")):
            resultado = obtener_articulo.invoke({"numero": "9"})

        self.assertIn("No se pudo cargar datos/ley_rep/ley_20920.json", resultado)


class TestArgumentosArticulo(unittest.TestCase):
    def test_argumentos_articulo_describen_cada_campo(self):
        self.assertIs(obtener_articulo.args_schema, ArgumentosArticulo)
        # Lo que recibe el modelo: el esquema de la herramienta, con una descripción por campo.
        parametros = convert_to_openai_tool(obtener_articulo)["function"]["parameters"]
        self.assertEqual(set(parametros["properties"]), {"numero", "transitorio"})
        self.assertEqual(parametros["required"], ["numero"])
        for campo, esquema in parametros["properties"].items():
            with self.subTest(campo=campo):
                self.assertGreater(len(esquema["description"]), 30)

    def test_transitorio_resuelve_el_ordinal(self):
        casos = (
            ({"numero": "1", "transitorio": True}, "Artículo primero transitorio"),
            ({"numero": "primero", "transitorio": True}, "Artículo primero transitorio"),
            ({"numero": "Cuarto", "transitorio": True}, "Artículo cuarto transitorio"),
            ({"numero": "4", "transitorio": True}, "Artículo cuarto transitorio"),
            # Sin transitorio, el ordinal es el número: "primero" es el artículo 1.
            ({"numero": "primero"}, "Artículo 1"),
            ({"numero": "1", "transitorio": False}, "Artículo 1"),
        )
        for argumentos, referencia in casos:
            with self.subTest(argumentos=argumentos):
                resultado = obtener_articulo.invoke(argumentos)
                self.assertTrue(resultado.startswith(f"[{referencia}]\n"), resultado[:60])

        resultado = obtener_articulo.invoke({"numero": "5", "transitorio": True})
        self.assertIn("No pude leer el artículo 5 transitorio", resultado)
        self.assertIn("del primero al cuarto", resultado)

    def test_argumentos_invalidos_no_lanzan_excepcion(self):
        casos = (
            ({"numero": "1", "transitorio": "tal vez"}, "transitorio: Input should be a valid"),
            ({"transitorio": True}, "numero: Field required"),
            ({"numero": 12}, "numero: Input should be a valid string"),
        )
        for argumentos, detalle in casos:
            with self.subTest(argumentos=argumentos):
                resultado = obtener_articulo.invoke(argumentos)
                self.assertTrue(resultado.startswith("Argumentos inválidos ("))
                self.assertIn(detalle, resultado)


class TestDescripciones(unittest.TestCase):
    def test_cada_herramienta_dice_cuando_usarla(self):
        for herramienta in (buscar_en_ley, obtener_articulo, entregar_informe):
            with self.subTest(herramienta=herramienta.name):
                self.assertIn("Usar cuando", herramienta.description)


class TestEntregarInforme(PruebaAgente):
    def setUp(self):
        super().setUp()
        self.argumentos = {"titulo": "../../Título", "contenido": "Texto íntegro (artículo 12)."}
        self.aprobar = self.enterContext(
            patch("src.orquestacion.herramientas.esperar_aprobacion", return_value=True)
        )

    def entregar(self) -> str:
        return entregar_informe.invoke(
            self.argumentos, config={"configurable": {"session_id": "cliente-informe"}}
        )

    def test_entregar_informe_solo_expone_titulo_y_contenido(self):
        self.assertIs(entregar_informe.args_schema, ArgumentosInforme)
        parametros = convert_to_openai_tool(entregar_informe)["function"]["parameters"]
        self.assertEqual(set(parametros["properties"]), {"titulo", "contenido"})
        self.assertEqual(parametros["required"], ["titulo", "contenido"])
        for esquema in parametros["properties"].values():
            self.assertTrue(esquema["description"])

    def test_entregar_informe_aprobado_registra_antes_de_escribir(self):
        originales: list[bool] = []

        def registrar(*args):
            originales.append(self.informes.exists())
            return registrar_aprobacion(*args)

        with patch("src.orquestacion.herramientas.registrar_aprobacion", side_effect=registrar):
            resultado = self.entregar()
        evento = json.loads(self.aprobaciones.read_text())
        informe = self.informes / f"{evento['id_aprobacion']}.md"
        self.assertEqual(originales, [False])
        self.assertEqual(informe.read_text(), "# ../../Título\n\nTexto íntegro (artículo 12).\n")
        self.assertEqual(evento["session_id"], "cliente-informe")
        self.assertTrue(evento["aprobado"])
        self.assertIn("Entrega simulada aprobada", resultado)
        self.assertIn("No se envió a ningún destinatario real", resultado)
        self.assertIn(self.argumentos["contenido"], self.aprobar.call_args.args[0])
        self.assertIn(self.argumentos["titulo"], self.aprobar.call_args.args[0])

    def test_entregar_informe_rechazado_no_escribe(self):
        self.aprobar.return_value = False
        self.assertIn("Entrega no aprobada", self.entregar())
        self.assertFalse(self.informes.exists())
        self.assertFalse(json.loads(self.aprobaciones.read_text())["aprobado"])

    def test_entregar_informe_sin_terminal_registra_rechazo(self):
        self.aprobar.side_effect = esperar_aprobacion
        with (
            patch("src.orquestacion.supervision.sys.stdin", io.StringIO("s\n")),
            patch("sys.stderr", io.StringIO()),
        ):
            self.assertIn("Entrega no aprobada", self.entregar())
        self.assertFalse(self.informes.exists())
        self.assertFalse(json.loads(self.aprobaciones.read_text())["aprobado"])

    def test_entregar_informe_tiempo_agotado_no_escribe(self):
        self.aprobar.side_effect = esperar_aprobacion
        with (
            patch("src.orquestacion.supervision.sys.stdin.isatty", return_value=True),
            patch("src.orquestacion.supervision.select.select", return_value=([], [], [])),
            patch("sys.stderr", io.StringIO()),
        ):
            self.assertIn("Entrega no aprobada", self.entregar())
        self.assertFalse(self.informes.exists())
        self.assertFalse(json.loads(self.aprobaciones.read_text())["aprobado"])

    def test_entregar_informe_sin_registro_no_escribe(self):
        with patch(
            "src.orquestacion.herramientas.registrar_aprobacion",
            side_effect=OSError("sin permisos"),
        ):
            self.assertIn("No se entregó", self.entregar())
        self.assertFalse(self.informes.exists())

    def test_entregar_informe_fallo_de_guardado_conserva_aprobacion(self):
        self.informes.write_text("impide crear el directorio")
        self.assertIn("No se confirma la entrega", self.entregar())
        self.assertTrue(json.loads(self.aprobaciones.read_text())["aprobado"])

    def test_entregar_informe_no_sobrescribe_otra_entrega(self):
        self.entregar()
        self.entregar()
        self.assertEqual(len(list(self.informes.glob("*.md"))), 2)
        self.assertEqual(len(self.aprobaciones.read_text().splitlines()), 2)

    def test_entregar_informe_argumentos_invalidos_no_piden_aprobacion(self):
        for argumentos in ({"titulo": "  ", "contenido": "texto"}, {"titulo": "Título"}):
            with self.subTest(argumentos=argumentos):
                resultado = entregar_informe.invoke(argumentos)
                self.assertTrue(resultado.startswith("Argumentos inválidos"))
        self.aprobar.assert_not_called()
        self.assertFalse(self.aprobaciones.exists())
