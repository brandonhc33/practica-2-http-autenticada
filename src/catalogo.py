"""Códigos públicos de agentes y sus modelos asociados."""

from typing import TypedDict


class ConfiguracionAgente(TypedDict):
    clave: str
    modelos: dict[str, str]


AGENTES: dict[str, ConfiguracionAgente] = {
    "gemini": {
        "clave": "GEMINI_API_KEY",
        "modelos": {
            "flash-lite": "gemini-3.5-flash-lite",
            "flash": "gemini-3.6-flash",
            "flash-3-8": "gemini-3.8-flash",
        },
    },
}
