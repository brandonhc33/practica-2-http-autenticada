"""Carga la copia local de Ley REP y prepara entradas para los prompts documentales."""

import json
import re
from pathlib import Path
from typing import Any

RUTA_CORPUS = Path(__file__).resolve().parent.parent / "datos" / "ley_rep" / "ley_20920.json"
TRANSITORIOS = ("primero", "segundo", "tercero", "cuarto")


def cargar_documento_ley_rep() -> dict[str, Any]:
    try:
        return json.loads(RUTA_CORPUS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError("No se pudo cargar datos/ley_rep/ley_20920.json.") from None


def obtener_fragmento_ley_rep(articulo: int | str) -> dict[str, Any]:
    numero = str(articulo).lower()
    parte = f"transitorio-{numero}" if numero in TRANSITORIOS else f"articulo-{numero}"
    identificador = f"ley20920-{parte}"
    for fragmento in cargar_documento_ley_rep()["fragmentos"]:
        if fragmento["id_fragmento"] == identificador:
            return fragmento
    raise ValueError("Artículo no disponible. Usa 1 a 46, o primero a cuarto transitorio.")


def _leer_objeto_json(mensaje: str) -> dict[str, Any]:
    try:
        datos = json.loads(mensaje)
    except ValueError:
        raise ValueError("El contexto de Ley REP debe ser un objeto JSON válido.") from None
    if not isinstance(datos, dict):
        raise ValueError("El contexto de Ley REP debe ser un objeto JSON.")
    return datos


def preparar_respuesta_rep(mensaje: str) -> str:
    """Una pregunta normal utiliza todos los artículos; un JSON conserva su contexto explícito."""
    datos: dict[str, Any]
    if mensaje.lstrip().startswith(("{", "[")):
        datos = _leer_objeto_json(mensaje)
        pregunta = datos.get("pregunta")
        if not isinstance(pregunta, str) or not pregunta.strip():
            raise ValueError("El JSON de Ley REP requiere una pregunta no vacía.")
        if "fragmentos" in datos:
            if not isinstance(datos["fragmentos"], list) or any(
                not isinstance(fragmento, dict) for fragmento in datos["fragmentos"]
            ):
                raise ValueError("fragmentos debe ser una lista de objetos JSON.")
            return mensaje
    else:
        if not mensaje.strip():
            raise ValueError("La pregunta de Ley REP no puede estar vacía.")
        datos = {"pregunta": mensaje}
    datos.setdefault("antecedentes", {})
    datos["fragmentos"] = cargar_documento_ley_rep()["fragmentos"]
    return json.dumps(datos, ensure_ascii=False)


def preparar_resumen_rep(mensaje: str) -> str:
    """Acepta un artículo local por número o un fragmento explícito en JSON."""
    if mensaje.lstrip().startswith(("{", "[")):
        _leer_objeto_json(mensaje)
        return mensaje
    coincidencia = re.fullmatch(
        r"(?:art[ií]culo\s+)?(\d+|(?:primero|segundo|tercero|cuarto)(?:\s+transitorio)?)",
        mensaje.strip(),
        re.IGNORECASE,
    )
    if coincidencia is None:
        raise ValueError("Para resumir, indica 'artículo 3' o entrega un fragmento como JSON.")
    numero = coincidencia[1].lower().split()[0]
    fragmento = obtener_fragmento_ley_rep(numero)
    return json.dumps(fragmento, ensure_ascii=False)
