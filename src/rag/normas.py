"""Normas disponibles y normas aprobadas: solo las segundas pueden entrar al índice."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from src.rag.corpus import (
    fragmentar_documentos,
    huella,
    serializar_documentos,
    verificar_integridad,
)

RAIZ = Path(__file__).resolve().parents[2]
# Señala en el texto lo que no venía como texto en la publicación.
MARCA_TABLA = "[Tabla transcrita de la imagen"
RUTA_NORMAS_ACTIVAS = RAIZ / "datos" / "gobernanza" / "normas_activas.json"


@dataclass(frozen=True)
class Norma:
    id: str
    nombre: str
    archivo: str


NORMAS = {
    n.id: n
    for n in (
        Norma("ley-20920", "Ley 20.920", "datos/ley_rep/ley_20920.json"),
        Norma("ds-12-2020", "DS 12/2020", "datos/ds_12_2020/ds_12_2020.json"),
    )
}


def buscar_norma(id_norma: str) -> Norma:
    if id_norma not in NORMAS:
        raise ValueError(f"Norma no disponible: {id_norma}. Usa {', '.join(NORMAS)}.")
    return NORMAS[id_norma]


def cargar_norma(id_norma: str, raiz: Path = RAIZ) -> list[Document]:
    """Un documento por artículo, con la norma y su fuente oficial en la metadata."""
    norma = buscar_norma(id_norma)
    datos = json.loads((raiz / norma.archivo).read_text(encoding="utf-8"))
    return [
        Document(
            id=f["id_fragmento"],
            page_content=f["texto"],
            metadata={
                "id_documento": f["id_fragmento"],
                "norma": norma.id,
                "documento": norma.nombre,
                "fuente": norma.archivo,
                "referencia": f["referencia"],
                "version": f["version_documento"],
                "paginas": ",".join(str(p) for p in f["paginas"]),
                "url": f["url"],
                "sha256_pdf": f["sha256_pdf"],
            },
        )
        for f in datos["fragmentos"]
    ]


def preparar_norma(id_norma: str, raiz: Path = RAIZ) -> tuple[list[Document], dict[str, Any]]:
    """Fragmentos y resumen verificado, sin red. La huella cubre texto y metadata."""
    documentos = cargar_norma(id_norma, raiz)
    chunks = fragmentar_documentos(documentos)
    integridad = verificar_integridad(documentos, chunks)
    return chunks, {
        "norma": id_norma,
        "nombre": buscar_norma(id_norma).nombre,
        "version": documentos[0].metadata["version"],
        "url": documentos[0].metadata["url"],
        "sha256_pdf": documentos[0].metadata["sha256_pdf"],
        "huella": huella(serializar_documentos(chunks)),
        "articulos": integridad["documentos"],
        "fragmentos": integridad["chunks"],
    }


def leer_normas_activas(ruta: Path = RUTA_NORMAS_ACTIVAS) -> dict[str, dict[str, Any]]:
    datos = json.loads(ruta.read_text(encoding="utf-8"))["normas"]
    for id_norma, norma in datos.items():
        buscar_norma(id_norma)
        if not isinstance(norma.get("huella"), str):
            raise ValueError(f"La norma activa {id_norma} no declara una huella.")
    return datos


def preparar_activas(
    ruta: Path = RUTA_NORMAS_ACTIVAS, raiz: Path = RAIZ
) -> tuple[list[Document], dict[str, dict[str, Any]]]:
    """Solo prepara lo aprobado. Si el texto cambió después, hay que aprobarlo otra vez."""
    chunks: list[Document] = []
    normas: dict[str, dict[str, Any]] = {}
    for id_norma, aprobada in leer_normas_activas(ruta).items():
        de_norma, resumen = preparar_norma(id_norma, raiz)
        if resumen["huella"] != aprobada["huella"]:
            raise ValueError(
                f"El texto de {id_norma} no es el aprobado: revísalo y actívalo de nuevo."
            )
        chunks.extend(de_norma)
        normas[id_norma] = resumen
    if not chunks:
        raise ValueError("No hay normas activas para indexar.")
    if len({c.page_content for c in chunks}) != len(chunks):
        raise ValueError("Hay fragmentos con el mismo texto: revisa las normas activas.")
    return chunks, normas
