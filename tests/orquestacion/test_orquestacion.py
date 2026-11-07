import io
import os
import unittest
import warnings
from collections.abc import Iterator
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from unittest.mock import MagicMock, patch

from google.genai import types
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from src.costos.registro import sesion_costos
from src.orquestacion.cadena_tres_pasos import construir_cadena
from src.orquestacion.enrutamiento import (
    MENSAJE_SEGURO,
    MENSAJE_VACIO,
    TEXTO_RESPALDO,
    construir_cadena_con_enrutamiento,
    construir_ruta_segura,
    main,
    procesar_consulta_segura,
)
from src.orquestacion.modelo import RegistroLlamadas, crear_modelo

ENRUTAMIENTO = "src.orquestacion.enrutamiento"
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


def fallar_por_conexion(_: object) -> str:
    raise ConnectionError("simulado")


def fallar_por_tiempo(_: object) -> str:
    raise TimeoutError("simulado")


def crear_modelo_de_tres_pasos() -> MagicMock:
    """El side_effect va en el mock mismo: LangChain lo llama como función, no con invoke."""
    return MagicMock(
        side_effect=[
            AIMessage(content="salida del paso 1"),
            AIMessage(content="salida del paso 2"),
            AIMessage(content="- respuesta del secundario"),
        ]
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


class TestRutaSegura(unittest.TestCase):
    def test_camino_normal_no_usa_respaldo(self):
        alternativa = MagicMock(return_value="respuesta del secundario")
        ruta = construir_ruta_segura(RunnableLambda(lambda _: "respuesta normal"), alternativa)

        with self.assertNoLogs(ENRUTAMIENTO, level="ERROR"):
            resultado = ruta.invoke({"mensaje": "hola"})

        self.assertEqual(resultado, "respuesta normal")
        alternativa.assert_not_called()

    def test_cadena_normativa_usa_fallback_ante_fallo_del_modelo(self):
        secundario = crear_modelo_de_tres_pasos()
        ruta = construir_ruta_segura(
            construir_cadena(RunnableLambda(fallar_por_conexion)), construir_cadena(secundario)
        )

        with self.assertLogs(ENRUTAMIENTO, level="ERROR"):
            resultado = ruta.invoke({"mensaje": "¿Quién fija las metas?"})

        self.assertEqual(resultado, "- respuesta del secundario")
        self.assertEqual(secundario.call_count, 3)

    def test_fallback_registra_el_fallo_del_modelo_principal(self):
        ruta = construir_ruta_segura(
            RunnableLambda(fallar_por_conexion), RunnableLambda(lambda _: "respuesta")
        )

        with self.assertLogs(ENRUTAMIENTO, level="ERROR") as registros:
            ruta.invoke({"mensaje": "hola"})

        self.assertEqual(len(registros.records), 1)
        self.assertIn("ConnectionError", registros.output[0])
        self.assertIn("simulado", registros.output[0])

    def test_ruta_usa_texto_de_respaldo_si_fallan_ambos_modelos(self):
        ruta = construir_ruta_segura(
            RunnableLambda(fallar_por_conexion), RunnableLambda(fallar_por_tiempo)
        )

        with self.assertLogs(ENRUTAMIENTO, level="ERROR") as registros:
            resultado = ruta.invoke({"mensaje": "hola"})

        self.assertEqual(resultado, TEXTO_RESPALDO)
        self.assertIn("no existan obligaciones", " ".join(resultado.split()))
        self.assertEqual(len(registros.records), 2)
        self.assertIn("ConnectionError", registros.output[0])
        self.assertIn("TimeoutError", registros.output[1])

    def test_ruta_sin_alternativa_usa_texto_de_respaldo(self):
        ruta = construir_ruta_segura(RunnableLambda(fallar_por_conexion))

        with self.assertLogs(ENRUTAMIENTO, level="ERROR"):
            self.assertEqual(ruta.invoke({"mensaje": "hola"}), TEXTO_RESPALDO)

    def test_respuesta_vacia_activa_el_fallback(self):
        principal = MagicMock(
            side_effect=[AIMessage(content="salida del paso 1"), AIMessage(content="")]
        )
        secundario = crear_modelo_de_tres_pasos()
        ruta = construir_ruta_segura(construir_cadena(principal), construir_cadena(secundario))

        with self.assertLogs(ENRUTAMIENTO, level="ERROR") as registros:
            resultado = ruta.invoke({"mensaje": "hola"})

        self.assertEqual(resultado, "- respuesta del secundario")
        # Sin exigir_texto, el paso 3 habría escrito una respuesta a partir de nada.
        self.assertEqual(principal.call_count, 2)
        self.assertIn("ValueError", registros.output[0])


class TestProcesarConsultaSegura(unittest.TestCase):
    def test_procesar_consulta_segura_no_propaga_excepciones(self):
        clasificacion_falsa = MagicMock(side_effect=ConnectionError("simulado"))
        cadena = construir_cadena_con_enrutamiento(clasificacion_falsa)

        with self.assertLogs(ENRUTAMIENTO, level="ERROR") as registros:
            resultado = procesar_consulta_segura(cadena, "mensaje de prueba")

        self.assertEqual(resultado, MENSAJE_SEGURO)
        self.assertIn("ConnectionError", registros.output[0])
        self.assertIn("simulado", registros.output[0])

    def test_consulta_vacia_no_llama_al_modelo(self):
        for mensaje in ("", "   \n"):
            with self.subTest(mensaje=mensaje):
                clasificacion_falsa = MagicMock(return_value="normativa")
                cadena = construir_cadena_con_enrutamiento(clasificacion_falsa)

                resultado = procesar_consulta_segura(cadena, mensaje)

                self.assertEqual(resultado, MENSAJE_VACIO)
                clasificacion_falsa.assert_not_called()

    def test_registro_no_incluye_la_consulta_y_traza_solo_en_debug(self):
        cadena = RunnableLambda(fallar_por_conexion)

        with self.assertLogs(ENRUTAMIENTO, level="DEBUG") as registros:
            procesar_consulta_segura(cadena, "consulta-privada")

        error, traza = registros.records
        self.assertEqual((error.levelname, traza.levelname), ("ERROR", "DEBUG"))
        self.assertIsNone(error.exc_info)
        self.assertIsNotNone(traza.exc_info)
        self.assertNotIn("consulta-privada", "\n".join(registros.output))


class TestMain(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("sys.argv", ["enrutamiento", "¿Cuál es la capital de Francia?"]))
        self.enterContext(patch(f"{ENRUTAMIENTO}.load_dotenv"))
        self.enterContext(patch(f"{ENRUTAMIENTO}.logging.basicConfig"))

    def test_main_imprime_respuesta_y_consumo(self):
        uso = {"input_tokens": 1_000, "output_tokens": 2_000, "total_tokens": 3_000}
        modelo_falso = GenericFakeChatModel(
            messages=iter(
                [
                    AIMessage(content="aclaracion", usage_metadata=uso),
                    AIMessage(content="¿Qué necesitas revisar?", usage_metadata=uso),
                ]
            ),
            callbacks=[RegistroLlamadas("gemini-3.5-flash-lite")],
        )
        salida, errores = io.StringIO(), io.StringIO()

        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "clave-ficticia"}, clear=True),
            patch(f"{ENRUTAMIENTO}.crear_modelo", return_value=modelo_falso),
            redirect_stdout(salida),
            redirect_stderr(errores),
        ):
            main()

        self.assertEqual(salida.getvalue().strip(), "¿Qué necesitas revisar?")
        self.assertIn("'respuestas_con_costo': 2", errores.getvalue())
        self.assertIn("'tokens_total': 6000", errores.getvalue())

    def test_main_sin_clave_termina_con_mensaje(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch(f"{ENRUTAMIENTO}.crear_modelo") as crear,
            self.assertRaises(SystemExit) as salida,
        ):
            main()

        self.assertEqual(
            salida.exception.code, "Falta configurar GEMINI_API_KEY en el archivo .env."
        )
        crear.assert_not_called()
