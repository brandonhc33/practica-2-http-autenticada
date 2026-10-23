"""El evaluador conserva evidencia y calcula métricas sin llamadas reales ni cobros."""

import os
import unittest
from collections import Counter
from copy import deepcopy
from decimal import Decimal
from unittest.mock import Mock, patch

from src.comparar_modelos import (
    CASOS,
    MODELOS_CANDIDATOS,
    listar_modelos_disponibles,
    medir_consulta,
    planificar,
    resumir,
    resumir_pares_completos,
)
from src.esquemas import TipoCambio
from src.reintentos import SIN_REINTENTOS


class ComparacionModelosTests(unittest.TestCase):
    def setUp(self):
        self.raw = self.enterContext(patch("src.comparar_modelos.consultar_gemini_raw"))
        self.raw.return_value = {
            "model": MODELOS_CANDIDATOS[0],
            "choices": [{"message": {"content": "Respuesta"}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 1500,
                "total_tokens": 3000,
                "prompt_tokens_details": {"cached_tokens": 400},
                "completion_tokens_details": {"reasoning_tokens": 500},
            },
        }
        self.reloj = self.enterContext(patch("src.comparar_modelos.perf_counter"))
        self.reloj.side_effect = [100.0, 102.5]
        self.cambio = self.enterContext(patch("src.costos.obtener_tipo_cambio"))
        self.cambio.return_value = TipoCambio(
            clp_por_usd=Decimal("950"), fecha=None, fuente="Prueba unitaria"
        )

    def test_mide_una_llamada_y_cobra_cache_y_razonamiento_con_tarifa_de_cada_modelo(self):
        for modelo, esperado in zip(MODELOS_CANDIDATOS, ("0.005192", "0.00798"), strict=True):
            with self.subTest(modelo=modelo):
                self.reloj.side_effect = [100.0, 102.5]
                self.raw.reset_mock()
                registro = medir_consulta(modelo, "Pregunta idéntica")
                self.assertEqual(registro["latencia_segundos"], 2.5)
                self.assertEqual(registro["estado"], "ok")
                self.assertEqual(registro["uso"]["salida"], 2000)
                self.assertEqual(registro["costo_usd"], esperado)
                self.assertEqual(Decimal(registro["costo_clp"]), Decimal(esperado) * 950)
                self.assertEqual(registro["respuesta_proveedor"], self.raw.return_value)
                self.raw.assert_called_once_with(
                    modelo, "Pregunta idéntica", politica=SIN_REINTENTOS
                )

    def test_error_no_inventa_costo_ni_se_reintenta(self):
        self.raw.side_effect = ValueError("Gemini respondió HTTP 429.")
        registro = medir_consulta(MODELOS_CANDIDATOS[0], "Pregunta")
        self.assertEqual(registro["estado"], "error")
        self.assertIn("HTTP 429", registro["error"])
        self.assertIsNone(registro["costo_usd"])
        self.assertIsNone(registro["uso"])
        self.raw.assert_called_once()
        self.cambio.assert_not_called()

    def test_respuesta_truncada_conserva_consumo_pero_no_cuenta_como_completa(self):
        self.raw.return_value["choices"][0]["finish_reason"] = "length"
        registro = medir_consulta(MODELOS_CANDIDATOS[0], "Pregunta")
        self.assertEqual(registro["estado"], "incompleta")
        self.assertEqual(registro["costo_usd"], "0.005192")
        resumen = resumir([registro], [MODELOS_CANDIDATOS[0]])[MODELOS_CANDIDATOS[0]]
        self.assertEqual(resumen["respuestas_completas"], 0)
        self.assertIsNone(resumen["latencia_media_segundos"])
        self.assertIsNone(resumen["costo_medio_usd"])
        self.assertEqual(resumen["costo_observado_total_usd"], "0.005192")

    def test_interrupcion_conserva_intento_con_costo_desconocido(self):
        self.raw.side_effect = KeyboardInterrupt()
        registro = medir_consulta(MODELOS_CANDIDATOS[0], "Pregunta")
        self.assertEqual(registro["estado"], "interrumpida")
        self.assertIsNone(registro["costo_usd"])
        self.assertEqual(registro["latencia_segundos"], 2.5)
        self.raw.assert_called_once()

    def test_sin_uso_o_conversion_no_inventa_datos(self):
        self.raw.return_value.pop("usage")
        registro = medir_consulta(MODELOS_CANDIDATOS[0], "Pregunta")
        self.assertEqual(registro["estado"], "incompleta")
        self.assertIsNone(registro["costo_usd"])
        self.cambio.assert_not_called()

    def test_fallo_del_dolar_conserva_medicion_y_costo_usd(self):
        self.cambio.side_effect = ValueError("Dólar no disponible")
        registro = medir_consulta(MODELOS_CANDIDATOS[0], "Pregunta")
        self.assertEqual(registro["estado"], "ok")
        self.assertEqual(registro["costo_usd"], "0.005192")
        self.assertIsNone(registro["costo_clp"])
        self.assertIsNone(registro["tipo_cambio"])
        self.assertIn("Dólar no disponible", registro["aviso_clp"])

    def test_promedios_usan_consultas_completas_y_conservan_errores_separados(self):
        uno = medir_consulta(MODELOS_CANDIDATOS[0], "Pregunta")
        dos = deepcopy(uno)
        dos.update(latencia_segundos=7.5, costo_usd="0.004808", costo_clp="4.5676")
        error = deepcopy(uno)
        error.update(estado="error", latencia_segundos=60, costo_usd=None, costo_clp=None)
        resumen = resumir([uno, dos, error], list(MODELOS_CANDIDATOS))
        valores = resumen[MODELOS_CANDIDATOS[0]]
        self.assertEqual(valores["intentos"], 3)
        self.assertEqual(valores["respuestas_completas"], 2)
        self.assertEqual(valores["errores_o_incompletas"], 1)
        self.assertEqual(valores["latencia_media_segundos"], 5)
        self.assertEqual(valores["latencia_mediana_segundos"], 5)
        self.assertEqual(valores["costo_medio_usd"], "0.005")
        self.assertEqual(valores["costo_observado_total_usd"], "0.01")
        self.assertEqual(valores["proyeccion_1000_consultas_usd"], "5.00")
        self.assertIsNone(resumen[MODELOS_CANDIDATOS[1]]["costo_observado_total_usd"])

    def test_mismos_casos_y_repeticiones_para_todos_los_modelos(self):
        plan = list(planificar(list(MODELOS_CANDIDATOS), 3))
        conteo = Counter((modelo, caso) for _, caso, modelo, _ in plan)
        self.assertEqual(len(plan), 18)
        for modelo in MODELOS_CANDIDATOS:
            for caso, mensaje in CASOS.items():
                self.assertEqual(conteo[modelo, caso], 3)
                self.assertTrue(all(texto == mensaje for _, c, _, texto in plan if c == caso))
        self.assertNotEqual(plan[0][2], plan[2][2])

    def test_pares_excluyen_la_contraparte_de_un_fallo_para_comparar_mismas_preguntas(self):
        uno = medir_consulta(MODELOS_CANDIDATOS[0], "Pregunta")
        uno.update(ronda=1, caso="explicacion_api")
        dos = {**uno, "modelo": MODELOS_CANDIDATOS[1]}
        tres = {**uno, "caso": "errores_http", "latencia_segundos": 50}
        cuatro = {**dos, "caso": "errores_http", "estado": "error"}
        resumen = resumir_pares_completos([uno, dos, tres, cuatro], list(MODELOS_CANDIDATOS))
        for modelo in MODELOS_CANDIDATOS:
            self.assertEqual(resumen[modelo]["respuestas_completas"], 1)
            self.assertEqual(resumen[modelo]["latencia_media_segundos"], 2.5)

    def test_inventario_pagina_y_no_expone_clave_en_url_o_resultado(self):
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "secreto-de-prueba"}),
            patch("src.comparar_modelos.requests.get") as get,
        ):
            paginas = []
            for datos in (
                {"models": [{"name": "models/a"}], "nextPageToken": "pagina-dos"},
                {"models": [{"name": "models/b"}]},
            ):
                respuesta = Mock(status_code=200)
                respuesta.json.return_value = datos
                contexto = Mock()
                contexto.__enter__ = Mock(return_value=respuesta)
                contexto.__exit__ = Mock(return_value=False)
                paginas.append(contexto)
            get.side_effect = paginas
            modelos = listar_modelos_disponibles()
        self.assertEqual([m["name"] for m in modelos], ["models/a", "models/b"])
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args.kwargs["params"]["pageToken"], "pagina-dos")
        self.assertNotIn("secreto-de-prueba", str(modelos))
        self.assertNotIn("secreto-de-prueba", get.call_args.args[0])
