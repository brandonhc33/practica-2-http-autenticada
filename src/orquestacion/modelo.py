"""Modelo de Gemini para las chains y registro del consumo de cada llamada."""

from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult
from langchain_google_genai import ChatGoogleGenerativeAI

from src.api.esquemas import UsoTokens
from src.catalogo import AGENTES
from src.costos.calculadora import calcular_costo_usd_gemini
from src.costos.registro import obtener_registro_costos

# El conector lo envía como attempts: 1 es un solo intento, para que el fallback actúe enseguida.
INTENTOS_POR_LLAMADA = 1
# Sin un límite, una llamada colgada nunca lanzaría la excepción que activa el fallback.
LIMITE_SEGUNDOS = 30


class RegistroLlamadas(BaseCallbackHandler):
    """Anota cada llamada del modelo en el registro de costos de la sesión."""

    def __init__(self, nombre_modelo: str) -> None:
        self.nombre_modelo = nombre_modelo

    def on_llm_end(
        self, response: LLMResult, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        mensaje = getattr(response.generations[0][0], "message", None)
        datos = mensaje.usage_metadata if isinstance(mensaje, AIMessage) else None
        uso = None
        if datos:
            # El conector ya suma el razonamiento a output_tokens, igual que UsoTokens.salida.
            uso = UsoTokens(
                entrada=datos["input_tokens"],
                salida=datos["output_tokens"],
                total=datos["total_tokens"],
                entrada_cache=datos.get("input_token_details", {}).get("cache_read", 0),
            )
        costo = calcular_costo_usd_gemini(self.nombre_modelo, uso)
        obtener_registro_costos().registrar_respuesta(uso, costo, intentos=INTENTOS_POR_LLAMADA)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        obtener_registro_costos().registrar_fallo(intentos=INTENTOS_POR_LLAMADA)


def crear_modelo(alias: str = "flash-lite") -> ChatGoogleGenerativeAI:
    """Crea un modelo del catálogo con un solo intento, tiempo límite y registro de consumo."""
    nombre_modelo = AGENTES["gemini"]["modelos"][alias]
    return ChatGoogleGenerativeAI(
        model=nombre_modelo,
        max_retries=INTENTOS_POR_LLAMADA,
        timeout=LIMITE_SEGUNDOS,
        callbacks=[RegistroLlamadas(nombre_modelo)],
    )
