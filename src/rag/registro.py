"""Mediciones por etapa con tokens de generación reales y costos desconocidos explícitos."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter
from typing import Any, Literal
from uuid import uuid4

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from src.api.esquemas import UsoTokens, decimal_fijo
from src.costos.calculadora import TARIFAS_GEMINI, calcular_costo_usd_gemini
from src.orquestacion.modelo import exigir_texto
from src.rag.recuperacion import (
    PROMPT_RAG,
    buscar_por_vector,
    formatear_contexto,
    revisar_citas,
    validar_consulta,
)

# Referencia estándar de pago de gemini-embedding-001, no factura ni uso medido.
# https://ai.google.dev/gemini-api/docs/pricing#gemini-embedding — 2026-11-16.
TARIFA_EMBEDDING_POR_MILLON = Decimal("0.15")


@contextmanager
def medir(tiempos: dict[str, float | None], etapa: str) -> Iterator[None]:
    inicio = perf_counter()
    try:
        yield
    finally:
        tiempos[etapa] = (perf_counter() - inicio) * 1000


def consumo_generacion(mensaje: AIMessage, nombre_modelo: str) -> dict[str, Any]:
    datos = mensaje.usage_metadata
    uso = None if datos is None else UsoTokens(
        entrada=datos["input_tokens"],
        salida=datos["output_tokens"],
        total=datos["total_tokens"],
        entrada_cache=datos.get("input_token_details", {}).get("cache_read", 0),
    )
    costo = calcular_costo_usd_gemini(nombre_modelo, uso)
    tarifas = TARIFAS_GEMINI.get(nombre_modelo)
    return {
        "tokens": dict(datos) if datos is not None else None,
        "costo_generacion_usd": decimal_fijo(costo.total) if costo is not None else None,
        "tarifas_generacion_por_millon_usd": (
            tarifas.model_dump(mode="json") if tarifas is not None else None
        ),
    }


def registrar_consulta(
    pregunta: str,
    indice: Chroma,
    manifiesto: dict[str, Any],
    embeddings: Embeddings,
    modelo: BaseChatModel,
    nombre_modelo: str,
    k: int = 3,
    *,
    tipo_ejecucion: Literal["real", "prueba"],
) -> dict[str, Any]:
    """Ejecuta una vez y conserva el resultado parcial incluso si falla una etapa."""
    validar_consulta(pregunta, k)
    inicio = perf_counter()
    tiempos: dict[str, float | None] = {
        "embed_query": None, "busqueda_vectorial": None, "generacion": None,
    }
    registro: dict[str, Any] = {
        "id_corrida": uuid4().hex,
        "timestamp": datetime.now(UTC).isoformat(),
        "tipo_ejecucion": tipo_ejecucion,
        "pregunta": pregunta,
        "k": k,
        "huella_indice": manifiesto["huella_indice"],
        "configuracion_indice": manifiesto["configuracion"],
        "modelo_generacion": nombre_modelo,
        "tiempos_ms": tiempos,
        "estado": "error",
        "etapa_error": None,
        "tipo_error": None,
        "respuesta": None,
        "fuentes": {},
        "revision_citas": None,
        "tokens": None,
        "costo_generacion_usd": None,
        "tarifas_generacion_por_millon_usd": None,
        "embeddings": {
            "caracteres_consulta": len(pregunta),
            "tokens_reales": None,
            "costo_real_usd": None,
            "tokens_aproximados_por_caracteres": (len(pregunta) + 3) // 4,
            "tarifa_referencia_por_millon_usd": decimal_fijo(TARIFA_EMBEDDING_POR_MILLON),
            "advertencia": "El conector solo devuelve vectores; no informa tokens ni costo real.",
        },
        "fuente_tarifas": "https://ai.google.dev/gemini-api/docs/pricing",
        "advertencia_costo": "Estimación de pago, no factura. Embeddings desconocidos, no cero.",
        "costo_total_usd": None,
    }
    etapa = "embed_query"
    try:
        with medir(tiempos, etapa):
            vector = embeddings.embed_query(pregunta)
        etapa = "busqueda_vectorial"
        with medir(tiempos, etapa):
            recuperados = buscar_por_vector(indice, vector, k)
        if not recuperados:
            raise ValueError("El índice no devolvió fragmentos.")
        contexto, fuentes = formatear_contexto(recuperados)
        registro["fuentes"] = fuentes
        prompt = PROMPT_RAG.invoke({"pregunta": pregunta, "contexto": contexto})
        registro["caracteres_contexto"] = len(contexto)
        etapa = "generacion"
        with medir(tiempos, etapa):
            mensaje = modelo.invoke(prompt)
        # Registrar uso antes de validar el texto: un bloqueo vacío también puede consumir.
        registro.update(consumo_generacion(mensaje, nombre_modelo))
        respuesta = exigir_texto(mensaje.text)
        registro["respuesta"] = respuesta
        registro["revision_citas"] = revisar_citas(respuesta, fuentes)
        registro["estado"] = "ok"
    except Exception as error:
        registro["etapa_error"] = etapa
        # No persistir mensajes del SDK: podrían contener datos del transporte o credenciales.
        registro["tipo_error"] = type(error).__name__
    registro["costo_conocido_usd"] = registro["costo_generacion_usd"]
    registro["embeddings"]["costo_aproximado_usd"] = decimal_fijo(
        Decimal(registro["embeddings"]["tokens_aproximados_por_caracteres"])
        * TARIFA_EMBEDDING_POR_MILLON / Decimal(1_000_000)
    )
    registro["tiempo_total_ms"] = (perf_counter() - inicio) * 1000
    registro["tiempo_etapas_ms"] = sum(t for t in tiempos.values() if t is not None)
    # Carga/verificación del índice ocurre antes de esta función y no se atribuye al retrieval.
    registro["alcance_tiempo"] = (
        "Consulta con índice y clientes cargados; total de pared incluye armado de prompt, "
        "pero no instalación, indexación ni carga inicial."
    )
    return registro
