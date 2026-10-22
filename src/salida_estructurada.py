"""Interpreta el contenido generado y exige el contrato de la tarea seleccionada."""

import json
import re
from typing import Any

from pydantic import ValidationError

from prompts.banco import BANCO_DE_PROMPTS, NombrePrompt


def parsear_respuesta_json(texto: str, nombre: NombrePrompt) -> dict[str, Any]:
    texto_limpio = texto.strip()
    # Solo retiramos un bloque completo de Markdown. No intentamos reparar JSON
    # cortado ni rescatar fragmentos de una respuesta con prosa adicional.
    bloque = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", texto_limpio, re.DOTALL | re.IGNORECASE)
    if bloque:
        texto_limpio = bloque.group(1)
    try:
        datos = json.loads(texto_limpio)
    except json.JSONDecodeError:
        raise ValueError("La respuesta del modelo no es JSON válido.") from None
    if not isinstance(datos, dict):
        raise ValueError("La respuesta del modelo debe ser un objeto JSON.")

    try:
        salida = BANCO_DE_PROMPTS[nombre].tipo_salida.model_validate(datos)
    except ValidationError as error:
        campos = ", ".join(
            ".".join(str(parte) for parte in detalle["loc"]) or "objeto"
            for detalle in error.errors(include_input=False)
        )
        raise ValueError(
            f"La respuesta no cumple el esquema de {nombre}. Revisa: {campos}."
        ) from None
    return salida.model_dump(mode="json")
