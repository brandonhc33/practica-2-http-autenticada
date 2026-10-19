"""Costos calculados desde el consumo del proveedor, sin consultas reales a Gemini."""

import json
from io import StringIO
from unittest.mock import patch

from src.agente_gemini import main, obtener_dato_de_prueba
from tests.base import CasoAPI


class CostosGeminiTests(CasoAPI):
    def test_cache_se_descuenta_de_la_entrada_normal(self):
        self.upstream.json.return_value["usage"]["prompt_tokens_details"] = {"cached_tokens": 400}
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 200)
        self.assertEqual(detalles["uso"]["entrada_cache"], 400)
        self.assertEqual(detalles["costo_estimado"]["usd"]["entrada"], "US$ 0.000192")
        self.assertEqual(detalles["costo_estimado"]["usd"]["salida"], "US$ 0.005")
        self.assertEqual(detalles["costo_estimado"]["usd"]["total"], "US$ 0.005192")
        self.assertEqual(detalles["costo_estimado"]["clp"]["total"], "$ 4.6728")

    def test_razonamiento_se_cobra_una_sola_vez_aunque_completion_tokens_lo_omita(self):
        for salida_reportada in (1_500, 2_000):
            with self.subTest(salida_reportada=salida_reportada):
                self.upstream.json.return_value["usage"] = {
                    "prompt_tokens": 1_000,
                    "completion_tokens": salida_reportada,
                    "total_tokens": 3_000,
                    "completion_tokens_details": {"reasoning_tokens": 500},
                }
                respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
                self.assertEqual(self.assertRespuesta(respuesta, 200), self.resultado)

    def test_importes_pequenos_no_se_redondean_a_cero(self):
        self.upstream.json.return_value["usage"] = {
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
        }
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        costo = self.assertRespuesta(respuesta, 200)["costo_estimado"]
        self.assertEqual(costo["usd"]["entrada"], "US$ 0.0000003")
        self.assertEqual(costo["usd"]["salida"], "US$ 0.0000025")
        self.assertEqual(costo["usd"]["total"], "US$ 0.0000028")
        self.assertEqual(costo["clp"]["entrada"], "$ 0.00027")
        self.assertEqual(costo["clp"]["salida"], "$ 0.00225")
        self.assertEqual(costo["clp"]["total"], "$ 0.00252")
        self.assertNotRegex(respuesta.text, r"[0-9][eE][+-][0-9]")

        with (
            patch("src.agente_gemini.load_dotenv"),
            patch("sys.argv", ["src.agente_gemini", "Hola"]),
            patch("sys.stdout", new_callable=StringIO) as salida,
        ):
            main()
        self.assertIn('"US$ 0.0000003"', salida.getvalue())
        self.assertIn('"$ 0.00027"', salida.getvalue())
        self.assertNotRegex(salida.getvalue(), r"[0-9][eE][+-][0-9]")

    def test_consumo_cero_es_distinto_de_consumo_ausente(self):
        self.upstream.json.return_value["usage"] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        detalles = self.assertRespuesta(respuesta, 200)
        self.assertEqual(
            detalles["uso"], {"entrada": 0, "salida": 0, "total": 0, "entrada_cache": 0}
        )
        for campo in ("entrada", "salida", "total"):
            self.assertEqual(detalles["costo_estimado"]["usd"][campo], "US$ 0.00")
            self.assertEqual(detalles["costo_estimado"]["clp"][campo], "$ 0.00")

    def test_uso_ausente_o_invalido_conserva_texto_sin_inventar_costo(self):
        uso_valido = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        casos = [None, [], "30", {}, {"total_tokens": 30}]
        for campo in uso_valido:
            casos.append({k: v for k, v in uso_valido.items() if k != campo})
            for valor in (None, -1, "10", 1.5, True):
                casos.append({**uso_valido, campo: valor})
        casos.append({**uso_valido, "total_tokens": 29})
        for detalles in ([], "cache", {"cached_tokens": 11}, {"cached_tokens": True}):
            casos.append({**uso_valido, "prompt_tokens_details": detalles})
        for uso in casos:
            with self.subTest(uso=uso):
                self.upstream.json.return_value["usage"] = uso
                respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
                self.assertEqual(
                    self.assertRespuesta(respuesta, 200),
                    {"respuesta": "Respuesta simulada", "uso": None, "costo_estimado": None},
                )
        del self.upstream.json.return_value["usage"]
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        self.assertIsNone(self.assertRespuesta(respuesta, 200)["costo_estimado"])
        self.get.assert_not_called()

    def test_costos_corresponden_a_cada_consulta(self):
        for _ in range(2):
            respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
            self.assertEqual(self.assertRespuesta(respuesta, 200), self.resultado)
        self.assertEqual(self.post.call_count, 2)

    def test_funcion_de_prueba_devuelve_resultado_con_consumo_y_costo(self):
        with patch("src.agente_gemini.load_dotenv"):
            resultado = obtener_dato_de_prueba("¿Qué es una API?")
        self.assertEqual(resultado.model_dump(mode="json"), self.resultado)
        self.assertEqual(
            self.post.call_args.kwargs["json"]["messages"],
            [{"role": "user", "content": "¿Qué es una API?"}],
        )

    def test_comando_imprime_json_con_el_mismo_resultado_que_el_endpoint(self):
        for argumentos in ([], ["¿Qué es una API?"]):
            with (
                self.subTest(argumentos=argumentos),
                patch("src.agente_gemini.load_dotenv"),
                patch("sys.argv", ["src.agente_gemini", *argumentos]),
                patch("sys.stdout", new_callable=StringIO) as salida,
            ):
                main()
                self.assertEqual(json.loads(salida.getvalue()), self.resultado)

    def test_comando_con_error_no_publica_costo(self):
        self.upstream.status_code = 429
        with (
            patch("src.agente_gemini.load_dotenv"),
            patch("sys.argv", ["src.agente_gemini", "Hola"]),
            patch("sys.stdout", new_callable=StringIO) as salida,
        ):
            with self.assertRaisesRegex(SystemExit, "HTTP 429"):
                main()
        self.assertEqual(salida.getvalue(), "")
