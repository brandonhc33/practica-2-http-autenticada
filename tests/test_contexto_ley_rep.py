"""Integridad del PDF convertido y contexto documental, sin consultas reales."""

import hashlib
import json
import re
import unittest
from io import StringIO
from unittest.mock import patch

from prompts.contexto_ley_rep import (
    RUTA_CORPUS,
    cargar_documento_ley_rep,
    obtener_fragmento_ley_rep,
    preparar_respuesta_rep,
    preparar_resumen_rep,
)
from src.agente_gemini import main
from tests.base import CasoAPI
from tests.test_prompts import RESPUESTA_REP


class DocumentoLeyREPTests(unittest.TestCase):
    def test_archivos_corresponden_al_pdf_y_texto_registrados(self):
        datos = cargar_documento_ley_rep()
        carpeta = RUTA_CORPUS.parent
        pdf = (carpeta / datos["archivo_pdf"]).read_bytes()
        texto = (carpeta / "ley_20920.txt").read_bytes()
        self.assertEqual(hashlib.sha256(pdf).hexdigest(), datos["sha256_pdf"])
        self.assertEqual(hashlib.sha256(texto).hexdigest(), datos["sha256_texto"])
        self.assertEqual(datos["paginas"], 18)
        self.assertEqual(datos["version_documento"], "2016-06-01")
        self.assertEqual(texto.decode().count("[Página "), 18)
        self.assertIn("Tribunal Constitucional", texto.decode())

    def test_se_conservan_los_articulos_y_transitorios_en_orden(self):
        datos = cargar_documento_ley_rep()
        texto = RUTA_CORPUS.with_suffix(".txt").read_text(encoding="utf-8")
        texto_normalizado = " ".join(re.sub(r"\[Página \d+\]", "", texto).split())
        esperados = [f"ley20920-articulo-{n}" for n in range(1, 47)] + [
            f"ley20920-transitorio-{n}" for n in ("primero", "segundo", "tercero", "cuarto")
        ]
        self.assertEqual([f["id_fragmento"] for f in datos["fragmentos"]], esperados)
        for fragmento in datos["fragmentos"]:
            with self.subTest(fragmento=fragmento["id_fragmento"]):
                self.assertEqual(fragmento["sha256_pdf"], datos["sha256_pdf"])
                self.assertTrue(fragmento["texto"].startswith("Artículo "))
                self.assertTrue(fragmento["paginas"])
                self.assertTrue(all(1 <= pagina <= 18 for pagina in fragmento["paginas"]))
                self.assertNotIn("Biblioteca del Congreso Nacional", fragmento["texto"])
                self.assertIn(" ".join(fragmento["texto"].split()), texto_normalizado)

    def test_articulos_multiplagina_y_normas_citadas_no_se_cortan(self):
        definiciones = obtener_fragmento_ley_rep(3)
        self.assertEqual(definiciones["paginas"], [2, 3, 4])
        self.assertIn("31) Valorización energética", definiciones["texto"])
        modificaciones = obtener_fragmento_ley_rep(46)
        self.assertEqual(modificaciones["paginas"], [16, 17])
        self.assertIn("Artículo 48 ter.-", modificaciones["texto"])
        transitorio = obtener_fragmento_ley_rep("cuarto")
        self.assertEqual(transitorio["paginas"], [17, 18])
        self.assertIn("Tesoro Público", transitorio["texto"])
        self.assertNotIn("Habiéndose cumplido", transitorio["texto"])

    def test_pregunta_normal_y_json_sin_fragmentos_cargan_la_ley(self):
        for mensaje in (
            "¿Cuál es el objeto de esta ley?",
            json.dumps(
                {"pregunta": "¿Cuál es el objeto?", "antecedentes": {"actividad": "estudio"}}
            ),
        ):
            with self.subTest(mensaje=mensaje):
                datos = json.loads(preparar_respuesta_rep(mensaje))
                self.assertEqual(len(datos["fragmentos"]), 50)
                self.assertIn("Artículo 1º.- Objeto.", datos["fragmentos"][0]["texto"])
                self.assertEqual(datos["fragmentos"][0]["version_documento"], "2016-06-01")
                self.assertIn("antecedentes", datos)
        self.assertEqual(datos["antecedentes"], {"actividad": "estudio"})

    def test_contexto_explicito_incluso_vacio_se_respeta(self):
        for fragmentos in ([], [obtener_fragmento_ley_rep(9)]):
            mensaje = json.dumps(
                {
                    "pregunta": "¿Qué dice el documento?",
                    "antecedentes": {},
                    "fragmentos": fragmentos,
                }
            )
            with self.subTest(fragmentos=len(fragmentos)):
                with patch("prompts.contexto_ley_rep.cargar_documento_ley_rep") as cargar:
                    self.assertEqual(preparar_respuesta_rep(mensaje), mensaje)
                    cargar.assert_not_called()

    def test_resumen_acepta_numero_articulo_transitorio_y_json_explicito(self):
        for selector in ("3", "artículo 3", "ARTICULO 3"):
            with self.subTest(selector=selector):
                datos = json.loads(preparar_resumen_rep(selector))
                self.assertEqual(datos, obtener_fragmento_ley_rep(3))
        for selector in ("artículo primero transitorio", " Artículo primero  transitorio "):
            with self.subTest(selector=selector):
                transitorio = json.loads(preparar_resumen_rep(selector))
                self.assertEqual(transitorio, obtener_fragmento_ley_rep("primero"))
        mensaje = json.dumps(obtener_fragmento_ley_rep(1))
        self.assertEqual(preparar_resumen_rep(mensaje), mensaje)

    def test_entradas_invalidas_no_generan_contexto_incompleto(self):
        for mensaje in ("", "{", "[]", '{"pregunta":""}', '{"pregunta":"Hola","fragmentos":[1]}'):
            with self.subTest(mensaje=mensaje), self.assertRaises(ValueError):
                preparar_respuesta_rep(mensaje)
        for mensaje in ("0", "47", "artículo 1 transitorio", "resume algo", "{", "[]"):
            with self.subTest(selector=mensaje), self.assertRaises(ValueError):
                preparar_resumen_rep(mensaje)


class ContextoLeyREPTests(CasoAPI):
    def test_endpoints_incluyen_la_ley_para_una_pregunta_normal(self):
        self.upstream.json.return_value["choices"] = [
            {"message": {"content": json.dumps(RESPUESTA_REP)}, "finish_reason": "stop"}
        ]
        for endpoint in ("/consultar", "/consultar/raw"):
            with self.subTest(endpoint=endpoint):
                self.post.reset_mock()
                respuesta = self.client.post(
                    endpoint,
                    headers=self.headers,
                    json={
                        **self.cuerpo,
                        "prompt": "responder_ley_rep",
                        "mensaje": "¿Cuál es el objeto de esta ley?",
                    },
                )
                self.assertEqual(respuesta.status_code, 200)
                self.post.assert_called_once()
                contenido = self.post.call_args.kwargs["json"]["messages"][1]["content"]
                contexto = json.loads(contenido)
                self.assertEqual(contexto["pregunta"], "¿Cuál es el objeto de esta ley?")
                self.assertEqual(len(contexto["fragmentos"]), 50)
                self.assertEqual(contexto["fragmentos"][0], obtener_fragmento_ley_rep(1))

    def test_cli_permite_preguntar_con_la_ley_y_resumir_un_articulo_en_raw(self):
        for prompt, pregunta in (
            ("responder_ley_rep", "¿Cuál es el objeto de esta ley?"),
            ("resumir_fragmento_rep", "artículo 3"),
        ):
            with (
                self.subTest(prompt=prompt),
                patch("src.agente_gemini.load_dotenv"),
                patch("sys.argv", ["cliente", "--raw", "--prompt", prompt, pregunta]),
                patch("sys.stdout", new_callable=StringIO) as salida,
            ):
                main()
                self.assertEqual(json.loads(salida.getvalue()), self.upstream.json.return_value)
                entrada = json.loads(self.post.call_args.kwargs["json"]["messages"][1]["content"])
                if prompt == "responder_ley_rep":
                    self.assertEqual(len(entrada["fragmentos"]), 50)
                else:
                    self.assertEqual(entrada, obtener_fragmento_ley_rep(3))
        self.get.assert_not_called()
