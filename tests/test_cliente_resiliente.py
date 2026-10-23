"""Integración del cliente, API, CLI y evaluadores con respuestas HTTP simuladas."""

import json
import logging
import os
from io import StringIO
from unittest.mock import MagicMock, call, patch

import requests
from urllib3.connection import HTTPConnection
from urllib3.connectionpool import HTTPConnectionPool
from urllib3.exceptions import MaxRetryError, NewConnectionError, ReadTimeoutError

from prompts.banco import BANCO_DE_PROMPTS
from prompts.test_consistencia import evaluar_intento
from src.agente_gemini import consultar_gemini_raw, main
from src.comparar_modelos import medir_consulta
from src.errores_cliente import (
    ErrorAutenticacion,
    ErrorCliente,
    ErrorPeticion,
    ErrorTemporalProveedor,
    ErrorTimeoutLectura,
)
from src.reintentos import SIN_REINTENTOS, PoliticaReintento
from tests.base import CasoAPI


class ClienteResilienteTests(CasoAPI):
    def respuesta(self, codigo, *, headers=None):
        respuesta = MagicMock(status_code=codigo, headers=headers or {})
        respuesta.__enter__.return_value = respuesta
        respuesta.json.return_value = self.upstream.json.return_value
        return respuesta

    def test_api_normal_y_raw_se_recuperan_tras_dos_fallos_y_conservan_el_cuerpo(self):
        for ruta in ("/consultar", "/consultar/raw"):
            with self.subTest(ruta=ruta):
                self.post.reset_mock()
                self.esperar.reset_mock()
                self.post.side_effect = [
                    self.respuesta(429, headers={"Retry-After": "3"}),
                    self.respuesta(503),
                    self.respuesta(200),
                ]
                respuesta = self.client.post(ruta, headers=self.headers, json=self.cuerpo)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(self.post.call_count, 3)
                self.assertEqual(self.esperar.call_args_list, [call(3), call(2)])
                cuerpos = [llamada.kwargs["json"] for llamada in self.post.call_args_list]
                self.assertTrue(all(cuerpo == cuerpos[0] for cuerpo in cuerpos))
                for llamada in self.post.call_args_list:
                    self.assertFalse(llamada.kwargs["allow_redirects"])
                    self.assertEqual(
                        llamada.kwargs["headers"]["Authorization"], "Bearer clave-gemini-ficticia"
                    )
                if ruta == "/consultar/raw":
                    self.assertEqual(respuesta.json(), self.upstream.json.return_value)
                else:
                    self.assertEqual(respuesta.json()["detalles"], self.resultado)

    def test_estados_temporales_se_recuperan_con_una_segunda_llamada(self):
        for codigo in (429, 500, 502, 503, 504):
            with self.subTest(codigo=codigo):
                self.post.reset_mock()
                self.post.side_effect = [self.respuesta(codigo), self.respuesta(200)]
                consultar_gemini_raw("modelo", "Hola")
                self.assertEqual(self.post.call_count, 2)

    def test_estados_permanentes_no_se_reintentan_ni_exponen_el_cuerpo(self):
        for codigo in (400, 401, 403, 404, 501, 505):
            with self.subTest(codigo=codigo):
                self.post.reset_mock()
                self.upstream.status_code = codigo
                error_esperado = ErrorAutenticacion if codigo in (401, 403) else ErrorPeticion
                with self.assertRaises(error_esperado):
                    consultar_gemini_raw("modelo", "Hola")
                self.post.assert_called_once()
        self.upstream.json.assert_not_called()
        self.esperar.assert_not_called()

    def test_credencial_del_proveedor_no_se_confunde_con_el_token_local(self):
        self.upstream.status_code = 401
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 502)
        self.assertEqual(detalles["tipo_error"], "ErrorAutenticacion")
        self.assertEqual(detalles["codigo_proveedor"], 401)
        self.post.assert_called_once()

    def test_retry_after_largo_devuelve_504_sin_otra_peticion(self):
        self.post.side_effect = [self.respuesta(429, headers={"Retry-After": "3600"})]
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 504)
        self.assertEqual(detalles["intentos"], 1)
        self.assertIn("presupuesto de tiempo", detalles["causa"])
        self.post.assert_called_once()
        self.esperar.assert_not_called()

    def test_solo_los_fallos_identificados_antes_del_envio_reintentan_conexion(self):
        pool = HTTPConnectionPool("simulado.test")
        self.addCleanup(pool.close)
        error_apertura = NewConnectionError(HTTPConnection("simulado.test"), "falló la apertura")
        errores = (
            requests.exceptions.ConnectTimeout(),
            requests.exceptions.ConnectionError(MaxRetryError(pool, "/", error_apertura)),
        )
        for error in errores:
            with self.subTest(error=type(error).__name__):
                self.post.reset_mock()
                self.post.side_effect = [error, self.respuesta(200)]
                consultar_gemini_raw("modelo", "Hola")
                self.assertEqual(self.post.call_count, 2)

    def test_lectura_interrupcion_ambigua_y_tls_no_se_reintentan(self):
        pool = HTTPConnectionPool("simulado.test")
        self.addCleanup(pool.close)
        for error, esperado in (
            (requests.exceptions.ReadTimeout(), ErrorTimeoutLectura),
            (
                requests.exceptions.ConnectionError(ReadTimeoutError(pool, "/", "lectura")),
                ErrorTimeoutLectura,
            ),
            (requests.exceptions.ConnectionError("interrupción"), ErrorCliente),
            (requests.exceptions.SSLError("certificado"), ErrorPeticion),
        ):
            with self.subTest(error=type(error).__name__):
                self.post.reset_mock()
                self.post.side_effect = error
                with self.assertRaises(esperado):
                    consultar_gemini_raw("modelo", "Hola")
                self.post.assert_called_once()
        self.esperar.assert_not_called()

    def test_lectura_se_puede_habilitar_expresamente_desde_python(self):
        self.post.side_effect = [requests.exceptions.ReadTimeout(), self.respuesta(200)]
        consultar_gemini_raw("modelo", "Hola", politica=PoliticaReintento(reintentar_lectura=True))
        self.assertEqual(self.post.call_count, 2)

    def test_ambos_evaluadores_hacen_una_peticion_y_conservan_costo_desconocido(self):
        self.upstream.status_code = 503
        registros = (
            medir_consulta("gemini-3.5-flash-lite", "Hola"),
            evaluar_intento(BANCO_DE_PROMPTS["explicar_concepto"], "gemini-3.5-flash-lite", 1),
        )
        self.assertEqual(self.post.call_count, 2)
        self.esperar.assert_not_called()
        for registro in registros:
            self.assertIn("HTTP 503", registro["error"])
            self.assertIsNone(registro["uso"])
        self.assertIsNone(registros[0]["costo_usd"])
        self.assertIsNone(registros[1]["costo_estimado"])

    def test_politica_sin_reintentos_es_publica_y_preserva_categoria(self):
        self.upstream.status_code = 429
        with self.assertRaises(ErrorTemporalProveedor):
            consultar_gemini_raw("modelo", "Hola", politica=SIN_REINTENTOS)
        self.post.assert_called_once()

    def test_cli_recupera_el_error_y_su_stdout_sigue_siendo_json(self):
        self.post.side_effect = [self.respuesta(429), self.respuesta(200)]
        logger = logging.getLogger("pruebas.cliente_resiliente")
        with (
            patch("src.agente_gemini.load_dotenv"),
            patch("sys.argv", ["cliente", "--raw", "pregunta-privada"]),
            patch("sys.stdout", new_callable=StringIO) as salida,
            patch("src.reintentos.logger", logger),
            self.assertLogs(logger, level="INFO") as registros,
        ):
            main()
        self.assertEqual(json.loads(salida.getvalue()), self.upstream.json.return_value)
        self.assertEqual(self.post.call_count, 2)
        texto_log = "\n".join(registros.output)
        self.assertIn("HTTP=429", texto_log)
        self.assertIn("duración=", texto_log)
        self.assertIn("reintentando", texto_log)
        self.assertNotIn("clave-gemini-ficticia", texto_log)
        self.assertNotIn("pregunta-privada", texto_log)

    def test_cli_respeta_un_intento_y_traduce_el_error_a_una_salida_clara(self):
        self.upstream.status_code = 503
        with (
            patch("src.agente_gemini.load_dotenv"),
            patch("sys.argv", ["cliente", "--intentos", "1", "Hola"]),
            self.assertRaises(SystemExit) as salida,
        ):
            main()
        self.assertIn("HTTP 503", str(salida.exception))
        self.post.assert_called_once()
        self.esperar.assert_not_called()

    def test_cli_rechaza_politica_invalida_antes_de_cargar_credenciales(self):
        for argumentos in (("--intentos", "0"), ("--presupuesto-segundos", "nan")):
            with (
                self.subTest(argumentos=argumentos),
                patch("src.agente_gemini.load_dotenv") as cargar,
                patch("sys.argv", ["cliente", *argumentos, "Hola"]),
                patch("sys.stderr", new_callable=StringIO),
                self.assertRaises(SystemExit) as salida,
            ):
                main()
                self.assertEqual(salida.exception.code, 2)
                cargar.assert_not_called()
        self.post.assert_not_called()

    def test_falta_credencial_falla_antes_de_realizar_la_peticion(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}), self.assertRaises(ErrorPeticion):
            consultar_gemini_raw("modelo", "Hola")
        self.post.assert_not_called()
