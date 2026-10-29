"""Costo conocido, aislamiento y contabilización sin modificar la salida del cliente."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest.mock import patch

import requests

from src.agente_gemini import consultar_gemini_raw
from src.costos import calcular_costo_usd_gemini
from src.esquemas import UsoTokens
from src.registro_costos import RegistroCostosSesion, obtener_registro_costos, sesion_costos
from tests.base import CasoAPI

MODELO = "gemini-3.5-flash-lite"


class RegistroCostosTests(unittest.TestCase):
    def setUp(self):
        self.uso = UsoTokens(entrada=1_000, salida=2_000, total=3_000)
        self.costo = calcular_costo_usd_gemini(MODELO, self.uso)
        self.registro = RegistroCostosSesion()

    def test_dos_operaciones_acumulan_importes_y_tokens_exactos(self):
        for _ in range(2):
            self.registro.registrar_respuesta(self.uso, self.costo, intentos=1)
        resumen = self.registro.resumen()
        self.assertEqual(resumen.costo_conocido_usd, Decimal("0.0106"))
        self.assertEqual(resumen.respuestas_con_costo, 2)
        self.assertEqual(resumen.tokens_total, 6_000)
        self.assertEqual(resumen.intentos_http, 2)
        self.assertEqual(resumen.intentos_sin_uso, 0)
        self.assertEqual(resumen.como_dict()["costo_conocido_usd"], "0.0106")

    def test_consumo_cero_es_distinto_de_respuesta_sin_consumo(self):
        cero = UsoTokens(entrada=0, salida=0, total=0)
        self.registro.registrar_respuesta(cero, calcular_costo_usd_gemini(MODELO, cero), intentos=1)
        self.registro.registrar_respuesta(None, None, intentos=1)
        resumen = self.registro.resumen()
        self.assertEqual(resumen.costo_conocido_usd, Decimal("0"))
        self.assertEqual(resumen.respuestas_con_costo, 1)
        self.assertEqual(resumen.respuestas_sin_costo, 1)
        self.assertEqual(resumen.intentos_sin_uso, 1)

    def test_modelo_sin_tarifa_conserva_tokens_y_costo_desconocido(self):
        self.registro.registrar_respuesta(
            self.uso, calcular_costo_usd_gemini("sin-tarifa", self.uso), intentos=1
        )
        resumen = self.registro.resumen()
        self.assertEqual(resumen.tokens_total, 3_000)
        self.assertEqual(resumen.respuestas_sin_costo, 1)
        self.assertEqual(resumen.respuestas_con_costo, 0)
        self.assertEqual(resumen.intentos_sin_uso, 0)

    def test_fallo_cuenta_intentos_sin_inventar_importes(self):
        self.registro.registrar_fallo(intentos=3)
        resumen = self.registro.resumen()
        self.assertEqual(resumen.consultas_fallidas, 1)
        self.assertEqual(resumen.intentos_http, 3)
        self.assertEqual(resumen.intentos_sin_uso, 3)
        self.assertEqual(resumen.respuestas_con_costo, 0)

    def test_cada_resumen_es_una_instantanea(self):
        previo = self.registro.resumen()
        self.registro.registrar_respuesta(self.uso, self.costo, intentos=1)
        self.assertEqual(previo.costo_conocido_usd, Decimal("0"))
        self.assertEqual(self.registro.resumen().costo_conocido_usd, Decimal("0.0053"))

    def test_sesiones_anidadas_son_independientes_y_restauran_el_contexto(self):
        original = obtener_registro_costos()
        with sesion_costos() as exterior:
            exterior.registrar_respuesta(self.uso, self.costo, intentos=1)
            with sesion_costos() as interior:
                self.assertIs(obtener_registro_costos(), interior)
                self.assertEqual(interior.resumen().costo_conocido_usd, Decimal("0"))
                interior.registrar_fallo(intentos=1)
            self.assertIs(obtener_registro_costos(), exterior)
            self.assertEqual(exterior.resumen().consultas_fallidas, 0)
            self.assertEqual(exterior.resumen().costo_conocido_usd, Decimal("0.0053"))
        self.assertIs(obtener_registro_costos(), original)

    def test_registro_compartido_entre_hilos_no_pierde_sumas(self):
        def registrar(_):
            self.registro.registrar_respuesta(self.uso, self.costo, intentos=1)

        with ThreadPoolExecutor(max_workers=4) as ejecutor:
            list(ejecutor.map(registrar, range(100)))
        resumen = self.registro.resumen()
        self.assertEqual(resumen.respuestas_con_costo, 100)
        self.assertEqual(resumen.costo_conocido_usd, Decimal("0.53"))

    def test_calculo_usd_no_consulta_el_dolar_y_descuenta_la_cache(self):
        uso = UsoTokens(entrada=1_000, salida=2_000, total=3_000, entrada_cache=400)
        with patch("src.costos.obtener_tipo_cambio") as cambio:
            costo = calcular_costo_usd_gemini(MODELO, uso)
        self.assertIsNotNone(costo)
        assert costo is not None
        self.assertEqual(costo.total, Decimal("0.005192"))
        cambio.assert_not_called()


class RegistroClienteTests(CasoAPI):
    def test_consultas_normal_y_raw_comparten_sesion_sin_cambiar_sus_respuestas(self):
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        self.assertEqual(self.assertRespuesta(respuesta, 200), self.resultado)
        self.get.reset_mock()
        respuesta_raw = self.client.post("/consultar/raw", headers=self.headers, json=self.cuerpo)
        self.assertEqual(respuesta_raw.json(), self.upstream.json.return_value)
        self.get.assert_not_called()
        resumen = self.registro_costos.resumen()
        self.assertEqual(resumen.respuestas_con_costo, 2)
        self.assertEqual(resumen.costo_conocido_usd, Decimal("0.0106"))

    def test_recuperacion_429_503_200_registra_el_costo_una_sola_vez(self):
        codigos = iter((429, 503, 200))

        def siguiente(*args, **kwargs):
            self.upstream.status_code = next(codigos)
            return self.post.return_value

        self.post.side_effect = siguiente
        consultar_gemini_raw(MODELO, "Hola")
        resumen = self.registro_costos.resumen()
        self.assertEqual(resumen.respuestas_con_costo, 1)
        self.assertEqual(resumen.intentos_http, 3)
        self.assertEqual(resumen.intentos_sin_uso, 2)
        self.assertEqual(resumen.costo_conocido_usd, Decimal("0.0053"))
        self.get.assert_not_called()

    def test_salida_rechazada_conserva_el_consumo_reportado_por_el_proveedor(self):
        self.upstream.json.return_value["choices"][0]["finish_reason"] = "length"
        respuesta = self.client.post(
            "/consultar",
            headers=self.headers,
            json={**self.cuerpo, "prompt": "explicar_concepto"},
        )
        self.assertRespuesta(respuesta, 502)
        resumen = self.registro_costos.resumen()
        self.assertEqual(resumen.respuestas_con_costo, 1)
        self.assertEqual(resumen.tokens_total, 3_000)
        self.assertEqual(resumen.costo_conocido_usd, Decimal("0.0053"))
        self.post.assert_called_once()

    def test_agotamiento_conserva_el_contrato_y_todos_los_intentos_sin_uso(self):
        self.upstream.status_code = 429
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        self.assertRespuesta(respuesta, 503)
        resumen = self.registro_costos.resumen()
        self.assertEqual(resumen.consultas_fallidas, 1)
        self.assertEqual(resumen.intentos_http, 3)
        self.assertEqual(resumen.intentos_sin_uso, 3)
        self.assertEqual(resumen.respuestas_con_costo, 0)

    def test_timeout_de_lectura_no_reintenta_ni_inventa_costo(self):
        self.post.side_effect = requests.exceptions.ReadTimeout()
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        self.assertRespuesta(respuesta, 504)
        resumen = self.registro_costos.resumen()
        self.assertEqual(resumen.consultas_fallidas, 1)
        self.assertEqual(resumen.intentos_http, 1)
        self.assertEqual(resumen.intentos_sin_uso, 1)
        self.post.assert_called_once()

    def test_recalcular_costo_para_presentacion_no_duplica_el_registro(self):
        from src.costos import calcular_costo_gemini

        consultar_gemini_raw(MODELO, "Hola")
        uso = UsoTokens(entrada=1_000, salida=2_000, total=3_000)
        calcular_costo_gemini(MODELO, uso)
        calcular_costo_gemini(MODELO, uso)
        self.assertEqual(self.registro_costos.resumen().respuestas_con_costo, 1)
