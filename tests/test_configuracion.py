"""Pruebas de configuracion de la API con servicios simulados."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api import app
from tests.base import CasoAPI


class ConfiguracionAPITests(CasoAPI):
    def test_falta_clave_del_agente_devuelve_503(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 503)
        self.assertEqual(
            detalles, {"agente": "gemini", "configuracion_requerida": "GEMINI_API_KEY"}
        )
        self.post.assert_not_called()


class ConfiguracionTests(unittest.TestCase):
    def test_servidor_no_inicia_sin_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.api.load_dotenv"):
                with self.assertRaisesRegex(RuntimeError, "Falta API_BEARER_TOKEN"):
                    with TestClient(app):
                        pass
