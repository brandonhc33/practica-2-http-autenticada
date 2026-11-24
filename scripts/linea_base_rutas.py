"""Bloque 30: mide el clasificador actual del bloque 19 sobre el dataset etiquetado."""

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.rag_comun import abrir_salida_nueva, exigir_consumo
from src.catalogo import AGENTES
from src.orquestacion.modelo import crear_modelo
from src.personalizacion.dataset import (
    RUTA_DATASET,
    cargar_dataset,
    construir_ejemplos,
    ejemplos_raw,
    huella_archivo,
    referencias_disponibles,
    revisar_dataset,
)
from src.personalizacion.linea_base import (
    MUESTRA_MINIMA,
    UMBRAL_INCUMPLIMIENTO,
    ahora_utc,
    evaluar_regla_articulos,
    huella_prompt,
    medir_linea_base,
)

CRITERIO = (
    "Incumple si la salida, normalizada, no es la ruta etiquetada. Única excepción, escrita en el "
    "dataset: en a03 y a04 también se acepta «resumen», porque la persona pide un resumen que el "
    "flujo convierte en aclaración. Los fallos de la regla de artículos se cuentan aparte. Fijado "
    f"antes de medir: {UMBRAL_INCUMPLIMIENTO:.0%} o más sobre al menos {MUESTRA_MINIMA} respuestas."
)


def imprimir_regla_local(evaluacion: dict[str, Any]) -> None:
    print(
        f"Regla local de artículos: {evaluacion['articulos_correctos']} de "
        f"{evaluacion['total']} coinciden con la etiqueta."
    )
    for caso in evaluacion["casos"]:
        if not caso["articulo_correcto"]:
            print(
                f"- {caso['id']}: esperado {caso['articulo_esperado']}, "
                f"detectado {caso['articulo_detectado']}"
            )
    if evaluacion["rutas_inalcanzables"]:
        print(
            "Ninguna respuesta del modelo llevaría a la ruta etiquetada en: "
            + ", ".join(evaluacion["rutas_inalcanzables"])
        )


def cargar_tramo(
    ruta: Path, dataset: Path, nombre_modelo: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Solo continúa una medición interrumpida con el mismo dataset, prompt, modelo y criterio."""
    informe = json.loads(ruta.read_text(encoding="utf-8"))
    esperado = {
        "huella_dataset": huella_archivo(dataset),
        "huella_prompt": huella_prompt(),
        "modelo": nombre_modelo,
        "criterio": CRITERIO,
    }
    distintos = [clave for clave, valor in esperado.items() if informe[clave] != valor]
    if distintos:
        raise ValueError(f"cambió {', '.join(distintos)} desde el tramo anterior.")
    if informe["resultado"]["error"] is None:
        raise ValueError("la medición anterior no se interrumpió.")
    registros = informe["resultado"]["registros"]
    return registros, {
        "archivo": ruta.name,
        "sha256": huella_archivo(ruta),
        "inicio_utc": informe["inicio_utc"],
        "fin_utc": informe["fin_utc"],
        "respuestas": len(registros),
        "error": informe["resultado"]["error"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=RUTA_DATASET)
    parser.add_argument(
        "--solo-regla-local",
        action="store_true",
        help="Evalúa la detección de artículos sin Gemini ni clave.",
    )
    parser.add_argument("--salida", type=Path, help="JSON nuevo con la medición real.")
    parser.add_argument(
        "--continuar",
        type=Path,
        help="Medición interrumpida: conserva sus respuestas y consulta solo las que faltan.",
    )
    parser.add_argument(
        "--pausa", type=float, default=5.0, help="Segundos entre llamadas (5 por defecto)."
    )
    parser.add_argument("--confirmar-consumo", action="store_true")
    args = parser.parse_args(argv)
    try:
        dataset = cargar_dataset(args.dataset)
        problemas = revisar_dataset(
            construir_ejemplos(ejemplos_raw(dataset)), referencias_disponibles()
        )
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    if problemas:
        parser.exit(1, "El dataset no pasa la validación; corrígelo antes de medir.\n")
    regla_local = evaluar_regla_articulos(dataset)
    imprimir_regla_local(regla_local)
    if args.solo_regla_local:
        return 0
    if args.salida is None:
        parser.error("Indica --salida para la medición con Gemini o usa --solo-regla-local.")

    nombre_modelo = AGENTES["gemini"]["modelos"]["flash-lite"]
    previos: list[dict[str, Any]] = []
    tramo_anterior: dict[str, Any] | None = None
    if args.continuar is not None:
        try:
            previos, tramo_anterior = cargar_tramo(args.continuar, args.dataset, nombre_modelo)
        except (OSError, ValueError, KeyError) as error:
            parser.exit(1, f"No se puede continuar: {error}\n")
    try:
        exigir_consumo(args.confirmar_consumo)
        archivo = abrir_salida_nueva(args.salida)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    informe: dict[str, Any] = {
        "actividad": "Bloque 30: línea base del clasificador de rutas antes de personalizar",
        "tipo_ejecucion": "real",
        "inicio_utc": ahora_utc(),
        "modelo": nombre_modelo,
        "huella_dataset": huella_archivo(args.dataset),
        "huella_prompt": huella_prompt(),
        "criterio": CRITERIO,
        "regla_local": regla_local,
        "pausa_segundos": args.pausa,
        "tramo_anterior": tramo_anterior,
    }
    with archivo:
        try:
            informe["resultado"] = medir_linea_base(
                dataset,
                crear_modelo("flash-lite"),
                nombre_modelo,
                previos=previos,
                pausa_segundos=args.pausa,
            )
        finally:
            informe["fin_utc"] = ahora_utc()
            archivo.write(json.dumps(informe, ensure_ascii=False, indent=2) + "\n")
    resumen = informe["resultado"]["resumen"]
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    if informe["resultado"]["error"] is not None:
        print(f"Medición interrumpida: {informe['resultado']['error']}; no se reintenta.")
        return 1
    return 0 if resumen["completa"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
