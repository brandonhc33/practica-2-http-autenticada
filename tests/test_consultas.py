"""Pruebas de consultas de la API con servicios simulados."""

import os
from unittest.mock import Mock, patch

from src.agente_gemini import ENDPOINT
from src.agentes import CLIENTES
from src.catalogo import AGENTES
from src.esquemas import Resultado
from tests.base import CasoAPI


class ConsultasTests(CasoAPI):
    def test_health_con_token_correcto(self):
        respuesta = self.client.get("/health", headers=self.headers)
        detalles = self.assertRespuesta(respuesta, 200, "La API está disponible.")
        self.assertEqual(detalles, {"estado": "ok"})
        self.post.assert_not_called()

    def test_consulta_exitosa_incluye_texto_tokens_y_costo_en_detalles(self):
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 200, "Consulta realizada correctamente.")
        self.assertEqual(detalles, self.resultado)
        self.post.assert_called_once()
        self.assertEqual(self.post.call_args.args[0], ENDPOINT)
        self.assertEqual(
            self.post.call_args.kwargs["json"],
            {
                "model": "gemini-3.5-flash-lite",
                "messages": [{"role": "user", "content": "Hola"}],
            },
        )

    def test_modelo_se_resuelve_dentro_del_agente(self):
        with patch.dict(AGENTES["gemini"]["modelos"], {"otro": "gemini-modelo-alternativo"}):
            cuerpo = {**self.cuerpo, "modelo": "otro"}
            respuesta = self.client.post("/consultar", headers=self.headers, json=cuerpo)
        detalles = self.assertRespuesta(respuesta, 200)
        self.assertEqual(self.post.call_args.kwargs["json"]["model"], "gemini-modelo-alternativo")
        self.assertEqual(detalles["respuesta"], "Respuesta simulada")
        self.assertEqual(detalles["uso"], self.resultado["uso"])
        self.assertIsNone(detalles["costo_estimado"])

    def test_modelos_del_catalogo_se_envian_al_proveedor_y_calculan_su_costo(self):
        casos = (
            ("flash-lite", "gemini-3.5-flash-lite", "US$ 0.0053", "$ 4.77"),
            ("flash", "gemini-3.6-flash", "US$ 0.00825", "$ 7.425"),
            ("flash-3-8", "gemini-3.8-flash", "US$ 0.00825", "$ 7.425"),
        )
        for alias, modelo, usd, clp in casos:
            with self.subTest(modelo=alias):
                self.post.reset_mock()
                respuesta = self.client.post(
                    "/consultar", headers=self.headers, json={**self.cuerpo, "modelo": alias}
                )
                detalles = self.assertRespuesta(respuesta, 200)
                self.post.assert_called_once()
                self.assertEqual(self.post.call_args.kwargs["json"]["model"], modelo)
                self.assertEqual(detalles["uso"], self.resultado["uso"])
                self.assertEqual(detalles["costo_estimado"]["modelo"], modelo)
                self.assertEqual(detalles["costo_estimado"]["usd"]["total"], usd)
                self.assertEqual(detalles["costo_estimado"]["clp"]["total"], clp)

    def test_otro_agente_usa_su_propio_cliente_y_modelo(self):
        cliente = Mock(return_value=Resultado(respuesta="Respuesta de otro agente"))
        catalogo = {"otro": {"clave": "OTRO_API_KEY", "modelos": {"basico": "modelo-real"}}}
        with (
            patch.dict(AGENTES, catalogo),
            patch.dict(CLIENTES, {"otro": cliente}),
            patch.dict(os.environ, {"OTRO_API_KEY": "clave-otro-ficticia"}),
        ):
            cuerpo = {"agente": "otro", "modelo": "basico", "mensaje": "Hola"}
            respuesta = self.client.post("/consultar", headers=self.headers, json=cuerpo)
        detalles = self.assertRespuesta(respuesta, 200)
        cliente.assert_called_once_with("modelo-real", "Hola")
        self.post.assert_not_called()
        self.assertEqual(
            detalles,
            {"respuesta": "Respuesta de otro agente", "uso": None, "costo_estimado": None},
        )

    def test_mensaje_original_se_conserva(self):
        contenido = "  primera línea\n    segunda línea  "
        cuerpo = {**self.cuerpo, "mensaje": contenido}
        respuesta = self.client.post("/consultar", headers=self.headers, json=cuerpo)
        detalles = self.assertRespuesta(respuesta, 200)
        enviado = self.post.call_args.kwargs["json"]
        self.assertEqual(enviado["messages"][0]["content"], contenido)
        self.assertEqual(detalles, self.resultado)
