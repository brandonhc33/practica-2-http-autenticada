"""Envía una consulta a Gemini con una petición HTTP autenticada."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv


CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
EVIDENCIA = CARPETA_PROYECTO / "docs" / "evidencia_peticion_autenticada.json"


def consultar_gemini(pregunta):
    pregunta = pregunta.strip()
    if not pregunta:
        raise ValueError("Escribe una pregunta que no esté vacía.")

    # La ruta del script permite encontrar .env desde cualquier carpeta.
    load_dotenv(CARPETA_PROYECTO / ".env")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    modelo = os.getenv("GEMINI_MODEL", "").strip() or "gemini-3.5-flash-lite"
    if not api_key:
        raise ValueError("Falta GEMINI_API_KEY. Agrega tu clave en el archivo .env.")

    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{quote(modelo, safe='')}:generateContent"
    )
    # La clave viaja en el encabezado, nunca en la URL ni en el cuerpo.
    encabezados = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    cuerpo = {"contents": [{"parts": [{"text": pregunta}]}]}

    try:
        with requests.post(
            endpoint,
            headers=encabezados,
            json=cuerpo,
            timeout=(10, 60),
            allow_redirects=False,
        ) as respuesta:
            # Algunos errores de clave de Gemini también llegan como HTTP 400.
            if respuesta.status_code != 200:
                mensajes = {
                    400: "Revisa la clave y el contenido de la petición.",
                    401: "Revisa tu clave de API.",
                    403: "Revisa la clave y los permisos del proyecto en Google AI Studio.",
                    404: "Revisa GEMINI_MODEL: el modelo no existe o no está disponible.",
                    429: "Se alcanzó la cuota. Revisa tus límites en Google AI Studio.",
                }
                detalle = mensajes.get(
                    respuesta.status_code, "Intenta nuevamente más tarde."
                )
                raise ValueError(f"Gemini respondió HTTP {respuesta.status_code}. {detalle}")

            datos = respuesta.json()
    except requests.exceptions.JSONDecodeError:
        raise ValueError("Gemini no devolvió un JSON válido.") from None
    except requests.exceptions.Timeout:
        raise ValueError("La petición tardó demasiado. Intenta nuevamente.") from None
    except requests.exceptions.RequestException:
        raise ValueError("No se pudo conectar con Gemini. Revisa tu conexión.") from None

    # El texto generado está dentro del primer candidato de la respuesta.
    candidatos = datos.get("candidates", [])
    partes = candidatos[0].get("content", {}).get("parts", []) if candidatos else []
    texto = "\n".join(
        parte["text"]
        for parte in partes
        if parte.get("text") and not parte.get("thought")
    ).strip()
    if not texto:
        raise ValueError("Gemini respondió HTTP 200, pero no devolvió texto generado.")

    # Guardamos solo el resultado y los datos de la prueba, sin los encabezados.
    return {
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metodo": "POST",
        "endpoint": endpoint,
        "codigo_http": 200,
        "modelo": modelo,
        "pregunta": pregunta,
        "respuesta": texto,
    }


def main():
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("pregunta", nargs="?", help="Consulta que enviarás a Gemini.")
    argumentos.add_argument(
        "--guardar-evidencia",
        nargs="?",
        const=EVIDENCIA,
        type=Path,
        metavar="ARCHIVO",
        help="Guarda la respuesta exitosa en docs/ o en el archivo indicado.",
    )
    opciones = argumentos.parse_args()
    pregunta = opciones.pregunta
    if pregunta is None:
        pregunta = input("Escribe tu pregunta: ")

    resultado = consultar_gemini(pregunta)
    print(f"HTTP {resultado['codigo_http']} | {resultado['modelo']}")
    print(f"\nGemini: {resultado['respuesta']}")

    if opciones.guardar_evidencia:
        archivo = opciones.guardar_evidencia
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"\nEvidencia guardada en: {archivo}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nConsulta cancelada.", file=sys.stderr)
        raise SystemExit(1)
