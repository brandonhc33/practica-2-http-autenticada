"""Punto de entrada de la API: uv run python main.py."""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicia la API local autenticada de Gemini.")
    parser.add_argument("--host", default="127.0.0.1", help="Dirección de escucha (127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Puerto de escucha (8000).")
    parser.add_argument("--reload", action="store_true", help="Recarga al editar el código.")
    argumentos = parser.parse_args()
    uvicorn.run(
        "src.api.app:app", host=argumentos.host, port=argumentos.port, reload=argumentos.reload
    )


if __name__ == "__main__":
    main()
