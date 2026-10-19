"""Cliente de Gemini: autenticación, petición HTTP y lectura de la respuesta."""

import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from pydantic import ValidationError

from .catalogo import AGENTES
from .costos import calcular_costo_gemini
from .esquemas import Resultado, UsoTokens

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"


def extraer_uso(uso: object) -> UsoTokens | None:
    """Lee el consumo real; metadatos ausentes o inválidos no equivalen a costo cero."""
    if not isinstance(uso, dict):
        return None
    detalles_entrada = uso.get("prompt_tokens_details")
    if detalles_entrada is None:
        detalles_entrada = {}
    if not isinstance(detalles_entrada, dict):
        return None
    try:
        tokens = UsoTokens.model_validate(
            {
                "entrada": uso.get("prompt_tokens"),
                "salida": uso.get("completion_tokens"),
                "total": uso.get("total_tokens"),
                "entrada_cache": detalles_entrada.get("cached_tokens", 0),
            }
        )
    except ValidationError:
        return None
    if tokens.total < tokens.entrada + tokens.salida or tokens.entrada_cache > tokens.entrada:
        return None

    # Gemini puede informar completion_tokens sin el razonamiento. El total sí lo
    # incluye: restar la entrada conserva toda la salida sin sumarlo dos veces.
    tokens.salida = tokens.total - tokens.entrada
    return tokens


def consultar_gemini_raw(modelo: str, mensaje: str) -> dict[str, Any]:
    """Devuelve todos los campos JSON del proveedor sin procesar el texto ni el consumo."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Falta GEMINI_API_KEY. Agrega tu clave en el archivo .env.")

    # La clave viaja en el encabezado, nunca en la URL ni en el cuerpo.
    # El token de la API local se valida en api.py y no se envía a Google.
    encabezados = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    cuerpo = {
        "model": modelo,
        "messages": [{"role": "user", "content": mensaje}],
    }

    try:
        with requests.post(
            ENDPOINT,
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
                    404: "Revisa el modelo de Gemini configurado en src/catalogo.py.",
                    429: "Se alcanzó la cuota. Revisa tus límites en Google AI Studio.",
                    503: "Gemini no está disponible temporalmente. Intenta nuevamente más tarde.",
                }
                detalle = mensajes.get(respuesta.status_code, "Intenta nuevamente más tarde.")
                raise ValueError(f"Gemini respondió HTTP {respuesta.status_code}. {detalle}")

            datos = respuesta.json()
    except requests.exceptions.JSONDecodeError:
        raise ValueError("Gemini no devolvió un JSON válido.") from None
    except requests.exceptions.Timeout:
        raise ValueError("La petición tardó demasiado. Intenta nuevamente.") from None
    except requests.exceptions.RequestException:
        raise ValueError("No se pudo conectar con Gemini. Revisa tu conexión.") from None

    if not isinstance(datos, dict):
        raise ValueError("Gemini no devolvió una respuesta válida.")
    return datos


def consultar_gemini(modelo: str, mensaje: str) -> Resultado:
    datos = consultar_gemini_raw(modelo, mensaje)
    # El endpoint de chat devuelve el texto en choices[0].message.content.
    opciones = datos.get("choices")
    primera = opciones[0] if isinstance(opciones, list) and opciones else None
    mensaje_generado = primera.get("message") if isinstance(primera, dict) else None
    texto = mensaje_generado.get("content") if isinstance(mensaje_generado, dict) else None
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("Gemini respondió HTTP 200, pero no devolvió texto generado.")
    texto = texto.strip()

    uso = extraer_uso(datos.get("usage"))
    return Resultado(respuesta=texto, uso=uso, costo_estimado=calcular_costo_gemini(modelo, uso))


def obtener_dato_de_prueba(pregunta: str) -> Resultado:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    modelo = AGENTES["gemini"]["modelos"]["flash-lite"]
    return consultar_gemini(modelo, pregunta)


def main() -> None:
    pregunta_por_defecto = (
        "Estoy aprendiendo a programar en Python y quiero entender cómo se conecta una "
        "aplicación con una inteligencia artificial. ¿Puedes explicar qué es una API, "
        "cómo viaja una pregunta desde Python hasta Gemini y cómo vuelve la respuesta? "
        "Incluye una analogía cotidiana, explica para qué sirve una API key y menciona "
        "tres errores comunes al hacer la conexión con una forma de resolver cada uno. "
        "Responde en español, con secciones breves y en unas 200 palabras."
    )
    parser = argparse.ArgumentParser(
        description="Consulta Gemini y muestra texto, tokens y costos en USD y CLP como JSON."
    )
    parser.add_argument(
        "pregunta",
        nargs="?",
        default=pregunta_por_defecto,
        help="Pregunta para Gemini. Si la omites, se utiliza la pregunta de prueba.",
    )
    argumentos = parser.parse_args()
    if not argumentos.pregunta.strip():
        parser.error("La pregunta no puede estar vacía ni contener solo espacios.")
    try:
        resultado = obtener_dato_de_prueba(argumentos.pregunta)
        print(json.dumps(resultado.model_dump(mode="json"), ensure_ascii=False, indent=2))
    except ValueError as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
