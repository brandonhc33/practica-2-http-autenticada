"""Modelo falso compartido por las pruebas del agente, sin red ni tokens."""

from collections.abc import Callable, Iterable, Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import Field


class ModeloFalso(GenericFakeChatModel):
    """Devuelve respuestas fijas y guarda los mensajes que recibió en cada llamada."""

    recibidos: list[list[BaseMessage]] = Field(default_factory=list)

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        """create_tool_calling_agent lo exige; las respuestas fijas ya traen la herramienta."""
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.recibidos.append(list(messages))
        return super()._generate(messages, stop, run_manager, **kwargs)


def crear_modelo_falso(respuestas: Iterable[AIMessage | str], **opciones: Any) -> ModeloFalso:
    """Crea el modelo sin streaming: por partes, el falso falla con una llamada a herramienta."""
    return ModeloFalso(messages=iter(respuestas), disable_streaming=True, **opciones)


def pedir_herramienta(nombre: str, **argumentos: Any) -> AIMessage:
    """Respuesta del modelo que pide usar una herramienta con esos argumentos."""
    return AIMessage(
        content="", tool_calls=[{"name": nombre, "args": argumentos, "id": f"llamada-{nombre}"}]
    )
