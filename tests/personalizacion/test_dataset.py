"""El dataset del bloque 29 se valida sin red y el validador encuentra lo que dice encontrar."""

import json
import unittest
from collections import Counter
from unittest.mock import Mock, patch

from google.genai import types

from src.personalizacion.dataset import (
    CLAVES_SALIDA,
    MINIMO_EJEMPLOS,
    RUTAS,
    cargar_dataset,
    chequear_balance,
    comprobar_modo_desarrollador,
    construir_configuracion_peft,
    construir_ejemplos,
    ejemplos_raw,
    esperar_a_que_termine,
    generar_casos_rotos,
    referencias_disponibles,
    resumir_balance,
    revisar_dataset,
    validar_dataset,
)

Estado = types.JobState


class TestDatasetRutas(unittest.TestCase):
    def setUp(self):
        self.dataset = cargar_dataset()
        self.pares = ejemplos_raw(self.dataset)
        self.examples = construir_ejemplos(self.pares)
        self.referencias = referencias_disponibles()

    def test_dataset_real_cumple_minimos_y_no_tiene_problemas(self):
        self.assertGreaterEqual(len(self.examples), MINIMO_EJEMPLOS)
        self.assertEqual(revisar_dataset(self.examples, self.referencias), [])
        self.assertEqual(set(chequear_balance(self.pares, "ruta")), set(RUTAS))

    def test_salida_serializada_es_la_que_el_modelo_imitaria(self):
        salidas = [json.loads(e.output or "") for e in self.examples]
        self.assertTrue(all(list(s) == list(CLAVES_SALIDA) for s in salidas))
        con_tilde = next(e for e in self.examples if "Artículo" in (e.output or ""))
        self.assertNotIn("\\u", con_tilde.output or "")
        self.assertIn('"articulo": null', self.examples[0].output or "")

    def test_ids_unicos_y_reglas_documentadas(self):
        ids = [e["id"] for e in self.dataset["ejemplos"]]
        self.assertEqual(len(ids), len(set(ids)))
        reglas = {e["regla"] for e in self.dataset["ejemplos"]}
        self.assertEqual(reglas, set(self.dataset["reglas_etiquetado"]))

    def test_balance_incluye_categorias_sin_ejemplos(self):
        resumen = resumir_balance(Counter({"normativa": 4, "resumen": 2}))
        self.assertEqual(resumen["conteos"]["aclaracion"], 0)
        self.assertIsNone(resumen["razon_max_min"])
        self.assertFalse(resumen["aceptable"])
        self.assertFalse(
            resumir_balance(Counter({"normativa": 7, "resumen": 3, "aclaracion": 3}))["aceptable"]
        )
        self.assertTrue(
            resumir_balance(Counter({"normativa": 6, "resumen": 3, "aclaracion": 4}))["aceptable"]
        )

    def test_reproduce_el_dataset_roto_de_la_leccion(self):
        claves = ("categoria", "accion_sugerida")
        buenos = [
            types.TuningExample(
                text_input=f"error {i}",
                output=json.dumps({"categoria": "red", "accion_sugerida": "reintentar"}),
            )
            for i in range(8)
        ]
        rotos = buenos + [
            types.TuningExample(text_input="", output='{"categoria": "red"}'),
            types.TuningExample(text_input="error 0", output="no es json"),
        ]
        self.assertEqual(
            validar_dataset(rotos, claves),
            [
                "ejemplo 8: text_input vacio",
                'ejemplo 8: output no tiene la clave "accion_sugerida"',
                "ejemplo 9: text_input duplicado del ejemplo 0",
                "ejemplo 9: output no es JSON valido",
            ],
        )

    def test_cada_copia_rota_se_detecta(self):
        casos = generar_casos_rotos(self.examples)
        self.assertEqual(len(casos), 10)
        for descripcion, rotos in casos:
            with self.subTest(descripcion):
                self.assertTrue(revisar_dataset(rotos, self.referencias))
        self.assertEqual(
            revisar_dataset(self.examples, self.referencias), [], "No modifica el original."
        )

    def test_duplicado_normalizado_con_otra_etiqueta_es_contradiccion(self):
        ejemplos = [
            types.TuningExample(
                text_input="¿Qué dice la ley?", output='{"ruta": "normativa", "articulo": null}'
            ),
            types.TuningExample(
                text_input="QUÉ DICE LA LEY", output='{"ruta": "aclaracion", "articulo": null}'
            ),
        ]
        self.assertEqual(
            validar_dataset(ejemplos), ["ejemplo 1: contradice la etiqueta del ejemplo 0"]
        )

    def test_reglas_de_ruta_y_articulo(self):
        ejemplos = [
            types.TuningExample(
                text_input="a", output='{"ruta": "aclaracion", "articulo": "Artículo 9"}'
            ),
            types.TuningExample(
                text_input="b", output='{"ruta": "resumen", "articulo": "Artículo 9"}'
            ),
            types.TuningExample(
                text_input="c" * 301, output='{"ruta": "normativa", "articulo": null}'
            ),
        ]
        problemas = revisar_dataset(ejemplos, self.referencias)
        self.assertIn("ejemplo 0: una ruta aclaracion no lleva articulo (R3)", problemas)
        self.assertIn("ejemplo 2: text_input supera 300 caracteres", problemas)
        self.assertFalse(any(p.startswith("ejemplo 1") for p in problemas))


class TestTrabajoDeTuning(unittest.TestCase):
    def test_peft_se_rechaza_en_modo_desarrollador_sin_red(self):
        config = construir_configuracion_peft()
        self.assertEqual(config.tuning_mode, types.TuningMode.TUNING_MODE_PEFT_ADAPTER)
        self.assertEqual(config.adapter_size, types.AdapterSize.ADAPTER_SIZE_FOUR)
        motivo = comprobar_modo_desarrollador(config)
        self.assertIsNotNone(motivo)
        self.assertIn("adapter_size", motivo or "")
        self.assertIn("Enterprise Agent Platform", motivo or "")

    def test_configuracion_sin_parametros_peft_no_tiene_rechazo_local(self):
        config = types.CreateTuningJobConfig(epoch_count=3, tuned_model_display_name="prueba")
        self.assertIsNone(comprobar_modo_desarrollador(config))

    def cliente_con_estados(self, *estados: types.JobState) -> Mock:
        cliente = Mock()
        cliente.tunings.get.side_effect = [types.TuningJob(name="t", state=e) for e in estados]
        return cliente

    def test_espera_consulta_con_get_hasta_estado_final(self):
        cliente = self.cliente_con_estados(
            Estado.JOB_STATE_QUEUED, Estado.JOB_STATE_RUNNING, Estado.JOB_STATE_SUCCEEDED
        )
        pausas: list[float] = []
        with patch("builtins.print"):
            trabajo = esperar_a_que_termine(cliente, "t", 5, dormir=pausas.append)
        self.assertEqual(trabajo.state, Estado.JOB_STATE_SUCCEEDED)
        self.assertEqual(pausas, [5, 5])
        cliente.tunings.get.assert_called_with(name="t")
        cliente.tunings.tune.assert_not_called()

    def test_un_trabajo_vencido_tambien_termina_la_espera(self):
        cliente = self.cliente_con_estados(Estado.JOB_STATE_RUNNING, Estado.JOB_STATE_EXPIRED)
        with patch("builtins.print"):
            trabajo = esperar_a_que_termine(cliente, "t", 1, dormir=lambda _: None)
        self.assertEqual(trabajo.state, Estado.JOB_STATE_EXPIRED)

    def test_espera_maxima_avisa_sin_cancelar(self):
        cliente = self.cliente_con_estados(*[Estado.JOB_STATE_RUNNING] * 3)
        tiempos = iter([0.0, 10.0, 20.0, 30.0])
        with patch("builtins.print"), self.assertRaisesRegex(TimeoutError, "cancel"):
            esperar_a_que_termine(
                cliente, "t", 10, 15, dormir=lambda _: None, reloj=lambda: next(tiempos)
            )
        cliente.tunings.cancel.assert_not_called()
