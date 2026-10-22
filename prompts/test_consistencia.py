"""Ejecuta al menos tres llamadas reales por prompt y guarda evidencia del Bloque 10.

Uso: uv run python -m prompts.test_consistencia
Este módulo no se ejecuta al importar el banco ni durante las pruebas unitarias.
"""

import argparse
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, sleep
from typing import Any

from dotenv import load_dotenv

from prompts.banco import BANCO_DE_PROMPTS, Prompt
from src.agente_gemini import ENDPOINT, consultar_gemini_raw, extraer_texto, extraer_uso
from src.catalogo import AGENTES
from src.costos import calcular_costo_gemini
from src.salida_estructurada import parsear_respuesta_json


def ahora_utc() -> str:
    return datetime.now(UTC).isoformat()


def evaluar_intento(prompt: Prompt, modelo: str, numero: int) -> dict[str, Any]:
    registro: dict[str, Any] = {
        "prompt": prompt.nombre,
        "numero": numero,
        "inicio_utc": ahora_utc(),
        "estado": "error_peticion",
        "error": None,
        "respuesta_proveedor": None,
        "datos_validados": None,
        "uso": None,
        "costo_estimado": None,
    }
    inicio = perf_counter()
    try:
        try:
            datos = consultar_gemini_raw(modelo, prompt.ejemplo_usuario, prompt=prompt.nombre)
        finally:
            registro["latencia_http_segundos"] = round(perf_counter() - inicio, 6)
        registro["respuesta_proveedor"] = datos
        registro["estado"] = "error_salida"
        uso = extraer_uso(datos.get("usage"))
        registro["uso"] = uso.model_dump() if uso is not None else None
        costo = calcular_costo_gemini(modelo, uso)
        registro["costo_estimado"] = costo.model_dump(mode="json") if costo is not None else None
        texto = extraer_texto(datos, exigir_completa=True)
        registro["datos_validados"] = parsear_respuesta_json(texto, prompt.nombre)
        registro["estado"] = "valido"
    except ValueError as error:
        registro["error"] = str(error)
    except KeyboardInterrupt:
        registro["estado"] = "interrumpido"
        registro["error"] = "Intento interrumpido; el consumo solo se conoce si fue recibido."
    return registro


def resumir(intentos: list[dict[str, Any]]) -> dict[str, Any]:
    resumen = {}
    for nombre in BANCO_DE_PROMPTS:
        casos = [intento for intento in intentos if intento["prompt"] == nombre]
        exitos = sum(intento["estado"] == "valido" for intento in casos)
        resumen[nombre] = {
            "exitos": exitos,
            "intentos": len(casos),
            "fallos": len(casos) - exitos,
            "fallos_estructura": sum(i["estado"] == "error_salida" for i in casos),
            "errores_peticion": sum(i["estado"] == "error_peticion" for i in casos),
            "interrumpidos": sum(i["estado"] == "interrumpido" for i in casos),
            "porcentaje_valido": round(exitos / len(casos) * 100, 2) if casos else None,
        }
    return resumen


def guardar_registro(ruta: Path, registro: dict[str, Any]) -> None:
    registro["resumen"] = resumir(registro["intentos"])
    ruta.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--modelo", choices=tuple(AGENTES["gemini"]["modelos"]), default="flash-lite"
    )
    parser.add_argument("--repeticiones", type=int, default=3)
    parser.add_argument(
        "--pausa", type=float, default=1.0, help="Segundos entre llamadas; mínimo 0."
    )
    parser.add_argument(
        "--salida", type=Path, default=Path(__file__).with_name("registro_resultados.json")
    )
    argumentos = parser.parse_args()
    if argumentos.repeticiones < 3:
        parser.error("La actividad requiere al menos 3 repeticiones por prompt.")
    if not math.isfinite(argumentos.pausa) or argumentos.pausa < 0:
        parser.error("--pausa debe ser un número finito mayor o igual a cero.")
    if argumentos.salida.exists():
        parser.error("El registro ya existe. Elige otro archivo con --salida para conservarlo.")

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    modelo = AGENTES["gemini"]["modelos"][argumentos.modelo]
    registro: dict[str, Any] = {
        "actividad": "Bloque 10: banco de prompts y consistencia estructural",
        "inicio_utc": ahora_utc(),
        "fin_utc": None,
        "estado": "en_curso",
        "modelo": modelo,
        "endpoint": ENDPOINT,
        "repeticiones_por_prompt": argumentos.repeticiones,
        "pausa_segundos": argumentos.pausa,
        "criterio": (
            "Finalización stop, objeto JSON válido y validación estricta de campos, "
            "tipos y restricciones Pydantic. Se tolera un único bloque Markdown envolvente."
        ),
        "alcance": "Mide estructura; no demuestra exactitud del contenido ni resistencia a inyección.",
        "banco": [
            {
                "nombre": prompt.nombre,
                "version": prompt.version,
                "system_instruction": prompt.system_instruction,
                "ejemplo_usuario": prompt.ejemplo_usuario,
                "claves_esperadas": list(prompt.tipo_salida.model_fields),
                "response_schema": prompt.response_schema,
            }
            for prompt in BANCO_DE_PROMPTS.values()
        ],
        "intentos": [],
    }
    argumentos.salida.parent.mkdir(parents=True, exist_ok=True)
    guardar_registro(argumentos.salida, registro)
    codigo_salida = 0
    try:
        for prompt in BANCO_DE_PROMPTS.values():
            for numero in range(1, argumentos.repeticiones + 1):
                if registro["intentos"]:
                    sleep(argumentos.pausa)
                intento = evaluar_intento(prompt, modelo, numero)
                registro["intentos"].append(intento)
                guardar_registro(argumentos.salida, registro)
                print(f"{prompt.nombre}, intento {numero}: {intento['estado']}", flush=True)
                if intento["error"]:
                    print(f"  {intento['error']}", flush=True)
                if intento["estado"] == "interrumpido":
                    raise KeyboardInterrupt
        if any(i["estado"] != "valido" for i in registro["intentos"]):
            codigo_salida = 1
        registro["estado"] = "completada" if codigo_salida == 0 else "con_fallos"
    except KeyboardInterrupt:
        codigo_salida = 130
        registro["estado"] = "interrumpida"
    finally:
        registro["fin_utc"] = ahora_utc()
        guardar_registro(argumentos.salida, registro)
    for nombre, valores in registro["resumen"].items():
        print(f"{nombre}: {valores['exitos']}/{valores['intentos']} respuestas válidas")
    print(f"Registro guardado en {argumentos.salida}")
    raise SystemExit(codigo_salida)


if __name__ == "__main__":
    main()
