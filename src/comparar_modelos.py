"""Evaluación real y reproducible de modelos Gemini para el Bloque 9 de Skillnest."""

import argparse
import json
import os
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Any

import requests
from dotenv import load_dotenv

from .agente_gemini import ENDPOINT, consultar_gemini_raw, extraer_uso
from .costos import TARIFAS_GEMINI, calcular_costo_gemini
from .esquemas import decimal_fijo

ENDPOINT_MODELOS = "https://generativelanguage.googleapis.com/v1beta/models"
MODELOS_CANDIDATOS = ("gemini-3.5-flash-lite", "gemini-3.6-flash")
CASOS = {
    "explicacion_api": (
        "Estoy aprendiendo Python. Explica qué es una API con una analogía cotidiana, "
        "cómo viaja una pregunta desde Python hasta Gemini y cómo vuelve la respuesta, "
        "y para qué sirve una API key. Responde en español, con secciones breves y "
        "entre 150 y 200 palabras."
    ),
    "errores_http": (
        "Una aplicación Python consulta Gemini con requests y usa un Bearer token "
        "distinto para proteger su API local. Explica cómo diagnosticar y resolver "
        "HTTP 401 de la API local, HTTP 429 de Gemini y un timeout al consultar Gemini. "
        "Distingue las dos credenciales y evita recomendar publicar secretos. "
        "Responde en español, con secciones breves y entre 150 y 200 palabras."
    ),
    "calculo_costo": (
        "Una consulta a una IA consume 1000 tokens de entrada y 2000 de salida, "
        "sin caché. La entrada cuesta USD 0.30 por millón y la salida USD 2.50 "
        "por millón. Usa un tipo de cambio hipotético de 950 CLP por USD. "
        "Calcula el costo de entrada, salida y total en USD, el total en CLP y "
        "el costo de 1000 consultas iguales. Muestra las operaciones, aclara "
        "que son estimaciones sin impuestos y no confundas tokens con palabras. "
        "Responde en español, con secciones breves y entre 150 y 200 palabras."
    ),
}


def ahora_utc() -> str:
    return datetime.now(UTC).isoformat()


def listar_modelos_disponibles() -> list[dict[str, Any]]:
    """Consulta todas las páginas y conserva solo metadatos públicos de modelos."""
    clave = os.getenv("GEMINI_API_KEY", "").strip()
    if not clave:
        raise ValueError("Falta GEMINI_API_KEY. Agrega tu clave en .env.")
    modelos = []
    parametros: dict[str, Any] = {"pageSize": 1000}
    while True:
        try:
            with requests.get(
                ENDPOINT_MODELOS,
                headers={"x-goog-api-key": clave},
                params=parametros,
                timeout=(10, 30),
                allow_redirects=False,
            ) as respuesta:
                if respuesta.status_code != 200:
                    raise ValueError(f"El inventario respondió HTTP {respuesta.status_code}.")
                datos = respuesta.json()
        except requests.RequestException:
            raise ValueError("No se pudo consultar el inventario de Gemini.") from None
        if not isinstance(datos, dict) or not isinstance(datos.get("models"), list):
            raise ValueError("El inventario de Gemini no contiene una lista de modelos.")
        campos = (
            "name",
            "displayName",
            "inputTokenLimit",
            "outputTokenLimit",
            "supportedGenerationMethods",
        )
        modelos.extend({campo: modelo.get(campo) for campo in campos} for modelo in datos["models"])
        siguiente = datos.get("nextPageToken")
        if not siguiente:
            return modelos
        parametros["pageToken"] = siguiente


def medir_consulta(modelo: str, mensaje: str) -> dict[str, Any]:
    """Cronometra solo el cliente HTTP; procesa tokens y monedas después del reloj."""
    registro: dict[str, Any] = {
        "inicio_utc": ahora_utc(),
        "modelo": modelo,
        "estado": "error",
        "error": None,
        "respuesta_proveedor": None,
        "uso": None,
        "costo_usd": None,
        "costo_clp": None,
        "tipo_cambio": None,
        "aviso_clp": None,
    }
    inicio = perf_counter()
    try:
        datos = consultar_gemini_raw(modelo, mensaje)
    except (ValueError, KeyboardInterrupt) as error:
        registro["latencia_segundos"] = round(perf_counter() - inicio, 6)
        if isinstance(error, KeyboardInterrupt):
            registro["estado"] = "interrumpida"
            registro["error"] = "Consulta interrumpida; consumo y costo desconocidos."
        else:
            registro["error"] = str(error)
        return registro
    registro["latencia_segundos"] = round(perf_counter() - inicio, 6)
    registro["respuesta_proveedor"] = datos
    uso = extraer_uso(datos.get("usage"))
    registro["uso"] = uso.model_dump() if uso is not None else None
    costo = calcular_costo_gemini(modelo, uso)
    if costo is not None:
        registro["costo_usd"] = decimal_fijo(costo.usd.total)
        registro["costo_clp"] = decimal_fijo(costo.clp.total) if costo.clp else None
        registro["tipo_cambio"] = (
            costo.tipo_cambio.model_dump(mode="json") if costo.tipo_cambio else None
        )
        registro["aviso_clp"] = costo.aviso_clp

    opciones = datos.get("choices")
    primera = opciones[0] if isinstance(opciones, list) and opciones else None
    mensaje_generado = primera.get("message") if isinstance(primera, dict) else None
    texto = mensaje_generado.get("content") if isinstance(mensaje_generado, dict) else None
    if (
        not isinstance(texto, str)
        or not texto.strip()
        or not isinstance(primera, dict)
        or primera.get("finish_reason") != "stop"
        or uso is None
    ):
        registro["estado"] = "incompleta"
        registro["error"] = "Falta texto, finalización stop o consumo válido; revisar el JSON."
    else:
        registro["estado"] = "ok"
    return registro


def resumir(registros: list[dict[str, Any]], modelos: list[str]) -> dict[str, Any]:
    """No convierte errores o consumo ausente en costos cero ni éxitos ficticios."""
    resumen = {}
    for modelo in modelos:
        intentos = [r for r in registros if r["modelo"] == modelo]
        completas = [r for r in intentos if r["estado"] == "ok"]
        latencias = [r["latencia_segundos"] for r in completas]
        valores: dict[str, Any] = {
            "intentos": len(intentos),
            "respuestas_completas": len(completas),
            "errores_o_incompletas": len(intentos) - len(completas),
            "latencia_media_segundos": round(mean(latencias), 6) if latencias else None,
            "latencia_mediana_segundos": round(median(latencias), 6) if latencias else None,
            "latencia_minima_segundos": min(latencias) if latencias else None,
            "latencia_maxima_segundos": max(latencias) if latencias else None,
        }
        for campo in ("entrada", "salida", "entrada_cache"):
            valores[f"tokens_{campo}_media"] = (
                round(mean(r["uso"][campo] for r in completas), 3) if completas else None
            )
        for moneda in ("usd", "clp"):
            campo = f"costo_{moneda}"
            costos = [Decimal(r[campo]) for r in completas if r[campo] is not None]
            observados = [Decimal(r[campo]) for r in intentos if r[campo] is not None]
            promedio = sum(costos) / Decimal(len(costos)) if costos else None
            valores[f"consultas_con_costo_{moneda}"] = len(costos)
            valores[f"costo_medio_{moneda}"] = (
                decimal_fijo(promedio) if promedio is not None else None
            )
            valores[f"proyeccion_1000_consultas_{moneda}"] = (
                decimal_fijo(promedio * 1000) if promedio is not None else None
            )
            valores[f"costo_observado_total_{moneda}"] = (
                decimal_fijo(sum(observados, Decimal(0))) if observados else None
            )
        resumen[modelo] = valores
    return resumen


def planificar(modelos: list[str], repeticiones: int):
    """Intercala candidatos y rota quién consulta primero para reducir sesgo temporal."""
    for ronda in range(1, repeticiones + 1):
        for indice, (caso, mensaje) in enumerate(CASOS.items()):
            desplazamiento = (ronda - 1 + indice) % len(modelos)
            orden = modelos[desplazamiento:] + modelos[:desplazamiento]
            for modelo in orden:
                yield ronda, caso, modelo, mensaje


def resumir_pares_completos(registros: list[dict[str, Any]], modelos: list[str]) -> dict[str, Any]:
    """Compara solo las mismas preguntas y rondas si algún candidato falla."""
    claves_por_modelo = [
        {(r["ronda"], r["caso"]) for r in registros if r["modelo"] == m and r["estado"] == "ok"}
        for m in modelos
    ]
    comunes = set.intersection(*claves_por_modelo)
    return resumir([r for r in registros if (r["ronda"], r["caso"]) in comunes], modelos)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listar-modelos", action="store_true", help="Lista sin generar texto.")
    parser.add_argument(
        "--modelos", nargs="+", choices=tuple(TARIFAS_GEMINI), default=list(MODELOS_CANDIDATOS)
    )
    parser.add_argument("--repeticiones", type=int, default=3)
    parser.add_argument(
        "--salida", type=Path, default=Path(f"docs/evaluaciones/gemini-{date.today()}.json")
    )
    argumentos = parser.parse_args()
    if argumentos.repeticiones < 1:
        parser.error("--repeticiones debe ser al menos 1.")
    if len(set(argumentos.modelos)) != len(argumentos.modelos):
        parser.error("No repitas modelos en --modelos.")
    if not argumentos.listar_modelos:
        if argumentos.salida.exists():
            parser.error("La salida ya existe. Usa --salida con otro nombre para conservarla.")
        if set(argumentos.modelos) & {"gemini-3.6-flash", "gemini-3.8-flash"} and (
            date.today() > date(2026, 12, 31)
        ):
            parser.error("Actualiza las tarifas promocionales de Gemini Flash en src/costos.py.")
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    try:
        disponibles = listar_modelos_disponibles()
    except ValueError as error:
        raise SystemExit(str(error)) from None
    if argumentos.listar_modelos:
        print(
            json.dumps(
                {"fecha_utc": ahora_utc(), "modelos": disponibles}, ensure_ascii=False, indent=2
            )
        )
        return
    nombres = {
        m["name"].removeprefix("models/")
        for m in disponibles
        if "generateContent" in (m.get("supportedGenerationMethods") or [])
    }
    if faltantes := set(argumentos.modelos) - nombres:
        parser.error(f"Modelos ausentes del inventario: {', '.join(sorted(faltantes))}.")
    datos: dict[str, Any] = {
        "inicio_utc": ahora_utc(),
        "fin_utc": None,
        "estado_ejecucion": "en_curso",
        "endpoint_consultas": ENDPOINT,
        "endpoint_inventario": ENDPOINT_MODELOS,
        "modelos_disponibles": disponibles,
        "modelos_evaluados": argumentos.modelos,
        "repeticiones_por_caso": argumentos.repeticiones,
        "casos": CASOS,
        "configuracion": {
            "parametros": "Predeterminados del proveedor; mismo cuerpo que la aplicación.",
            "streaming": False,
            "historial": False,
            "reintentos": 0,
            "timeout_conexion_segundos": 10,
            "timeout_lectura_segundos": 60,
            "latencia": "perf_counter alrededor de consultar_gemini_raw; excluye cálculo y dólar.",
            "orden": "Secuencial, intercalado y rotando el primer modelo por caso y ronda.",
        },
        "tarifas": {
            "fuente": "https://ai.google.dev/gemini-api/docs/pricing",
            "verificadas_el": "2026-10-20",
            "modalidad": "Standard de pago, USD por millón; no es facturación de la cuenta.",
            "flash_3_6_y_3_8_promocion_hasta": "2026-12-31",
            "modelos": {m: TARIFAS_GEMINI[m].model_dump(mode="json") for m in argumentos.modelos},
        },
        "mediciones": [],
    }
    argumentos.salida.parent.mkdir(parents=True, exist_ok=True)

    def guardar():
        datos["resumen"] = resumir(datos["mediciones"], argumentos.modelos)
        datos["resumen_pares_completos"] = resumir_pares_completos(
            datos["mediciones"], argumentos.modelos
        )
        argumentos.salida.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    guardar()
    total = len(CASOS) * argumentos.repeticiones * len(argumentos.modelos)
    for numero, (ronda, caso, modelo, mensaje) in enumerate(
        planificar(argumentos.modelos, argumentos.repeticiones), start=1
    ):
        registro = medir_consulta(modelo, mensaje)
        registro.update({"numero": numero, "ronda": ronda, "caso": caso})
        datos["mediciones"].append(registro)
        guardar()
        print(
            f"[{numero}/{total}] {modelo} / {caso}: {registro['estado']} "
            f"({registro['latencia_segundos']:.3f} s)",
            file=sys.stderr,
            flush=True,
        )
        if registro["estado"] == "interrumpida":
            datos["estado_ejecucion"] = "interrumpida"
            break
    datos["fin_utc"] = ahora_utc()
    if datos["estado_ejecucion"] != "interrumpida":
        datos["estado_ejecucion"] = "finalizada"
    guardar()
    print(json.dumps(datos["resumen"], ensure_ascii=False, indent=2))
    print(f"Evidencia: {argumentos.salida}", file=sys.stderr)
    if datos["estado_ejecucion"] == "interrumpida":
        raise SystemExit(130)
    if any(r["estado"] != "ok" for r in datos["mediciones"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
