"""Agente de Ley REP del Bloque 21: elige herramientas y deja su traza en intermediate_steps."""

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.agents import AgentAction
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from src.catalogo import AGENTES
from src.costos.registro import sesion_costos
from src.orquestacion.cadena_tres_pasos import REGLAS_TEXTO
from src.orquestacion.enrutamiento import MENSAJE_SEGURO, MENSAJE_VACIO
from src.orquestacion.herramientas import buscar_en_ley, obtener_articulo
from src.orquestacion.modelo import crear_modelo, exigir_texto

logger = logging.getLogger(__name__)

HERRAMIENTAS: list[BaseTool] = [buscar_en_ley, obtener_articulo]
# Cada paso es una llamada al modelo: el peor caso cuesta 4 llamadas, no las 15 por defecto.
LIMITE_PASOS = 4
# AgentExecutor entrega este texto, en inglés, cuando se agota max_iterations.
AVISO_LIMITE_ORIGINAL = "Agent stopped due to max iterations."
AVISO_LIMITE_PASOS = (
    "No alcancé a responder dentro del límite de pasos. Reformula la consulta con más detalle "
    "o pregunta por un artículo específico."
)

INSTRUCCIONES_AGENTE = (
    "Usa las herramientas cuando la respuesta dependa del texto de la ley. Si la consulta no lo "
    "necesita, como un saludo o una pregunta sobre lo que puedes hacer, responde sin "
    "herramientas. Basa cada afirmación sobre la ley solo en lo que devolvieron las herramientas "
    "e indica el artículo que la respalda. Si no alcanza, dilo: la falta de evidencia no "
    "significa que no existan obligaciones."
)

prompt_agente = ChatPromptTemplate.from_messages(
    [
        ("system", REGLAS_TEXTO + "\n\n" + INSTRUCCIONES_AGENTE),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "<consulta>{entrada}</consulta>"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)


def construir_ejecutor(modelo: BaseChatModel, herramientas: Sequence[BaseTool]) -> AgentExecutor:
    """Arma el agente con su traza de pasos y un máximo de cuatro llamadas al modelo."""
    agente = create_tool_calling_agent(modelo, herramientas, prompt_agente)
    return AgentExecutor(
        agent=agente,
        tools=herramientas,
        return_intermediate_steps=True,
        max_iterations=LIMITE_PASOS,
    )


def salida_como_texto(resultado: dict[str, Any]) -> dict[str, Any]:
    """Deja output en texto: une los bloques, traduce el aviso de límite y rechaza el vacío."""
    salida = resultado["output"]
    if isinstance(salida, list):
        # Con Gemini 3 el conector entrega bloques; solo los de tipo "text" son la respuesta.
        salida = "".join(
            bloque if isinstance(bloque, str) else bloque.get("text", "")
            for bloque in salida
            if isinstance(bloque, str) or bloque.get("type") == "text"
        )
    if salida.strip() == AVISO_LIMITE_ORIGINAL:
        salida = AVISO_LIMITE_PASOS
    return {**resultado, "output": exigir_texto(salida)}


def consultar_agente(agente: Runnable, entrada: str) -> dict[str, Any]:
    """Ejecuta una consulta y devuelve output e intermediate_steps, sin propagar excepciones."""
    if not entrada.strip():
        return {"output": MENSAJE_VACIO, "intermediate_steps": []}
    try:
        return salida_como_texto(agente.invoke({"entrada": entrada}))
    except Exception as error:
        logger.error("Falló el agente (%s): %s", type(error).__name__, error)
        logger.debug("Traza del error", exc_info=error)
        return {"output": MENSAJE_SEGURO, "intermediate_steps": []}


def describir_pasos(pasos: list[tuple[AgentAction, Any]]) -> str:
    """Resume qué herramienta usó el agente y con qué argumentos."""
    if not pasos:
        return "ninguna"
    return ", ".join(f"{accion.tool}({accion.tool_input})" for accion, _ in pasos)


def main() -> None:
    """Responde consultas por terminal; las herramientas usadas y el consumo van a stderr."""
    parser = argparse.ArgumentParser(description="Responde consultas de Ley REP con un agente.")
    parser.add_argument("consultas", nargs="+", help="Una o más consultas sobre la Ley REP.")
    consultas = parser.parse_args().consultas
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    clave = AGENTES["gemini"]["clave"]
    if not os.getenv(clave, "").strip():
        sys.exit(f"Falta configurar {clave} en el archivo .env.")
    # En nivel INFO, el registro de costos muestra los tokens de cada llamada al modelo.
    logging.basicConfig(level=logging.INFO)
    ejecutor = construir_ejecutor(crear_modelo(), HERRAMIENTAS)
    with sesion_costos() as registro:
        for consulta in consultas:
            resultado = consultar_agente(ejecutor, consulta)
            print(resultado["output"], flush=True)
            pasos = describir_pasos(resultado["intermediate_steps"])
            print(f"Herramientas: {pasos}", file=sys.stderr, flush=True)
    print(registro.resumen().como_dict(), file=sys.stderr)


if __name__ == "__main__":
    main()
