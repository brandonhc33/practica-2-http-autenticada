"""Contrato unitario de transporte y fachada con las excepciones de este proyecto."""

import unittest
from unittest.mock import MagicMock, patch

from src.agente_gemini import _enviar_peticion, consultar_gemini
from src.errores_cliente import ErrorAutenticacion, ErrorTemporalProveedor, ReintentosAgotados


class ClienteModularTests(unittest.TestCase):
    def test_transporte_clasifica_401_y_403_como_autenticacion(self):
        for codigo in (401, 403):
            with self.subTest(codigo=codigo):
                respuesta = MagicMock(status_code=codigo, headers={})
                respuesta.__enter__.return_value = respuesta
                with patch("src.agente_gemini.requests.post", return_value=respuesta):
                    with self.assertRaises(ErrorAutenticacion):
                        _enviar_peticion({}, {}, (1, 1))

    def test_transporte_clasifica_429_y_5xx_recuperables_como_temporales(self):
        for codigo in (429, 500, 502, 503, 504):
            with self.subTest(codigo=codigo):
                respuesta = MagicMock(status_code=codigo, headers={})
                respuesta.__enter__.return_value = respuesta
                with patch("src.agente_gemini.requests.post", return_value=respuesta):
                    with self.assertRaises(ErrorTemporalProveedor):
                        _enviar_peticion({}, {}, (1, 1))

    def test_transporte_devuelve_el_json_exitoso_sin_transformarlo(self):
        datos = {"texto": "simulado", "metadato": [1, None]}
        respuesta = MagicMock(status_code=200)
        respuesta.__enter__.return_value = respuesta
        respuesta.json.return_value = datos
        with patch("src.agente_gemini.requests.post", return_value=respuesta):
            self.assertIs(_enviar_peticion({}, {}, (1, 1)), datos)

    def test_fachada_propaga_el_mismo_error_permanente(self):
        error = ErrorAutenticacion("credencial inválida", codigo_http=401)
        with patch("src.agente_gemini.consultar_gemini_raw", side_effect=error):
            with self.assertRaises(ErrorAutenticacion) as resultado:
                consultar_gemini("modelo", "Hola")
        self.assertIs(resultado.exception, error)

    def test_fachada_conserva_agotamiento_y_causa_para_la_traduccion_de_api_y_cli(self):
        causa = ErrorTemporalProveedor("cuota", codigo_http=429)
        error = ReintentosAgotados(3, causa)
        with patch("src.agente_gemini.consultar_gemini_raw", side_effect=error):
            with self.assertRaises(ReintentosAgotados) as resultado:
                consultar_gemini("modelo", "Hola")
        self.assertIs(resultado.exception, error)
        self.assertIs(resultado.exception.ultimo_error, causa)
