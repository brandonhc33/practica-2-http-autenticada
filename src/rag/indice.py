"""Índices Chroma verificables, separados por corpus y configuración."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.types import PyEmbedding
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.rag.corpus import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    cargar_corpus,
    fragmentar_documentos,
    huella,
    serializar_documentos,
    verificar_integridad,
)

RAIZ = Path(__file__).resolve().parents[2]
DIRECTORIO_INDICE = RAIZ / "vectorstore"
DIRECTORIO_EJEMPLO = RAIZ / "output" / "rag" / "vectorstore_ejemplo"
MODELO_EMBEDDINGS = "models/gemini-embedding-001"
DIMENSIONES = 3072
MANIFIESTO = "manifiesto.json"


def crear_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Usa tareas de retrieval del conector; el timeout limita cada intento del SDK."""
    return GoogleGenerativeAIEmbeddings(
        model=MODELO_EMBEDDINGS,
        output_dimensionality=DIMENSIONES,
        client_args={"timeout": 30},
    )


def preparar_indice(
    corpus: str = "ley-rep",
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    estrategia: str = "recursivo",
    *,
    modelo_embeddings: str = MODELO_EMBEDDINGS,
    dimensiones: int = DIMENSIONES,
) -> tuple[list[Document], dict[str, Any]]:
    """Prepara configuración y huellas antes de crear clientes o consumir cuota."""
    documentos = cargar_corpus(corpus)
    chunks = fragmentar_documentos(documentos, chunk_size, chunk_overlap, estrategia)
    integridad = verificar_integridad(documentos, chunks)
    if integridad["textos_duplicados"]:
        raise ValueError("Hay chunks de texto duplicado: revisa el corpus antes de indexar.")
    configuracion = {
        "formato": 1,
        "corpus": corpus,
        "corpus_sha256": huella(serializar_documentos(documentos)),
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "estrategia": estrategia,
        "modelo_embeddings": modelo_embeddings,
        "dimensiones": dimensiones,
        "distancia": "cosine",
        "coleccion": f"rag-{corpus}",
        "chunks_sha256": huella(serializar_documentos(chunks)),
        "cantidad_chunks": len(chunks),
    }
    return chunks, {
        "configuracion": configuracion,
        "huella_indice": huella(configuracion),
        "integridad": integridad,
    }


def leer_manifiesto(directorio: Path) -> dict[str, Any]:
    """Una ruta ausente o una indexación interrumpida no se convierten en un índice vacío."""
    try:
        datos = json.loads((directorio / MANIFIESTO).read_text(encoding="utf-8"))
        if datos["estado"] != "completo":
            raise ValueError
        if huella(datos["configuracion"]) != datos["huella_indice"]:
            raise ValueError
        return datos
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError(
            f"Índice ausente, incompleto o manifiesto inválido en {directorio}. "
            "Indexa en una carpeta nueva; no se borra ni repara automáticamente."
        ) from None


def _conectar(directorio: Path, datos: dict[str, Any], *, crear: bool = False) -> Chroma:
    return Chroma(
        collection_name=datos["configuracion"]["coleccion"],
        client=chromadb.PersistentClient(
            path=str(directorio.resolve()), settings=Settings(anonymized_telemetry=False),
        ),
        # Se pasan vectores explícitos; nunca activar el embedding automático de Chroma.
        embedding_function=None,
        collection_metadata={"hnsw:space": "cosine"},
        create_collection_if_not_exists=crear,
    )


def _verificar_contenido(indice: Chroma, datos: dict[str, Any]) -> None:
    guardados = indice.get(include=["documents", "metadatas"])
    docs = [
        Document(id=id_, page_content=texto, metadata=metadata or {})
        for id_, texto, metadata in zip(
            guardados["ids"], guardados["documents"] or [], guardados["metadatas"] or [],
            strict=True,
        )
    ]
    if len(docs) != datos["configuracion"]["cantidad_chunks"]:
        raise ValueError("El conteo del índice no coincide con el manifiesto.")
    # Chroma no garantiza el orden de get(); la huella del contenido sí debe coincidir.
    esperado, _ = preparar_indice(
        datos["configuracion"]["corpus"],
        datos["configuracion"]["chunk_size"],
        datos["configuracion"]["chunk_overlap"],
        datos["configuracion"]["estrategia"],
    )
    por_id = {d.id: d for d in docs}
    if set(por_id) != {d.id for d in esperado} or any(
        serializar_documentos([por_id[d.id]]) != serializar_documentos([d]) for d in esperado
    ):
        raise ValueError("Los textos, IDs o fuentes del índice no coinciden con el corpus.")


def abrir_indice(directorio: Path = DIRECTORIO_INDICE) -> tuple[Chroma, dict[str, Any]]:
    """Reconecta sin crear colecciones, generar embeddings ni aceptar configuraciones viejas."""
    datos = leer_manifiesto(directorio)
    config = datos["configuracion"]
    _, actual = preparar_indice(
        config["corpus"], config["chunk_size"], config["chunk_overlap"], config["estrategia"],
        modelo_embeddings=config["modelo_embeddings"], dimensiones=config["dimensiones"],
    )
    if actual["huella_indice"] != datos["huella_indice"]:
        raise ValueError("El corpus o el chunking cambió. Usa un índice nuevo.")
    try:
        indice = _conectar(directorio, datos)
        _verificar_contenido(indice, datos)
    except Exception as error:
        raise ValueError(f"El índice no es íntegro o no se puede abrir: {type(error).__name__}.") from error
    return indice, datos


def exigir_embeddings_reales(datos: dict[str, Any]) -> None:
    config = datos["configuracion"]
    if config["modelo_embeddings"] != MODELO_EMBEDDINGS or config["dimensiones"] != DIMENSIONES:
        raise ValueError("El índice no corresponde al modelo y dimensiones de embeddings reales.")


def indexar_corpus(
    chunks: list[Document],
    datos: dict[str, Any],
    embeddings: Embeddings,
    directorio: Path = DIRECTORIO_INDICE,
) -> dict[str, Any]:
    """Crea una vez; reutiliza lo compatible o falla sin borrar ni duplicar documentos."""
    if huella(serializar_documentos(chunks)) != datos["configuracion"]["chunks_sha256"]:
        raise ValueError("Los chunks no coinciden con la configuración preparada.")
    if directorio.exists():
        _, previo = abrir_indice(directorio)
        if previo["huella_indice"] != datos["huella_indice"]:
            raise ValueError("Ya existe otro índice. Elige una carpeta nueva.")
        return {**previo, "reutilizado": True}
    directorio.mkdir(parents=True, exist_ok=False)
    # Si falla después de mkdir, no queda un manifiesto de éxito; no se reutilizará.
    vectores = embeddings.embed_documents([c.page_content for c in chunks])
    dimensiones = datos["configuracion"]["dimensiones"]
    if len(vectores) != len(chunks) or any(len(v) != dimensiones for v in vectores):
        raise ValueError("La cantidad o dimensiones de los embeddings es incorrecta.")
    indice = _conectar(directorio, datos, crear=True)
    # La escritura por vectores evita el modelo automático de Chroma.
    cliente = chromadb.PersistentClient(
        path=str(directorio.resolve()), settings=Settings(anonymized_telemetry=False),
    )
    coleccion = cliente.get_collection(datos["configuracion"]["coleccion"], embedding_function=None)
    vectores_chroma: list[PyEmbedding] = list(vectores)
    coleccion.add(
        ids=[str(c.id) for c in chunks],
        documents=[c.page_content for c in chunks],
        metadatas=[c.metadata for c in chunks],
        embeddings=vectores_chroma,
    )
    _verificar_contenido(indice, datos)
    completo = {**datos, "estado": "completo", "creado_utc": datetime.now(UTC).isoformat()}
    with (directorio / MANIFIESTO).open("x", encoding="utf-8") as archivo:
        json.dump(completo, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    return {**completo, "reutilizado": False}
