"""Relevancia por chunk etiquetada antes de consultar, independiente de la generación."""

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from src.rag.indice import RAIZ
from src.rag.recuperacion import buscar_por_vector, validar_consulta

RUTA_CASOS = RAIZ / "datos" / "evaluacion" / "recuperacion_rag.json"


def precision_at_k(ids_recuperados: list[str], ids_relevantes: set[str]) -> float:
    recuperados = set(ids_recuperados)
    return len(recuperados & ids_relevantes) / len(recuperados) if recuperados else 0.0


def recall_at_k(ids_recuperados: list[str], ids_relevantes: set[str]) -> float | None:
    if not ids_relevantes:
        return None
    return len(set(ids_recuperados) & ids_relevantes) / len(ids_relevantes)


def promediar(valores: Iterable[float | None]) -> float | None:
    validos = [v for v in valores if v is not None]
    return sum(validos) / len(validos) if validos else None


def cargar_casos(
    manifiesto: dict[str, Any], ids_indice: set[str], ruta: Path = RUTA_CASOS,
) -> list[dict[str, Any]]:
    """Rechaza etiquetas obsoletas o incompletas antes de pedir embeddings."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if datos["huella_indice"] != manifiesto["huella_indice"]:
        raise ValueError("Las etiquetas corresponden a otro corpus o chunking. Revísalas primero.")
    casos = datos["casos"]
    if not 8 <= len(casos) <= 15:
        raise ValueError("Se requieren entre 8 y 15 preguntas etiquetadas.")
    preguntas = set()
    for caso in casos:
        pregunta = caso["pregunta"]
        relevantes = caso["ids_relevantes"]
        validar_consulta(pregunta, 3)
        if pregunta in preguntas or not isinstance(relevantes, list):
            raise ValueError("Preguntas duplicadas o ids_relevantes no es una lista.")
        if any(not isinstance(id_, str) for id_ in relevantes):
            raise ValueError("Los IDs relevantes deben ser textos.")
        if len(relevantes) != len(set(relevantes)) or not set(relevantes) <= ids_indice:
            raise ValueError("Las etiquetas contienen IDs duplicados o ausentes del índice.")
        if not caso.get("criterio"):
            raise ValueError("Falta justificar la relevancia leyendo el corpus.")
        preguntas.add(pregunta)
    return casos


def evaluar_recuperacion(
    indice: Chroma,
    embeddings: Embeddings,
    casos: list[dict[str, Any]],
    manifiesto: dict[str, Any],
    ks: tuple[int, ...] = (3, 5),
    repeticiones: int = 1,
) -> dict[str, Any]:
    """Recupera un ranking por pregunta y repetición; evalúa sus prefijos sin generar texto."""
    if repeticiones not in (1, 2) or not ks:
        raise ValueError("Usa una o dos repeticiones y al menos un k.")
    for k in ks:
        validar_consulta("evaluación", k)
    corridas = []
    for _ in range(repeticiones):
        resultados = []
        for caso in casos:
            vector = embeddings.embed_query(caso["pregunta"])
            ranking = buscar_por_vector(indice, vector, max(ks))
            ids = [str(d.id) for d, _ in ranking]
            metricas = {}
            for k in ks:
                metricas[str(k)] = {
                    "ids_recuperados": ids[:k],
                    "precision": precision_at_k(ids[:k], set(caso["ids_relevantes"])),
                    "recall": recall_at_k(ids[:k], set(caso["ids_relevantes"])),
                }
            resultados.append({**caso, "por_k": metricas})
        corridas.append({
            "resultados": resultados,
            "promedios": {
                str(k): {
                    "precision": promediar(r["por_k"][str(k)]["precision"] for r in resultados),
                    "recall": promediar(r["por_k"][str(k)]["recall"] for r in resultados),
                } for k in ks
            },
        })
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "huella_indice": manifiesto["huella_indice"],
        "configuracion_indice": manifiesto["configuracion"],
        "ks": list(ks),
        "repeticiones": repeticiones,
        "repeticiones_identicas": corridas[0] == corridas[1] if repeticiones == 2 else None,
        "corridas": corridas,
        "alcance": "Relevancia por chunk; no mide veracidad ni calidad de la respuesta generada.",
    }


def formatear_resultados(evaluacion: dict[str, Any]) -> str:
    lineas = [
        f"Fecha UTC: {evaluacion['timestamp']}",
        f"Huella del índice: {evaluacion['huella_indice']}",
        "Configuración: " + json.dumps(evaluacion["configuracion_indice"], ensure_ascii=False),
    ]
    for i, corrida in enumerate(evaluacion["corridas"], start=1):
        lineas.append(f"\nCorrida {i}")
        for k, promedios in corrida["promedios"].items():
            lineas.append(f"\nk={k} | precisión | recall | pregunta")
            for caso in corrida["resultados"]:
                m = caso["por_k"][k]
                recall = "n/a" if m["recall"] is None else f"{m['recall']:.3f}"
                lineas.append(f"{m['precision']:.3f} | {recall} | {caso['pregunta']}")
            lineas.append(f"Promedios: {promedios}")
    lineas.append(f"\nRepeticiones idénticas: {evaluacion['repeticiones_identicas']}")
    return "\n".join(lineas) + "\n"
