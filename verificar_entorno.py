"""Comprueba lo necesario para la corrida real del Gate 2, sin mostrar la clave.

Termina con código 1 si falta algo. El ensayo `python servicio_rag.py` no necesita ni la
clave ni el índice.
"""

import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PAQUETES = [
    "langchain-core", "langchain-chroma", "langchain-google-genai", "chromadb", "langgraph",
    "langgraph-checkpoint-sqlite", "python-dotenv", "pytest",
]
RAIZ = Path(__file__).resolve().parent


def main() -> int:
    problemas: list[str] = []
    print("Python:", sys.version.split()[0])
    if sys.version_info < (3, 12):  # noqa: UP036 — se ejecuta antes de instalar
        problemas.append("usar Python 3.12 o superior")
    for paquete in PAQUETES:
        try:
            print(f"{paquete}: {version(paquete)}")
        except PackageNotFoundError:
            print(f"{paquete}: NO instalado")
            problemas.append(f"instalar {paquete}")
    if not problemas:
        from dotenv import load_dotenv

        load_dotenv(RAIZ / ".env")
    definida = bool(os.getenv("GEMINI_API_KEY"))
    print("GEMINI_API_KEY:", "definida" if definida else "FALTA")
    if not definida:
        problemas.append("definir GEMINI_API_KEY en el archivo .env")
    if not problemas or problemas == ["definir GEMINI_API_KEY en el archivo .env"]:
        from src.rag.indice_normas import abrir_indice_normas

        try:
            _, datos = abrir_indice_normas()
            print(f"índice en indice_normas/: ok, {datos['fragmentos']} fragmentos de "
                  f"{', '.join(datos['normas'])}")
        except ValueError as error:
            print(f"índice en indice_normas/: {error}")
            problemas.append("indexar con: python servicio_rag.py indexar --confirmar-consumo")
    print()
    if problemas:
        print("Pendiente: " + "; ".join(problemas))
        return 1
    print("Entorno listo para la corrida final")
    return 0


if __name__ == "__main__":
    sys.exit(main())
