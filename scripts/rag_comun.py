"""Configuración y salidas nuevas compartidas por los comandos del RAG."""

import os
from pathlib import Path
from typing import TextIO

from dotenv import load_dotenv

from src.rag.indice import RAIZ


def exigir_consumo(confirmado: bool) -> None:
    if not confirmado:
        raise ValueError("Este comando consume cuota. Añade --confirmar-consumo para ejecutarlo.")
    load_dotenv(RAIZ / ".env")
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("Falta GEMINI_API_KEY: configúrala en el entorno o en .env.")


def abrir_salida_nueva(ruta: Path) -> TextIO:
    """Reserva la salida antes de gastar cuota y nunca sobrescribe evidencia anterior."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    return ruta.open("x", encoding="utf-8")
