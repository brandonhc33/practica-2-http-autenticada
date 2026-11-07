import os
import unittest
import warnings
from collections.abc import Iterator
from decimal import Decimal
from unittest.mock import patch

from google.genai import types
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from src.costos.registro import sesion_costos
from src.orquestacion.modelo import RegistroLlamadas, crear_modelo

GENERAR_EN_SDK = "google.genai.models.Models.generate_content"
RESPUESTA_SDK = types.GenerateContentResponse(
    candidates=[
        types.Candidate(
            content=types.Content(role="model", parts=[types.Part(text="hola")]),
            finish_reason=types.FinishReason.STOP,
        )
    ],
    usage_metadata=types.GenerateContentResponseUsageMetadata(
        prompt_token_count=1_000,
        cached_content_token_count=100,
        candidates_token_count=500,
        thoughts_token_count=1_500,
        total_token_count=3_000,
    ),
)


class TestRegistroLlamadas(unittest.TestCase):
    def test_registro_cuenta_respuestas_y_fallos(self):
        def fallar() -> Iterator[AIMessage]:
            raise ConnectionError("simulado")
            yield  # Convierte la función en un generador: falla al pedir la respuesta.

        uso = {"input_tokens": 1_000, "output_tokens": 2_000, "total_tokens": 3_000}
        registro_llamadas = RegistroLlamadas("gemini-3.5-flash-lite")
        modelo_correcto = GenericFakeChatModel(
            messages=iter([AIMessage(content="ok", usage_metadata=uso)]),
            callbacks=[registro_llamadas],
        )
        modelo_roto = GenericFakeChatModel(messages=fallar(), callbacks=[registro_llamadas])

        with sesion_costos() as registro:
            modelo_correcto.invoke("hola")
            with self.assertRaises(ConnectionError):
                modelo_roto.invoke("hola")

        resumen = registro.resumen()
        self.assertEqual(resumen.respuestas_con_costo, 1)
        self.assertEqual(resumen.consultas_fallidas, 1)
        self.assertEqual(resumen.intentos_http, 2)
        self.assertEqual(resumen.intentos_sin_uso, 1)
        self.assertEqual(resumen.tokens_total, 3_000)
        self.assertEqual(resumen.costo_conocido_usd, Decimal("0.0053"))

    def test_respuesta_sin_uso_queda_sin_costo(self):
        modelo = GenericFakeChatModel(
            messages=iter([AIMessage(content="ok")]),
            callbacks=[RegistroLlamadas("gemini-3.5-flash-lite")],
        )

        with sesion_costos() as registro:
            modelo.invoke("hola")

        resumen = registro.resumen()
        self.assertEqual(resumen.respuestas_sin_costo, 1)
        self.assertEqual(resumen.intentos_sin_uso, 1)
        self.assertEqual(resumen.tokens_total, 0)


class TestCrearModelo(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"GEMINI_API_KEY": "clave-ficticia"}, clear=True))

    def test_crear_modelo_limita_reintentos_y_tiempo(self):
        for alias, nombre in (
            ("flash-lite", "gemini-3.5-flash-lite"),
            ("flash", "gemini-3.6-flash"),
        ):
            with self.subTest(alias=alias):
                modelo = crear_modelo(alias)
                self.assertEqual(modelo.model, nombre)
                self.assertEqual(modelo.max_retries, 1)
                self.assertEqual(modelo.timeout, 30)
                assert isinstance(modelo.callbacks, list)
                callback = modelo.callbacks[0]
                assert isinstance(callback, RegistroLlamadas)
                self.assertEqual(callback.nombre_modelo, nombre)
        self.assertEqual(crear_modelo().model, "gemini-3.5-flash-lite")

    def test_modelo_envia_limites_sin_temperatura(self):
        for alias in ("flash-lite", "flash"):
            with (
                self.subTest(alias=alias),
                patch(GENERAR_EN_SDK, return_value=RESPUESTA_SDK) as generar,
                warnings.catch_warnings(record=True) as avisos,
            ):
                warnings.simplefilter("always")
                crear_modelo(alias).invoke("hola")

                config = generar.call_args.kwargs["config"]
                self.assertEqual(config.http_options.timeout, 30_000)
                self.assertEqual(config.http_options.retry_options.attempts, 1)
                self.assertIsNone(config.temperature)
                self.assertEqual(avisos, [])

    def test_registro_incluye_razonamiento_y_cache(self):
        with sesion_costos() as registro, patch(GENERAR_EN_SDK, return_value=RESPUESTA_SDK):
            crear_modelo().invoke("hola")

        resumen = registro.resumen()
        self.assertEqual(resumen.tokens_entrada, 1_000)
        self.assertEqual(resumen.tokens_salida, 2_000)
        # (900 x 0,30 + 100 x 0,03 + 2.000 x 2,50) / 1.000.000
        self.assertEqual(resumen.costo_conocido_usd, Decimal("0.005273"))
