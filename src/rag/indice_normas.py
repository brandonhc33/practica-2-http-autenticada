"""Índice Chroma persistente que se actualiza por norma sin recalcular lo que no cambió.

El índice de los bloques 24 a 28 (`indice.py`) es inmutable y conserva sus mediciones.
Este agrega, reemplaza y retira fragmentos según las normas aprobadas.
"""

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.api.types import PyEmbedding
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.gobernanza.prompts import guardar_json
from src.rag.corpus import CHUNK_OVERLAP, CHUNK_SIZE, huella
from src.rag.indice import DIMENSIONES, MANIFIESTO, MODELO_EMBEDDINGS
from src.rag.normas import RAIZ, RUTA_NORMAS_ACTIVAS, preparar_activas

DIRECTORIO_NORMAS = RAIZ / "indice_normas"
COLECCION = "normas-rep"
LOTE = 25


def configuracion(
    modelo_embeddings: str = MODELO_EMBEDDINGS, dimensiones: int = DIMENSIONES
) -> dict[str, Any]:
    return {
        "formato": 2,
        "coleccion": COLECCION,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "estrategia": "recursivo",
        "modelo_embeddings": modelo_embeddings,
        "dimensiones": dimensiones,
        "distancia": "cosine",
    }


def huella_indice(config: dict[str, Any], normas: dict[str, dict[str, Any]]) -> str:
    return huella({"configuracion": config, "normas": {n: d["huella"] for n, d in normas.items()}})


def _cliente(directorio: Path) -> ClientAPI:
    return chromadb.PersistentClient(
        path=str(directorio.resolve()), settings=Settings(anonymized_telemetry=False)
    )


def leer_manifiesto(directorio: Path = DIRECTORIO_NORMAS) -> dict[str, Any]:
    try:
        datos = json.loads((directorio / MANIFIESTO).read_text(encoding="utf-8"))
        if datos["estado"] not in ("completo", "en_proceso"):
            raise ValueError
        return datos
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError(
            f"Índice de normas ausente o manifiesto inválido en {directorio}. Indexa primero."
        ) from None


def _guardados(coleccion: Collection) -> dict[str, Document]:
    datos = coleccion.get(include=["documents", "metadatas"])
    return {
        id_: Document(id=id_, page_content=texto, metadata=dict(metadata or {}))
        for id_, texto, metadata in zip(
            datos["ids"], datos["documents"] or [], datos["metadatas"] or [], strict=True
        )
    }


def comparar(
    esperados: list[Document], guardados: dict[str, Document]
) -> dict[str, list[str]]:
    """Qué cambia fragmento por fragmento. El vector depende solo del texto."""
    plan: dict[str, list[str]] = {
        "agregar": [], "reemplazar": [], "solo_metadata": [], "sin_cambios": [], "retirar": [],
    }
    for chunk in esperados:
        previo = guardados.get(str(chunk.id))
        if previo is None:
            plan["agregar"].append(str(chunk.id))
        elif previo.page_content != chunk.page_content:
            plan["reemplazar"].append(str(chunk.id))
        elif previo.metadata != chunk.metadata:
            plan["solo_metadata"].append(str(chunk.id))
        else:
            plan["sin_cambios"].append(str(chunk.id))
    plan["retirar"] = sorted(set(guardados) - {str(c.id) for c in esperados})
    return plan


def _por_norma(
    plan: dict[str, list[str]], esperados: list[Document], guardados: dict[str, Document]
) -> dict[str, dict[str, int]]:
    norma_de = {i: d.metadata["norma"] for i, d in guardados.items()}
    norma_de |= {str(c.id): c.metadata["norma"] for c in esperados}
    resumen: dict[str, dict[str, int]] = {}
    for cambio, ids in plan.items():
        for norma, cantidad in Counter(norma_de[i] for i in ids).items():
            resumen.setdefault(norma, {})[cambio] = cantidad
    return resumen


def _anotar(
    cambios: dict[str, dict[str, int]], calculados: int, *, interrumpida: bool
) -> dict[str, Any]:
    return {
        "fecha": datetime.now(UTC).isoformat(timespec="seconds"),
        "cambios_previstos": cambios,
        "embeddings_calculados": calculados,
        "interrumpida": interrumpida,
    }


def planificar(
    directorio: Path = DIRECTORIO_NORMAS,
    ruta_activas: Path = RUTA_NORMAS_ACTIVAS,
    raiz: Path = RAIZ,
) -> dict[str, Any]:
    """Muestra qué haría la actualización y cuánto texto habría que convertir, sin API."""
    esperados, normas = preparar_activas(ruta_activas, raiz)
    guardados: dict[str, Document] = {}
    if directorio.exists():
        leer_manifiesto(directorio)
        guardados = _guardados(
            _cliente(directorio).get_collection(COLECCION, embedding_function=None)
        )
    plan = comparar(esperados, guardados)
    nuevos = {*plan["agregar"], *plan["reemplazar"]}
    caracteres = sum(len(c.page_content) for c in esperados if str(c.id) in nuevos)
    return {
        "normas": normas,
        "cambios_por_norma": _por_norma(plan, esperados, guardados),
        "embeddings_por_calcular": len(nuevos),
        "caracteres_por_convertir": caracteres,
        "tokens_aproximados": (caracteres + 3) // 4,
    }


def actualizar_indice(
    embeddings: Embeddings,
    directorio: Path = DIRECTORIO_NORMAS,
    *,
    modelo_embeddings: str = MODELO_EMBEDDINGS,
    dimensiones: int = DIMENSIONES,
    ruta_activas: Path = RUTA_NORMAS_ACTIVAS,
    raiz: Path = RAIZ,
) -> dict[str, Any]:
    """Deja el índice igual a las normas aprobadas y solo convierte el texto que cambió.

    Se guarda por lotes: si se corta, el índice queda cerrado a consultas y la siguiente
    ejecución continúa sin repetir lo guardado.
    """
    esperados, normas = preparar_activas(ruta_activas, raiz)
    config = configuracion(modelo_embeddings, dimensiones)
    historial: list[dict[str, Any]] = []
    if directorio.exists():
        previo = leer_manifiesto(directorio)
        if previo["configuracion"] != config:
            raise ValueError("El índice usa otra configuración. Elige una carpeta nueva.")
        historial = previo["historial"]
    directorio.mkdir(parents=True, exist_ok=True)
    cliente = _cliente(directorio)
    coleccion = cliente.get_or_create_collection(
        COLECCION, embedding_function=None, metadata={"hnsw:space": "cosine"}
    )
    guardados = _guardados(coleccion)
    plan = comparar(esperados, guardados)
    cambios = _por_norma(plan, esperados, guardados)
    manifiesto = {
        "estado": "en_proceso",
        "configuracion": config,
        "normas": normas,
        "huella_indice": huella_indice(config, normas),
        "historial": historial,
    }
    ruta = directorio / MANIFIESTO
    pendiente = any(plan[c] for c in plan if c != "sin_cambios")
    if pendiente or not ruta.exists() or leer_manifiesto(directorio)["estado"] != "completo":
        guardar_json(ruta, manifiesto)

    nuevos = [c for c in esperados if str(c.id) in {*plan["agregar"], *plan["reemplazar"]}]
    for inicio in range(0, len(nuevos), LOTE):
        lote = nuevos[inicio : inicio + LOTE]
        try:
            vectores = embeddings.embed_documents([c.page_content for c in lote])
        except Exception:
            # Lo guardado hasta aquí también fue consumo: queda anotado antes de salir.
            manifiesto["historial"] = [*historial, _anotar(cambios, inicio, interrumpida=True)]
            guardar_json(ruta, manifiesto)
            raise
        if len(vectores) != len(lote) or any(len(v) != dimensiones for v in vectores):
            raise ValueError("La cantidad o dimensiones de los embeddings es incorrecta.")
        vectores_chroma: list[PyEmbedding] = list(vectores)
        coleccion.upsert(
            ids=[str(c.id) for c in lote],
            documents=[c.page_content for c in lote],
            metadatas=[c.metadata for c in lote],
            embeddings=vectores_chroma,
        )
    for chunk in esperados:
        if str(chunk.id) in plan["solo_metadata"]:
            # Reescribir con el mismo vector: update() conservaría claves retiradas.
            guardado = coleccion.get(ids=[str(chunk.id)], include=["embeddings"])["embeddings"]
            if guardado is None:
                raise ValueError("No se pudo leer un vector guardado.")
            coleccion.delete(ids=[str(chunk.id)])
            coleccion.add(
                ids=[str(chunk.id)], documents=[chunk.page_content],
                metadatas=[chunk.metadata], embeddings=guardado,
            )
    if plan["retirar"]:
        coleccion.delete(ids=plan["retirar"])
    _exigir_igual(esperados, _guardados(coleccion))

    if pendiente or not historial:
        historial = [*historial, _anotar(cambios, len(nuevos), interrumpida=False)]
    manifiesto |= {"estado": "completo", "historial": historial, "fragmentos": len(esperados)}
    guardar_json(ruta, manifiesto)
    return {
        **manifiesto,
        "cambios_por_norma": cambios,
        "embeddings_calculados": len(nuevos),
        "reutilizado": not pendiente,
    }


def _exigir_igual(esperados: list[Document], guardados: dict[str, Document]) -> None:
    plan = comparar(esperados, guardados)
    if any(plan[c] for c in plan if c != "sin_cambios"):
        raise ValueError("El índice no coincide con las normas aprobadas: actualízalo.")


def abrir_indice_normas(
    directorio: Path = DIRECTORIO_NORMAS,
    *,
    modelo_embeddings: str = MODELO_EMBEDDINGS,
    dimensiones: int = DIMENSIONES,
    ruta_activas: Path = RUTA_NORMAS_ACTIVAS,
    raiz: Path = RAIZ,
) -> tuple[Chroma, dict[str, Any]]:
    """Solo abre un índice completo e igual a lo aprobado; no crea ni corrige nada."""
    datos = leer_manifiesto(directorio)
    if datos["estado"] != "completo":
        raise ValueError("La actualización del índice quedó a medias: ejecútala de nuevo.")
    if datos["configuracion"] != configuracion(modelo_embeddings, dimensiones):
        raise ValueError("El índice usa otro modelo de embeddings u otra configuración.")
    esperados, normas = preparar_activas(ruta_activas, raiz)
    if datos["huella_indice"] != huella_indice(datos["configuracion"], normas):
        raise ValueError("Las normas aprobadas cambiaron: actualiza el índice.")
    cliente = _cliente(directorio)
    try:
        _exigir_igual(
            esperados, _guardados(cliente.get_collection(COLECCION, embedding_function=None))
        )
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(f"No se puede abrir el índice: {type(error).__name__}.") from error
    indice = Chroma(
        collection_name=COLECCION,
        client=cliente,
        embedding_function=None,
        collection_metadata={"hnsw:space": "cosine"},
        create_collection_if_not_exists=False,
    )
    return indice, datos
