"""Pruebas de gemini de la API con servicios simulados."""

import requests

from tests.base import CasoAPI


class GeminiTests(CasoAPI):
    def test_timeout_de_gemini_devuelve_502(self):
        self.post.side_effect = requests.exceptions.Timeout()
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 502)
        self.assertIn("tardó demasiado", detalles["causa"])
        self.assertEqual(detalles["agente"], self.cuerpo["agente"])
        self.assertEqual(detalles["modelo"], self.cuerpo["modelo"])

    def test_gemini_no_disponible_devuelve_502(self):
        self.upstream.status_code = 503
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 502)
        self.assertIn("HTTP 503", detalles["causa"])
        self.assertIn("temporalmente", detalles["causa"])
        self.upstream.json.assert_not_called()

    def test_json_invalido_de_gemini_devuelve_502(self):
        self.upstream.json.side_effect = requests.exceptions.JSONDecodeError(
            "JSON inválido", "texto", 0
        )
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 502)
        self.assertIn("JSON válido", detalles["causa"])

    def test_respuesta_de_gemini_sin_texto_devuelve_502(self):
        for datos in (
            None,
            {},
            {"choices": []},
            {"choices": [None]},
            {"choices": [{"message": {"content": None}}]},
            {"choices": [{"message": {"content": "   "}}]},
        ):
            with self.subTest(datos=datos):
                self.upstream.json.return_value = datos
                respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
                self.assertRespuesta(respuesta, 502)
