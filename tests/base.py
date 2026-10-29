"""Preparación y aserciones compartidas de las pruebas HTTP."""

import os
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from src.api import app
from src.esquemas import EJEMPLO_CONSULTA
from src.registro_costos import sesion_costos
from src.tipo_cambio import ENDPOINT_DOLAR, consultar_dolar

TOKEN = "token-local-para-las-pruebas"


class CasoAPI(unittest.TestCase):
    def setUp(self):
        self.registro_costos = self.enterContext(sesion_costos())
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
        self.esperar = self.enterContext(patch("src.reintentos.sleep"))
        self.enterContext(patch("src.reintentos.uniform", return_value=0.0))
        self.enterContext(patch("src.reintentos.logger.warning"))
        consultar_dolar.cache_clear()
        self.addCleanup(consultar_dolar.cache_clear)
        self.get = self.enterContext(patch("src.tipo_cambio.requests.get"))
        self.dolar = Mock(status_code=200)
        self.dolar.json.return_value = {
            "indicador": "dolar",
            "fecha": "2026-10-19",
            "valor": "900.00",
        }
        self.get.return_value.__enter__.return_value = self.dolar
        self.post = self.enterContext(patch("src.agente_gemini.requests.post"))
        self.upstream = Mock(status_code=200)
        self.upstream.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Respuesta simulada"}}],
            "usage": {"prompt_tokens": 1_000, "completion_tokens": 2_000, "total_tokens": 3_000},
        }
        self.resultado = {
            "respuesta": "Respuesta simulada",
            "uso": {"entrada": 1_000, "salida": 2_000, "total": 3_000, "entrada_cache": 0},
            "costo_estimado": {
                "modelo": "gemini-3.5-flash-lite",
                "usd": {
                    "moneda": "USD",
                    "entrada": "US$ 0.0003",
                    "salida": "US$ 0.005",
                    "total": "US$ 0.0053",
                },
                "clp": {
                    "moneda": "CLP",
                    "entrada": "$ 0.27",
                    "salida": "$ 4.50",
                    "total": "$ 4.77",
                },
                "tipo_cambio": {
                    "clp_por_usd": "900.00",
                    "fecha": "2026-10-19",
                    "fuente": ENDPOINT_DOLAR,
                },
                "tarifas_por_millon_usd": {
                    "entrada": "US$ 0.30",
                    "entrada_cache": "US$ 0.03",
                    "salida": "US$ 2.50",
                },
                "tarifas_por_millon_clp": {
                    "entrada": "$ 270.00",
                    "entrada_cache": "$ 27.00",
                    "salida": "$ 2250.00",
                },
                "aviso_clp": None,
            },
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
        self.assertEqual(detalles["campos_permitidos"], ["agente", "modelo", "mensaje", "prompt"])
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
