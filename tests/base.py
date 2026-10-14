"""Preparación y aserciones compartidas de las pruebas HTTP."""

import os
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from src.api import app
from src.esquemas import EJEMPLO_CONSULTA

TOKEN = "token-local-para-las-pruebas"


class CasoAPI(unittest.TestCase):
    def setUp(self):
        self.enterContext(
            patch.dict(
                os.environ,
                {
                    "API_BEARER_TOKEN": TOKEN,
                    "GEMINI_API_KEY": "clave-gemini-ficticia",
                },
                clear=True,
            )
        )
        self.enterContext(patch("src.api.load_dotenv"))
        self.post = self.enterContext(patch("src.agente_gemini.requests.post"))
        self.upstream = Mock(status_code=200)
        self.upstream.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Respuesta simulada"}}]
        }
        self.post.return_value.__enter__.return_value = self.upstream
        self.client = self.enterContext(TestClient(app))
        self.headers = {"Authorization": f"Bearer {TOKEN}"}
        self.cuerpo = {
            "agente": "gemini",
            "modelo": "flash-lite",
            "mensaje": "Hola",
        }

    def assertRespuesta(self, respuesta, codigo, mensaje=None):
        self.assertEqual(respuesta.status_code, codigo)
        self.assertEqual(respuesta.headers["content-type"], "application/json")
        datos = respuesta.json()
        self.assertEqual(set(datos), {"error", "codigo", "mensaje", "detalles"})
        self.assertIs(datos["error"], codigo >= 400)
        self.assertEqual(datos["codigo"], codigo)
        self.assertIsInstance(datos["mensaje"], str)
        self.assertTrue(datos["mensaje"])
        self.assertIsInstance(datos["detalles"], dict)
        if mensaje is not None:
            self.assertEqual(datos["mensaje"], mensaje)
        return datos["detalles"]

    def assertValidaciones(self, respuesta):
        detalles = self.assertRespuesta(respuesta, 422, "Revisa los campos de la solicitud.")
        self.assertEqual(detalles["campos_permitidos"], ["agente", "modelo", "mensaje"])
        self.assertEqual(detalles["ejemplo"], EJEMPLO_CONSULTA)
        validaciones = detalles["validaciones"]
        self.assertTrue(validaciones)
        for validacion in validaciones:
            self.assertEqual(set(validacion), {"campo", "errores"})
            self.assertIsInstance(validacion["campo"], str)
            self.assertTrue(validacion["errores"])
            for error in validacion["errores"]:
                self.assertIsInstance(error, str)
                self.assertTrue(error)
        campos = {validacion["campo"]: validacion["errores"] for validacion in validaciones}
        self.assertEqual(len(campos), len(validaciones))
        return campos
