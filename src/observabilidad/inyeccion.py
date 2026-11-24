"""Primera barrera contra instrucciones escondidas en los fragmentos recuperados.

Es una lista de frases conocidas: una instrucción escrita con otras palabras, en otro
idioma o con letras separadas no se detecta. Se suma a la separación de roles y a la
delimitación del contexto; no las reemplaza.
"""

import logging
import re
import unicodedata

from langchain_core.documents import Document

from src.observabilidad.trazas import huella, registrar_evento

PATRONES = (
    r"ignor(?:a|ar|e|en)\s+(?:todas\s+)?(?:las\s+)?(?:instrucciones|reglas)\s+(?:anteriores|previas)",
    r"ignore\s+(?:all\s+)?(?:the\s+)?(?:previous|prior)\s+instructions",
    r"(?:olvida|haz\s+caso\s+omiso\s+de)\s+(?:todo\s+)?(?:lo\s+|las\s+instrucciones\s+)?anterior(?:es)?",
    r"nuevo\s+sistema\s*:",
    r"system\s*prompt\s*:",
    r"revela\s+(?:tu|el)\s+prompt",
    r"(?:a\s+partir\s+de\s+ahora|desde\s+ahora)\W+(?:eres|responde|actua)",
)
_COMPILADOS = tuple(re.compile(p) for p in PATRONES)


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni caracteres invisibles, con espacios simples."""
    descompuesto = unicodedata.normalize("NFKD", texto.lower())
    visible = "".join(
        c for c in descompuesto if unicodedata.category(c) not in {"Mn", "Cf"}
    )
    return re.sub(r"\s+", " ", visible)


def detectar_inyeccion(texto: str) -> list[int]:
    """Posiciones de los patrones encontrados; no devuelve el texto coincidente."""
    normalizado = normalizar(texto)
    return [i for i, patron in enumerate(_COMPILADOS) if patron.search(normalizado)]


def filtrar_documentos(
    recuperados: list[tuple[Document, float]],
) -> tuple[list[tuple[Document, float]], list[Document]]:
    """Separa limpios y descartados sobre la interfaz real del índice (`page_content`)."""
    limpios: list[tuple[Document, float]] = []
    descartados: list[Document] = []
    for documento, distancia in recuperados:
        patrones = detectar_inyeccion(documento.page_content)
        if not patrones:
            limpios.append((documento, distancia))
            continue
        descartados.append(documento)
        registrar_evento(
            "documento_descartado_por_inyeccion",
            nivel=logging.WARNING,
            id_chunk=str(documento.id),
            huella_fragmento=huella(documento.page_content),
            n_patrones=len(patrones),
            motivo="patron:" + ",".join(str(p) for p in patrones),
        )
    registrar_evento(
        "contexto_filtrado", n_limpios=len(limpios), n_descartados=len(descartados)
    )
    return limpios, descartados
