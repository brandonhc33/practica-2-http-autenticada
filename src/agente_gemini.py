"""Cliente de Gemini: autenticación, petición HTTP y lectura de la respuesta."""

import os

import requests

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"


def consultar_gemini(modelo: str, mensaje: str) -> str:
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

    # El endpoint de chat devuelve el texto en choices[0].message.content.
    if not isinstance(datos, dict):
        raise ValueError("Gemini no devolvió una respuesta válida.")
    opciones = datos.get("choices")
    primera = opciones[0] if isinstance(opciones, list) and opciones else None
    mensaje_generado = primera.get("message") if isinstance(primera, dict) else None
    texto = mensaje_generado.get("content") if isinstance(mensaje_generado, dict) else None
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("Gemini respondió HTTP 200, pero no devolvió texto generado.")
    texto = texto.strip()

    return texto
