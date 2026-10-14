"""Pruebas de errores http de la API con servicios simulados."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api import app
from tests.base import CasoAPI


class ErroresHTTPTests(CasoAPI):
    def test_rutas_inexistentes_y_metodos_no_permitidos_usan_el_contrato(self):
        for ruta in ("/no-existe", "/health/", "/consultar/"):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta, headers=self.headers, follow_redirects=False)
                detalles = self.assertRespuesta(respuesta, 404, "La ruta solicitada no existe.")
                self.assertEqual(detalles, {"ruta": ruta, "metodo": "GET"})
        respuesta = self.client.get("/consultar", headers=self.headers)
        detalles = self.assertRespuesta(respuesta, 405)
        self.assertEqual(respuesta.headers["Allow"], "POST")
        self.assertEqual(detalles["metodos_permitidos"], ["POST"])
        self.post.assert_not_called()

    def test_excepcion_inesperada_devuelve_500_sin_exponer_informacion_interna(self):
        with TestClient(app, raise_server_exceptions=False) as cliente:
            with patch(
                "src.api.consultar_agente", side_effect=RuntimeError("dato-interno-sensible")
            ):
                with self.assertLogs("src.respuestas", level="ERROR") as registros:
                    respuesta = cliente.post("/consultar", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 500, "Ocurrió un error interno en el servidor.")
        self.assertIn("accion", detalles)
        self.assertNotIn("dato-interno-sensible", respuesta.text)
        self.assertNotIn("RuntimeError", respuesta.text)
        self.assertIn("dato-interno-sensible", "\n".join(registros.output))
        self.post.assert_not_called()

    def test_error_de_validacion_de_respuesta_tambien_usa_el_contrato_500(self):
        with TestClient(app, raise_server_exceptions=False) as cliente:
            with patch("src.api.EstadoAPI", return_value={"estado": "invalido"}):
                with self.assertLogs("src.respuestas", level="ERROR"):
                    respuesta = cliente.get("/health", headers=self.headers)
        self.assertRespuesta(respuesta, 500)
        self.assertNotIn("invalido", respuesta.text)
        self.post.assert_not_called()
