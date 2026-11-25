"""Eventos JSON correlacionados por trace_id, sin contenido de la consulta.

El registro acepta una lista cerrada de eventos y campos. Así no depende de recordar
qué no se debe guardar: un campo nuevo con la pregunta o la respuesta falla en las
pruebas en vez de terminar en un archivo.
"""

import contextvars
import hashlib
import json
import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, TextIO

NOMBRE_LOGGER = "ley_rep.rag"
logger = logging.getLogger(NOMBRE_LOGGER)

_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)
_auditoria: contextvars.ContextVar[list[dict[str, Any]] | None] = contextvars.ContextVar(
    "auditoria", default=None
)

EVENTOS = frozenset({
    "consulta_recibida",
    "documentos_recuperados",
    "documento_descartado_por_inyeccion",
    "contexto_filtrado",
    "consumo_llm",
    "respuesta_bloqueada",
    "respuesta_entregada",
    "consulta_con_error",
})

# Solo conteos, tiempos, identificadores del corpus y valores de listas propias. Nunca la
# pregunta, la respuesta, el texto de un fragmento ni el mensaje de una excepción.
CAMPOS: dict[str, type | tuple[type, ...]] = {
    "pregunta_len": int,
    "patrones_en_pregunta": int,
    "datos_ocultados": int,
    "k": int,
    "n_documentos": int,
    "n_limpios": int,
    "n_descartados": int,
    "n_patrones": int,
    "id_chunk": str,
    "huella_fragmento": str,
    "huella_prompt": str,
    "modelo": str,
    "input_tokens": (int, type(None)),
    "output_tokens": (int, type(None)),
    "total_tokens": (int, type(None)),
    "costo_usd": (str, type(None)),
    "respuesta_len": int,
    "n_citas": int,
    "motivo": str,
    "etapa": str,
    "tipo_error": str,
    "estado": str,
    "requiere_revision": bool,
    "ms": (int, float),
    "ms_embedding": (int, float),
    "ms_busqueda": (int, float),
}
LARGO_MAXIMO_TEXTO = 80


def huella(texto: str) -> str:
    """Reconoce el mismo contenido sin guardarlo. No se usa con la pregunta.

    Una pregunta corta se podría adivinar probando textos hasta dar con su huella; los
    fragmentos y prompts, en cambio, ya son públicos.
    """
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]


class FormatoJSON(logging.Formatter):
    """Una línea JSON por evento; omite a propósito el texto y la traza de excepciones."""

    def format(self, record: logging.LogRecord) -> str:
        datos = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "evento": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
            **getattr(record, "campos", {}),
        }
        return json.dumps(datos, ensure_ascii=False)


def configurar_registro(destino: TextIO, nivel: int = logging.INFO) -> logging.Handler:
    """Envía los eventos a un destino y reemplaza el anterior, para no duplicar líneas."""
    manejador = logging.StreamHandler(destino)
    manejador.setFormatter(FormatoJSON())
    logger.handlers = [manejador]
    logger.setLevel(nivel)
    return manejador


def trace_id_actual() -> str | None:
    return _trace_id.get()


@contextmanager
def nueva_traza() -> Iterator[tuple[str, list[dict[str, Any]]]]:
    """Abre una traza propia; al salir restaura la anterior, incluso si hubo un error."""
    trace_id = "trace-" + uuid.uuid4().hex
    auditoria: list[dict[str, Any]] = []
    ficha_traza = _trace_id.set(trace_id)
    ficha_auditoria = _auditoria.set(auditoria)
    try:
        yield trace_id, auditoria
    finally:
        _auditoria.reset(ficha_auditoria)
        _trace_id.reset(ficha_traza)


def _validar(evento: str, campos: dict[str, Any]) -> None:
    if evento not in EVENTOS:
        raise ValueError(f"Evento no previsto: {evento}.")
    for nombre, valor in campos.items():
        tipos = CAMPOS.get(nombre)
        if tipos is None:
            # No incluir el valor: podría ser justo el contenido que no se debe registrar.
            raise ValueError(f"Campo no permitido en los registros: {nombre}.")
        if not isinstance(valor, tipos) or (isinstance(valor, bool) and tipos is not bool):
            raise ValueError(f"Tipo no permitido en el campo {nombre}.")
        if isinstance(valor, str) and len(valor) > LARGO_MAXIMO_TEXTO:
            raise ValueError(f"Texto demasiado largo en el campo {nombre}.")


def registrar_evento(evento: str, nivel: int = logging.INFO, **campos: Any) -> dict[str, Any]:
    """Escribe el evento y lo suma a la auditoría de la consulta abierta."""
    _validar(evento, campos)
    registro = {"evento": evento, "trace_id": trace_id_actual(), **campos}
    auditoria = _auditoria.get()
    if auditoria is not None:
        auditoria.append(registro)
    logger.log(
        nivel, "%s", evento, extra={"trace_id": registro["trace_id"], "campos": dict(campos)}
    )
    return registro
