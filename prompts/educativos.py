"""Prompts educativos de Python y APIs, con sus contratos de salida."""

from pydantic import Field

from .base import REGLAS_DE_SALIDA, NombrePrompt, Prompt, SalidaPrompt, Texto


class ExplicacionConcepto(SalidaPrompt):
    concepto: Texto
    explicacion: Texto
    analogia: Texto
    ejemplo: Texto


class DiagnosticoHTTP(SalidaPrompt):
    codigo_http: int | None = Field(ge=100, le=599)
    causa_probable: Texto
    pasos_revision: list[Texto] = Field(min_length=1, max_length=5)


class ResumenTecnico(SalidaPrompt):
    resumen: Texto
    puntos_clave: list[Texto] = Field(min_length=1, max_length=5)


REGLAS_COMUNES = (
    "Eres un asistente educativo de Python y APIs para una persona principiante. "
    + REGLAS_DE_SALIDA
)

PROMPTS_EDUCATIVOS: dict[NombrePrompt, Prompt] = {
    "explicar_concepto": Prompt(
        nombre="explicar_concepto",
        version="1.1",
        system_instruction=(
            REGLAS_COMUNES
            + "Explica el concepto técnico consultado. Incluye exactamente concepto, "
            "explicacion, analogia y ejemplo como textos no vacíos. La analogía debe "
            "ser cotidiana y el ejemplo debe describir un uso concreto en lenguaje "
            "natural, sin código, nombres de SDK ni versiones de modelos."
        ),
        ejemplo_usuario="¿Qué es una API y cómo la usa Python para consultar Gemini?",
        tipo_salida=ExplicacionConcepto,
    ),
    "diagnosticar_error_http": Prompt(
        nombre="diagnosticar_error_http",
        version="1.1",
        system_instruction=(
            REGLAS_COMUNES + "Diagnostica el error HTTP descrito. Devuelve exactamente codigo_http "
            "(entero de 100 a 599, o null si no se indicó uno), causa_probable (texto) "
            "y pasos_revision (lista de uno a cinco textos). Distingue el Bearer token "
            "de la API local de GEMINI_API_KEY, que autentica las llamadas a Google. "
            "En este proyecto API_BEARER_TOKEN es un secreto estático comparado "
            "directamente con el valor recibido: no tiene firma, expiración ni "
            "renovación automática. No atribuyas un error a caducidad de ese token. "
            "Presenta la causa como una hipótesis si no está confirmada. No solicites "
            "publicar credenciales ni supongas que el token local es un JWT."
        ),
        ejemplo_usuario=(
            "Mi POST /consultar a la API local de FastAPI devuelve HTTP 401. "
            "Todavía no se realizó ninguna llamada a Gemini. ¿Qué debo revisar?"
        ),
        tipo_salida=DiagnosticoHTTP,
    ),
    "resumir_texto_tecnico": Prompt(
        nombre="resumir_texto_tecnico",
        version="1.0",
        system_instruction=(
            REGLAS_COMUNES + "Resume exclusivamente el texto técnico del usuario, conservando sus "
            "distinciones importantes. Devuelve exactamente resumen (texto no vacío) "
            "y puntos_clave (lista de uno a cinco textos no vacíos). No agregues "
            "recomendaciones ni hechos que no aparezcan en el texto de entrada."
        ),
        ejemplo_usuario=(
            "Python envía una petición HTTP a Gemini usando GEMINI_API_KEY. "
            "Nuestra API local se protege con otro Bearer token. Ambos secretos "
            "se cargan desde .env y no se publican en Git. El cliente configura "
            "timeouts y controla errores de conexión y de cuota. El consumo de "
            "tokens lo informa Gemini y el costo estimado se calcula en Python."
        ),
        tipo_salida=ResumenTecnico,
    ),
}
