"""Conversión a CLP con una tasa pública o configurada localmente."""

import os
from decimal import Decimal
from unittest.mock import patch

import requests

from src.tipo_cambio import CACHE_SEGUNDOS, ENDPOINT_DOLAR, consultar_dolar
from tests.base import CasoAPI


class TipoCambioTests(CasoAPI):
    def test_consulta_dolar_sin_enviar_credenciales_ni_el_mensaje(self):
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        self.assertEqual(self.assertRespuesta(respuesta, 200), self.resultado)
        self.get.assert_called_once_with(ENDPOINT_DOLAR, timeout=(3, 5), allow_redirects=False)
        self.dolar.json.assert_called_once_with(parse_float=Decimal)

    def test_tasa_configurada_se_aplica_sin_consultar_la_fuente_publica(self):
        with patch.dict(os.environ, {"USD_CLP": "950"}):
            respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        costo = self.assertRespuesta(respuesta, 200)["costo_estimado"]
        self.assertEqual(
            costo["clp"],
            {"moneda": "CLP", "entrada": "$ 0.285", "salida": "$ 4.75", "total": "$ 5.035"},
        )
        self.assertEqual(
            costo["tipo_cambio"],
            {"clp_por_usd": "950.00", "fecha": None, "fuente": "USD_CLP (.env)"},
        )
        self.assertEqual(
            costo["tarifas_por_millon_clp"],
            {"entrada": "$ 285.00", "entrada_cache": "$ 28.50", "salida": "$ 2375.00"},
        )
        self.assertIsNone(costo["aviso_clp"])
        self.get.assert_not_called()

    def test_tasa_con_decimales_se_conserva_sin_redondear_el_costo(self):
        self.dolar.json.return_value["valor"] = Decimal("981.65")
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        costo = self.assertRespuesta(respuesta, 200)["costo_estimado"]
        self.assertEqual(costo["tipo_cambio"]["clp_por_usd"], "981.65")
        self.assertEqual(costo["clp"]["total"], "$ 5.202745")
        self.assertEqual(
            costo["tarifas_por_millon_clp"],
            {"entrada": "$ 294.495", "entrada_cache": "$ 29.4495", "salida": "$ 2454.125"},
        )
        self.assertIsNone(costo["aviso_clp"])

    def test_tasa_configurada_invalida_no_descarta_el_texto_ni_el_costo_usd(self):
        for valor in ("0", "-900", "abc", "NaN", "Infinity", "950,50"):
            with self.subTest(valor=valor), patch.dict(os.environ, {"USD_CLP": valor}):
                respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
                detalles = self.assertRespuesta(respuesta, 200)
                costo = detalles["costo_estimado"]
                self.assertEqual(detalles["respuesta"], "Respuesta simulada")
                self.assertEqual(costo["usd"], self.resultado["costo_estimado"]["usd"])
                self.assertIsNone(costo["clp"])
                self.assertIsNone(costo["tipo_cambio"])
                self.assertIsNone(costo["tarifas_por_millon_clp"])
                self.assertIn("USD_CLP debe ser", costo["aviso_clp"])
        self.get.assert_not_called()

    def test_fuente_no_disponible_conserva_resultado_y_explica_como_configurar_clp(self):
        self.get.side_effect = requests.exceptions.Timeout()
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 200)
        costo = detalles["costo_estimado"]
        self.assertEqual(detalles["respuesta"], "Respuesta simulada")
        self.assertEqual(costo["usd"], self.resultado["costo_estimado"]["usd"])
        self.assertIsNone(costo["clp"])
        self.assertIsNone(costo["tipo_cambio"])
        self.assertIsNone(costo["tarifas_por_millon_clp"])
        self.assertIn("Configura USD_CLP", costo["aviso_clp"])

    def test_metadatos_invalidos_del_dolar_no_producen_conversion(self):
        casos = [None, {}, {"indicador": "euro"}, {"indicador": "dolar"}]
        for valor in (None, True, 0, -900, "NaN", "Infinity"):
            casos.append({"indicador": "dolar", "fecha": "2026-10-19", "valor": valor})
        casos.append({"indicador": "dolar", "fecha": "invalida", "valor": 900})
        casos.append({"indicador": "dolar", "fecha": None, "valor": 900})
        for datos in casos:
            with self.subTest(datos=datos):
                consultar_dolar.cache_clear()
                self.dolar.json.return_value = datos
                respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
                costo = self.assertRespuesta(respuesta, 200)["costo_estimado"]
                self.assertIsNone(costo["clp"])
                self.assertIsNone(costo["tarifas_por_millon_clp"])
                self.assertIsNotNone(costo["aviso_clp"])

    def test_error_http_o_json_invalido_del_dolar_no_descarta_la_consulta(self):
        self.dolar.status_code = 503
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        self.assertIsNone(self.assertRespuesta(respuesta, 200)["costo_estimado"]["clp"])
        self.dolar.json.assert_not_called()

        self.dolar.status_code = 200
        self.dolar.json.side_effect = requests.exceptions.JSONDecodeError("JSON inválido", "", 0)
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        self.assertIsNone(self.assertRespuesta(respuesta, 200)["costo_estimado"]["clp"])

    def test_tasa_se_reutiliza_y_se_actualiza_al_vencer_cache(self):
        for instante in (0, 1, CACHE_SEGUNDOS):
            with patch("src.tipo_cambio.monotonic", return_value=instante):
                respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
                self.assertRespuesta(respuesta, 200)
        self.assertEqual(self.get.call_count, 2)
