"""Documentos de origen, cortes reproducibles y comprobación local de cobertura."""

import hashlib
import json
from collections import Counter
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter

from src.prompts.contexto_ley_rep import cargar_documento_ley_rep

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
CORPUS_EJEMPLO = [
    "Los pedidos se pueden cancelar dentro de las primeras 24 horas despues de "
    "realizados, sin costo adicional.",
    "Las devoluciones se aceptan hasta 30 dias despues de la entrega, siempre que "
    "el producto este sin usar.",
    "El reembolso se procesa en un plazo de 5 a 10 dias habiles despues de recibir "
    "el producto devuelto.",
    "Los productos en oferta o liquidacion no tienen devolucion, salvo defecto de fabrica.",
    "El envio de una devolucion corre por cuenta del cliente, excepto cuando el "
    "producto llego danado.",
]


def huella(datos: Any) -> str:
    """Calcula una huella estable del contenido JSON, sin depender de su sangría."""
    texto = json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def cargar_corpus(nombre: str = "ley-rep") -> list[Document]:
    """Mantiene cada artículo como documento y la réplica de tienda como otro corpus."""
    if nombre == "ejemplo":
        return [
            Document(
                id=f"tienda-{i}",
                page_content=texto,
                metadata={
                    "id_documento": f"tienda-{i}",
                    "fuente": "réplica didáctica Skillnest 20456",
                    "referencia": f"Política {i + 1}",
                    "version": "ejemplo ficticio",
                },
            )
            for i, texto in enumerate(CORPUS_EJEMPLO)
        ]
    if nombre != "ley-rep":
        raise ValueError("Corpus no disponible: usa ley-rep o ejemplo.")
    return [
        Document(
            id=f["id_fragmento"],
            page_content=f["texto"],
            metadata={
                "id_documento": f["id_fragmento"],
                "fuente": "datos/ley_rep/ley_20920.json",
                "referencia": f["referencia"],
                "version": f["version_documento"],
                "paginas": ",".join(str(p) for p in f["paginas"]),
                "url": f["url"],
                "sha256_pdf": f["sha256_pdf"],
            },
        )
        for f in cargar_documento_ley_rep()["fragmentos"]
    ]


def serializar_documentos(documentos: list[Document]) -> list[dict[str, Any]]:
    return [
        {"id": d.id, "texto": d.page_content, "metadata": d.metadata}
        for d in documentos
    ]


def fragmentar_documentos(
    documentos: list[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    estrategia: str = "recursivo",
) -> list[Document]:
    """Divide dentro de cada documento, conservando offsets y sin chunks de espacios."""
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("Se requiere chunk_size > 0 y 0 <= chunk_overlap < chunk_size.")
    opciones = {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "add_start_index": True,
        "strip_whitespace": True,
    }
    if estrategia == "recursivo":
        splitter = RecursiveCharacterTextSplitter(**opciones)
    elif estrategia == "fijo":
        splitter = CharacterTextSplitter(separator="", **opciones)
    else:
        raise ValueError("Estrategia no disponible: usa fijo o recursivo.")
    chunks = []
    for documento in documentos:
        for numero, chunk in enumerate(splitter.split_documents([documento])):
            chunk.id = f"{documento.id}-c{numero:03d}"
            chunks.append(chunk)
    return chunks


def verificar_integridad(documentos: list[Document], chunks: list[Document]) -> dict[str, Any]:
    """Verifica cobertura por offsets: el overlap puede aumentar la suma de caracteres."""
    originales = {d.id: d for d in documentos}
    if not documentos or len(originales) != len(documentos) or None in originales:
        raise ValueError("El corpus debe tener documentos con IDs únicos y no vacíos.")
    cobertura = {d.id: bytearray(len(d.page_content)) for d in documentos}
    for c in chunks:
        origen = originales.get(c.metadata.get("id_documento"))
        inicio = c.metadata.get("start_index")
        if origen is None or not isinstance(inicio, int) or inicio < 0:
            raise ValueError("Un chunk no conserva su documento u offset de origen.")
        fin = inicio + len(c.page_content)
        if not c.page_content.strip() or origen.page_content[inicio:fin] != c.page_content:
            raise ValueError("Chunk vacío o texto distinto de su posición en el corpus.")
        if any(not c.metadata.get(campo) for campo in ("fuente", "referencia", "version")):
            raise ValueError("Falta metadata de fuente, referencia o versión.")
        cobertura[origen.id][inicio:fin] = b"\x01" * len(c.page_content)
    ids = [c.id for c in chunks]
    if not chunks or None in ids or len(ids) != len(set(ids)):
        raise ValueError("El índice debe tener chunks con IDs únicos.")
    perdidos = sum(
        not marca and not caracter.isspace()
        for d in documentos
        for marca, caracter in zip(cobertura[d.id], d.page_content, strict=True)
    )
    if perdidos:
        raise ValueError(f"El chunking perdió {perdidos} caracteres del corpus.")
    textos = Counter(c.page_content for c in chunks)
    return {
        "documentos": len(documentos),
        "chunks": len(chunks),
        "caracteres_corpus": sum(len(d.page_content) for d in documentos),
        "caracteres_chunks": sum(len(c.page_content) for c in chunks),
        "caracteres_sin_cubrir": perdidos,
        "espacios_de_borde_no_indexados": sum(m.count(0) for m in cobertura.values()),
        "textos_duplicados": sum(n - 1 for n in textos.values() if n > 1),
        "longitud_minima": min(len(c.page_content) for c in chunks),
        "longitud_maxima": max(len(c.page_content) for c in chunks),
    }


def comparar_chunking(documentos: list[Document]) -> list[dict[str, Any]]:
    """Compara dos estrategias y tamaños sobre el mismo corpus, sin llamar a una API."""
    resultados = []
    for estrategia in ("fijo", "recursivo"):
        for tamano in (400, 800):
            overlap = tamano // 8
            chunks = fragmentar_documentos(documentos, tamano, overlap, estrategia)
            ejemplo = [c for c in chunks if c.metadata["id_documento"] == "ley20920-articulo-9"]
            resultados.append({
                "estrategia": estrategia,
                "chunk_size": tamano,
                "chunk_overlap": overlap,
                **verificar_integridad(documentos, chunks),
                "ejemplo_articulo_9": serializar_documentos(ejemplo),
            })
    return resultados
