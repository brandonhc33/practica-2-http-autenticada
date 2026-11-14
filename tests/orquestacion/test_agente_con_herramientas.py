import io
import itertools
import os
import unittest
from collections.abc import Iterator
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from typing import Any
from unittest.mock import patch

from google.genai import types
from langchain_core.messages import AIMessage, ToolMessage

from src.costos.registro import sesion_costos
from src.orquestacion.agente_con_herramientas import (
    AVISO_LIMITE_PASOS,
    HERRAMIENTAS,
    LIMITE_PASOS,
    construir_ejecutor,
    consultar_agente,
    main,
    salida_como_texto,
)
from src.orquestacion.enrutamiento import MENSAJE_SEGURO, MENSAJE_VACIO
from src.orquestacion.modelo import RegistroLlamadas, crear_modelo
from tests.orquestacion.modelo_falso import crear_modelo_falso, pedir_herramienta

AGENTE = "src.orquestacion.agente_con_herramientas"
USO = {"input_tokens": 1_000, "output_tokens": 2_000, "total_tokens": 3_000}


def fallar_por_conexion() -> Iterator[AIMessage]:
    raise ConnectionError("simulado")
    yield  # Convierte la función en un generador: falla al pedir la respuesta.


class TestEjecutor(unittest.TestCase):
    def test_agente_registra_la_herramienta_elegida(self):
        modelo = crear_modelo_falso(
            [
                pedir_herramienta("obtener_articulo", numero="12"),
                AIMessage(content="El artículo 12 trata de las metas."),
            ]
        )
        ejecutor = construir_ejecutor(modelo, HERRAMIENTAS)

        resultado = consultar_agente(ejecutor, "¿Qué dice el artículo 12?")

        accion, observacion = resultado["intermediate_steps"][0]
        self.assertEqual(accion.tool, "obtener_articulo")
        self.assertEqual(accion.tool_input, {"numero": "12"})
        self.assertTrue(observacion.startswith("[Artículo 12]\n"))
        self.assertEqual(resultado["output"], "El artículo 12 trata de las metas.")
        # La segunda llamada recibe la observación en el scratchpad, como un ToolMessage.
        self.assertEqual(len(modelo.recibidos), 2)
        ultimo = modelo.recibidos[1][-1]
        assert isinstance(ultimo, ToolMessage)
        self.assertEqual(ultimo.content, observacion)

    def test_agente_no_usa_herramienta_para_pregunta_general(self):
        modelo = crear_modelo_falso([AIMessage(content="Respondo consultas sobre la Ley REP.")])
        ejecutor = construir_ejecutor(modelo, HERRAMIENTAS)

        resultado = consultar_agente(ejecutor, "Hola, ¿qué puedes hacer?")

        self.assertEqual(resultado["intermediate_steps"], [])
        self.assertEqual(resultado["output"], "Respondo consultas sobre la Ley REP.")
        self.assertEqual(len(modelo.recibidos), 1)

    def test_agente_se_detiene_en_el_limite_de_pasos(self):
        modelo = crear_modelo_falso(
            itertools.repeat(pedir_herramienta("buscar_en_ley", consulta="metas"))
        )
        ejecutor = construir_ejecutor(modelo, HERRAMIENTAS)

        resultado = consultar_agente(ejecutor, "¿Qué metas fija la ley?")

        self.assertEqual(LIMITE_PASOS, 4)
        self.assertEqual(len(modelo.recibidos), 4)
        self.assertEqual(len(resultado["intermediate_steps"]), 4)
        self.assertEqual(resultado["output"], AVISO_LIMITE_PASOS)

    def test_ejecutor_devuelve_la_traza(self):
        ejecutor = construir_ejecutor(crear_modelo_falso([]), HERRAMIENTAS)

        self.assertTrue(ejecutor.return_intermediate_steps)
        self.assertEqual(ejecutor.max_iterations, 4)
        self.assertEqual(
            [herramienta.name for herramienta in ejecutor.tools],
            ["buscar_en_ley", "obtener_articulo"],
        )


class TestSalidaComoTexto(unittest.TestCase):
    def test_salida_como_texto_convierte_bloques(self):
        casos: tuple[tuple[Any, str], ...] = (
            (
                [{"type": "text", "text": "El artículo 12 ", "index": 0}, "fija metas."],
                "El artículo 12 fija metas.",
            ),
            ([{"type": "thinking", "thinking": "razono"}, {"type": "text", "text": "Hola"}], "Hola"),
            ("Texto que ya venía plano.", "Texto que ya venía plano."),
            ("Agent stopped due to max iterations.", AVISO_LIMITE_PASOS),
        )
        for salida, esperado in casos:
            with self.subTest(salida=salida):
                resultado = salida_como_texto({"output": salida, "intermediate_steps": []})
                self.assertEqual(resultado, {"output": esperado, "intermediate_steps": []})

    def test_respuesta_vacia_entrega_mensaje_seguro(self):
        for contenido in ("", "  \n", []):
            with self.subTest(contenido=contenido):
                modelo = crear_modelo_falso([AIMessage(content=contenido)])
                ejecutor = construir_ejecutor(modelo, HERRAMIENTAS)

                with self.assertLogs(AGENTE, level="ERROR") as registros:
                    resultado = consultar_agente(ejecutor, "¿Qué dice la ley?")

                self.assertEqual(resultado, {"output": MENSAJE_SEGURO, "intermediate_steps": []})
                self.assertIn("ValueError", registros.output[0])


class TestConsultarAgente(unittest.TestCase):
    def test_consultar_agente_no_propaga_excepciones(self):
        modelo = crear_modelo_falso(fallar_por_conexion())
        ejecutor = construir_ejecutor(modelo, HERRAMIENTAS)

        with self.assertLogs(AGENTE, level="DEBUG") as registros:
            resultado = consultar_agente(ejecutor, "consulta-privada")

        self.assertEqual(resultado, {"output": MENSAJE_SEGURO, "intermediate_steps": []})
        error, traza = registros.records
        self.assertEqual((error.levelname, traza.levelname), ("ERROR", "DEBUG"))
        self.assertIn("ConnectionError", registros.output[0])
        self.assertIn("simulado", registros.output[0])
        self.assertNotIn("consulta-privada", "\n".join(registros.output))

    def test_consulta_vacia_no_llama_al_modelo(self):
        for entrada in ("", "   \n"):
            with self.subTest(entrada=entrada):
                modelo = crear_modelo_falso([AIMessage(content="no debería usarse")])
                ejecutor = construir_ejecutor(modelo, HERRAMIENTAS)

                resultado = consultar_agente(ejecutor, entrada)

                self.assertEqual(resultado, {"output": MENSAJE_VACIO, "intermediate_steps": []})
                self.assertEqual(modelo.recibidos, [])


def respuesta_por_partes(
    partes: list[types.Part], entrada: int, salida: int, total: int, ultima: bool = False
) -> types.GenerateContentResponse:
    """Una parte de la respuesta: Gemini informa en cada una el consumo acumulado."""
    return types.GenerateContentResponse(
        model_version="gemini-3.5-flash-lite",
        candidates=[
            types.Candidate(
                content=types.Content(role="model", parts=partes),
                finish_reason=types.FinishReason.STOP if ultima else None,
            )
        ],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=entrada,
            candidates_token_count=salida,
            thoughts_token_count=20,
            total_token_count=total,
        ),
    )


class TestConectorGemini(unittest.TestCase):
    """El conector real con el SDK simulado: así se ve lo que de verdad se enviaría."""

    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"GEMINI_API_KEY": "clave-ficticia"}, clear=True))
        llamada_herramienta = types.Part(
            function_call=types.FunctionCall(name="obtener_articulo", args={"numero": "12"}),
            thought_signature=b"firma-de-razonamiento",
        )
        respuestas = iter(
            [
                [respuesta_por_partes([llamada_herramienta], 100, 10, 130, ultima=True)],
                [
                    respuesta_por_partes([types.Part(text="El artículo 12 ")], 300, 5, 325),
                    respuesta_por_partes([types.Part(text="fija metas.")], 300, 12, 332, True),
                ],
            ]
        )
        self.pedidos: list[dict[str, Any]] = []

        def generar_por_partes(_: object, **pedido: Any) -> Iterator[types.GenerateContentResponse]:
            self.pedidos.append(pedido)
            return iter(next(respuestas))

        self.enterContext(
            patch("google.genai.models.Models.generate_content_stream", generar_por_partes)
        )
        self.enterContext(
            patch(
                "google.genai.models.Models.generate_content",
                side_effect=AssertionError("El agente debía pedir la respuesta por partes."),
            )
        )

    def test_registro_suma_el_consumo_de_respuestas_por_partes(self):
        with sesion_costos() as registro:
            resultado = consultar_agente(
                construir_ejecutor(crear_modelo(), HERRAMIENTAS), "¿Qué dice el artículo 12?"
            )

        self.assertEqual(resultado["output"], "El artículo 12 fija metas.")
        resumen = registro.resumen()
        self.assertEqual(resumen.respuestas_con_costo, 2)
        # Cuenta la última parte de cada llamada, no la suma de los acumulados de cada parte.
        self.assertEqual(resumen.tokens_entrada, 100 + 300)
        self.assertEqual(resumen.tokens_salida, (10 + 20) + (12 + 20))
        self.assertEqual(resumen.tokens_total, 130 + 332)
        # (400 x 0,30 + 62 x 2,50) / 1.000.000
        self.assertEqual(resumen.costo_conocido_usd, Decimal("0.000275"))

    def test_agente_reenvia_la_firma_de_razonamiento(self):
        consultar_agente(construir_ejecutor(crear_modelo(), HERRAMIENTAS), "¿Artículo 12?")

        self.assertEqual(len(self.pedidos), 2)
        partes_del_modelo = [
            parte
            for contenido in self.pedidos[1]["contents"]
            if contenido.role == "model"
            for parte in contenido.parts or []
        ]
        llamadas = [parte for parte in partes_del_modelo if parte.function_call]
        self.assertEqual(len(llamadas), 1)
        self.assertEqual(llamadas[0].function_call.name, "obtener_articulo")
        self.assertEqual(llamadas[0].thought_signature, b"firma-de-razonamiento")


class TestMain(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch(f"{AGENTE}.load_dotenv"))
        self.enterContext(patch(f"{AGENTE}.logging.basicConfig"))

    def test_main_imprime_respuestas_herramientas_y_consumo(self):
        pedido = pedir_herramienta("obtener_articulo", numero="12")
        modelo = crear_modelo_falso(
            [
                pedido.model_copy(update={"usage_metadata": USO}),
                AIMessage(content="Fija metas de recolección.", usage_metadata=USO),
                AIMessage(content="Respondo consultas de Ley REP.", usage_metadata=USO),
            ],
            callbacks=[RegistroLlamadas("gemini-3.5-flash-lite")],
        )
        salida, errores = io.StringIO(), io.StringIO()

        with (
            patch("sys.argv", ["agente", "¿Qué dice el artículo 12?", "Hola"]),
            patch.dict(os.environ, {"GEMINI_API_KEY": "clave-ficticia"}, clear=True),
            patch(f"{AGENTE}.crear_modelo", return_value=modelo),
            redirect_stdout(salida),
            redirect_stderr(errores),
        ):
            main()

        self.assertEqual(
            salida.getvalue().splitlines(),
            ["Fija metas de recolección.", "Respondo consultas de Ley REP."],
        )
        self.assertIn("Herramientas: obtener_articulo({'numero': '12'})", errores.getvalue())
        self.assertIn("Herramientas: ninguna", errores.getvalue())
        self.assertIn("'respuestas_con_costo': 3", errores.getvalue())
        self.assertIn("'tokens_total': 9000", errores.getvalue())

    def test_main_sin_clave_termina_con_mensaje(self):
        with (
            patch("sys.argv", ["agente", "Hola"]),
            patch.dict(os.environ, {}, clear=True),
            patch(f"{AGENTE}.crear_modelo") as crear,
            self.assertRaises(SystemExit) as salida,
        ):
            main()

        self.assertEqual(
            salida.exception.code, "Falta configurar GEMINI_API_KEY en el archivo .env."
        )
        crear.assert_not_called()
