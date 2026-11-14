"""Ensayo real del agente de Ley REP: casos fijos por bloque y la herramienta que se esperaba."""

import argparse
import json
import logging
import os
from dataclasses import astuple
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.runnables import Runnable

from src.catalogo import AGENTES
from src.costos.registro import ResumenCostosSesion, sesion_costos
from src.orquestacion.agente_con_herramientas import (
    HERRAMIENTAS,
    construir_ejecutor,
    consultar_agente,
)
from src.orquestacion.modelo import crear_modelo

RAIZ = Path(__file__).resolve().parent.parent

# Cada caso fija la herramienta que debería elegir el agente; None es "ninguna".
CASOS: dict[int, tuple[dict[str, Any], ...]] = {
    21: (
        {
            "consulta": "¿Qué obligaciones tienen los consumidores según la Ley REP?",
            "herramienta_esperada": "buscar_en_ley",
        },
        {
            "consulta": "¿Qué establece el artículo 12 de la Ley REP?",
            "herramienta_esperada": "obtener_articulo",
        },
        {
            "consulta": "Hola, ¿qué tipo de consultas puedes responder?",
            "herramienta_esperada": None,
        },
    ),
}


def describir_caso(
    caso: dict[str, Any], resultado: dict[str, Any], consumo: ResumenCostosSesion
) -> dict[str, Any]:
    """Compara la primera herramienta usada con la esperada y anota pasos y consumo."""
    pasos = [
        {
            "herramienta": accion.tool,
            "argumentos": accion.tool_input,
            "caracteres_observacion": len(str(observacion)),
        }
        for accion, observacion in resultado["intermediate_steps"]
    ]
    elegida = pasos[0]["herramienta"] if pasos else None
    return {
        **caso,
        "herramienta_elegida": elegida,
        "coincide": elegida == caso["herramienta_esperada"],
        "pasos": pasos,
        "respuesta": resultado["output"],
        # Sin error, el modelo responde una vez por paso y una vez más al final.
        "llamadas_esperadas": len(pasos) + 1,
        "llamadas_registradas": consumo.respuestas_con_costo
        + consumo.respuestas_sin_costo
        + consumo.consultas_fallidas,
        "consumo": consumo.como_dict(),
    }


def sumar_consumos(consumos: list[ResumenCostosSesion]) -> ResumenCostosSesion:
    """Suma campo por campo el consumo de cada caso."""
    total = ResumenCostosSesion()
    for consumo in consumos:
        total = ResumenCostosSesion(
            *(a + b for a, b in zip(astuple(total), astuple(consumo), strict=True))
        )
    return total


def ejecutar_ensayo(agente: Runnable, casos: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    """Ejecuta los casos en orden, cada uno con su propio registro de consumo."""
    descritos, consumos = [], []
    for caso in casos:
        # Una sesión por caso: así cada caso tiene su consumo, y el total se suma al final.
        with sesion_costos() as registro:
            resultado = consultar_agente(agente, caso["consulta"])
        consumos.append(registro.resumen())
        descritos.append(describir_caso(caso, resultado, consumos[-1]))
    return {
        "coincidencias": sum(caso["coincide"] for caso in descritos),
        "casos": descritos,
        "consumo_total": sumar_consumos(consumos).como_dict(),
    }


def main() -> None:
    """Ejecuta el ensayo de un bloque con Gemini y guarda el resultado en un JSON nuevo."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bloque", type=int, choices=sorted(CASOS), required=True)
    parser.add_argument(
        "--salida", type=Path, required=True, help="JSON nuevo; no sobrescribe evidencia."
    )
    args = parser.parse_args()
    if args.salida.exists():
        parser.error("La salida ya existe. Usa otra ruta para conservar la evidencia.")
    load_dotenv(RAIZ / ".env")
    clave = AGENTES["gemini"]["clave"]
    if not os.getenv(clave, "").strip():
        parser.error(f"Falta configurar {clave} en el archivo .env.")
    logging.basicConfig(level=logging.INFO)

    alias = "flash-lite"
    ejecutor = construir_ejecutor(crear_modelo(alias), HERRAMIENTAS)
    evidencia = {
        "bloque": args.bloque,
        "modelo": AGENTES["gemini"]["modelos"][alias],
        "fecha": datetime.now(UTC).isoformat(),
        **ejecutar_ensayo(ejecutor, CASOS[args.bloque]),
    }
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with args.salida.open("x", encoding="utf-8") as archivo:
        json.dump(evidencia, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    for caso in evidencia["casos"]:
        marca = "coincide" if caso["coincide"] else "NO coincide"
        print(f"{marca}: {caso['herramienta_elegida']} | {caso['consulta']}")
    print(f"Evidencia: {args.salida}")


if __name__ == "__main__":
    main()
