"""Matriz de riesgos: puntaje, categoría, límite y controles comprobables."""

import json
from pathlib import Path
from typing import Any

from src.gobernanza.prompts import RAIZ

RUTA_MATRIZ = RAIZ / "datos" / "gobernanza" / "matriz_riesgos.json"
MINIMO_RIESGOS = 5
CAMPOS = {"id", "riesgo", "probabilidad", "impacto", "por_que", "mitigaciones", "supervision"}


def puntaje_riesgo(probabilidad: int, impacto: int) -> int:
    for valor in (probabilidad, impacto):
        # bool es un int en Python, y "4" * 4 daría "4444" sin avisar.
        if not isinstance(valor, int) or isinstance(valor, bool) or not 1 <= valor <= 5:
            raise ValueError("Probabilidad e impacto deben ser enteros de 1 a 5.")
    return probabilidad * impacto


def categoria_riesgo(puntaje: int) -> str:
    """Cortes fijos del curso: 15, 9 y 4."""
    if puntaje >= 15:
        return "CRITICO"
    if puntaje >= 9:
        return "ALTO"
    if puntaje >= 4:
        return "MEDIO"
    return "BAJO"


def esta_en_el_limite(probabilidad: int, impacto: int) -> bool:
    """Indica si cambiar en un punto la probabilidad o el impacto cambia la categoría."""
    actual = categoria_riesgo(puntaje_riesgo(probabilidad, impacto))
    vecinos = [
        (probabilidad + 1, impacto), (probabilidad - 1, impacto),
        (probabilidad, impacto + 1), (probabilidad, impacto - 1),
    ]
    return any(
        categoria_riesgo(puntaje_riesgo(p, i)) != actual
        for p, i in vecinos
        if 1 <= p <= 5 and 1 <= i <= 5
    )


def cargar_matriz(ruta: Path = RUTA_MATRIZ) -> dict[str, Any]:
    return json.loads(ruta.read_text(encoding="utf-8"))


def evaluar_matriz(matriz: dict[str, Any]) -> list[dict[str, Any]]:
    """Agrega puntaje, categoría y límite, y ordena de mayor a menor."""
    filas = [
        {
            **r,
            "puntaje": (p := puntaje_riesgo(r["probabilidad"], r["impacto"])),
            "categoria": categoria_riesgo(p),
            "al_limite": esta_en_el_limite(r["probabilidad"], r["impacto"]),
        }
        for r in matriz["riesgos"]
    ]
    return sorted(filas, key=lambda f: (-f["puntaje"], f["id"]))


def validar_matriz(matriz: dict[str, Any], raiz: Path = RAIZ) -> list[str]:
    """Devuelve los problemas; una mitigación solo cuenta si su archivo existe."""
    problemas: list[str] = []
    riesgos = matriz.get("riesgos", [])
    if len(riesgos) < MINIMO_RIESGOS:
        problemas.append(f"hay {len(riesgos)} riesgos y se piden al menos {MINIMO_RIESGOS}")
    vistos: set[str] = set()
    construidas = 0
    for r in riesgos:
        nombre = str(r.get("id", "sin id"))
        if set(r) != CAMPOS:
            problemas.append(f"{nombre}: campos distintos de {sorted(CAMPOS)}")
            continue
        if nombre in vistos:
            problemas.append(f"{nombre}: id repetido")
        vistos.add(nombre)
        try:
            categoria = categoria_riesgo(puntaje_riesgo(r["probabilidad"], r["impacto"]))
        except ValueError as error:
            problemas.append(f"{nombre}: {error}")
            continue
        if not r["mitigaciones"]:
            problemas.append(f"{nombre}: no tiene mitigaciones")
        validas = 0
        for m in r["mitigaciones"]:
            if not (raiz / m["archivo"]).is_file():
                problemas.append(f"{nombre}: no existe {m['archivo']}")
            else:
                validas += 1
        construidas += bool(validas)
        if categoria in {"ALTO", "CRITICO"}:
            if not r["supervision"]:
                problemas.append(f"{nombre}: es {categoria} y no tiene punto de supervisión")
            elif not (raiz / r["supervision"]["archivo"]).is_file():
                problemas.append(f"{nombre}: no existe {r['supervision']['archivo']}")
    if construidas < 2:
        problemas.append("menos de dos riesgos tienen una mitigación ya construida")
    if riesgos and not problemas and not any(
        f["categoria"] in {"ALTO", "CRITICO"} for f in evaluar_matriz(matriz)
    ):
        problemas.append("ningún riesgo es ALTO o CRITICO: revisar las estimaciones")
    return problemas


def tabla_markdown(filas: list[dict[str, Any]]) -> str:
    lineas = [
        "| Riesgo | P | I | Puntaje | Categoría | Al límite | Mitigación construida | Supervisión |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for f in filas:
        mitigaciones = "; ".join(f"{m['control']} (B{m['bloque']})" for m in f["mitigaciones"])
        supervision = f["supervision"]["control"] if f["supervision"] else "No requerida"
        lineas.append(
            f"| {f['riesgo']} | {f['probabilidad']} | {f['impacto']} | {f['puntaje']} | "
            f"{f['categoria']} | {'Sí' if f['al_limite'] else 'No'} | {mitigaciones} | {supervision} |"
        )
    return "\n".join(lineas)
