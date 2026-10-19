"""Respuesta completa de Gemini mediante el endpoint autenticado de inspección."""

import os
from unittest.mock import patch

import requests

from src.agente_gemini import ENDPOINT
from tests.base import TOKEN, CasoAPI


class ConsultasRawTests(CasoAPI):
    def test_devuelve_todos_los_campos_del_proveedor_sin_transformarlos(self):
        datos = {
            "id": "consulta-simulada",
            "object": "chat.completion",
            "created": 1_792_368_000,
            "model": "gemini-3.5-flash-lite",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "  respuesta original\n  "},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 35,
                "completion_tokens_details": {"reasoning_tokens": 5},
            },
            "metadato_adicional": {"valores": [1, None, {"bandera": True}]},
        }
        self.upstream.json.return_value = datos
        contenido = "  pregunta original\n  "
        respuesta = self.client.post(
            "/consultar/raw", headers=self.headers, json={**self.cuerpo, "mensaje": contenido}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.headers["content-type"], "application/json")
        self.assertEqual(respuesta.json(), datos)
        self.post.assert_called_once()
        self.assertEqual(self.post.call_args.args[0], ENDPOINT)
        self.assertEqual(
            self.post.call_args.kwargs["json"],
            {
                "model": "gemini-3.5-flash-lite",
                "messages": [{"role": "user", "content": contenido}],
            },
        )
        self.assertEqual(
            self.post.call_args.kwargs["headers"]["Authorization"], "Bearer clave-gemini-ficticia"
        )
        self.assertNotIn(TOKEN, str(self.post.call_args))
        self.assertFalse(self.post.call_args.kwargs["allow_redirects"])
        self.get.assert_not_called()

    def test_permite_inspeccionar_respuestas_sin_texto_ni_consumo(self):
        for datos in (
            {},
            {"choices": []},
            {"choices": [{"message": {"content": None}, "finish_reason": "content_filter"}]},
        ):
            with self.subTest(datos=datos):
                self.upstream.json.return_value = datos
                respuesta = self.client.post(
                    "/consultar/raw", headers=self.headers, json=self.cuerpo
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.json(), datos)
        self.get.assert_not_called()

    def test_validaciones_del_endpoint_raw_usan_el_contrato_local(self):
        for cuerpo in (
            {},
            {**self.cuerpo, "mensaje": ""},
            {**self.cuerpo, "modelo": "desconocido"},
        ):
            with self.subTest(cuerpo=cuerpo):
                respuesta = self.client.post("/consultar/raw", headers=self.headers, json=cuerpo)
                self.assertValidaciones(respuesta)
        self.post.assert_not_called()
        self.get.assert_not_called()

    def test_falta_clave_de_gemini_devuelve_503(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            respuesta = self.client.post("/consultar/raw", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 503)
        self.assertEqual(
            detalles, {"agente": "gemini", "configuracion_requerida": "GEMINI_API_KEY"}
        )
        self.post.assert_not_called()

    def test_error_del_proveedor_usa_el_contrato_local_sin_exponer_su_cuerpo(self):
        self.upstream.status_code = 429
        self.upstream.json.return_value = {"error": {"message": "dato-interno-del-proveedor"}}
        respuesta = self.client.post("/consultar/raw", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 502)
        self.assertIn("HTTP 429", detalles["causa"])
        self.assertNotIn("dato-interno-del-proveedor", respuesta.text)
        self.upstream.json.assert_not_called()

    def test_timeout_usa_el_contrato_local(self):
        self.post.side_effect = requests.exceptions.Timeout()
        respuesta = self.client.post("/consultar/raw", headers=self.headers, json=self.cuerpo)
        self.assertIn("tardó demasiado", self.assertRespuesta(respuesta, 502)["causa"])

    def test_json_invalido_o_que_no_es_objeto_devuelve_502(self):
        for datos in (None, [], "texto"):
            with self.subTest(datos=datos):
                self.upstream.json.return_value = datos
                respuesta = self.client.post(
                    "/consultar/raw", headers=self.headers, json=self.cuerpo
                )
                self.assertRespuesta(respuesta, 502)
        self.upstream.json.side_effect = requests.exceptions.JSONDecodeError("JSON inválido", "", 0)
        respuesta = self.client.post("/consultar/raw", headers=self.headers, json=self.cuerpo)
        self.assertIn("JSON válido", self.assertRespuesta(respuesta, 502)["causa"])
