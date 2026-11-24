"""Bloque 29: construye, revisa el balance y valida el dataset de rutas sin llamar a la API."""

import argparse
from pathlib import Path

from src.personalizacion.dataset import (
    RAZON_BALANCE_MAXIMA,
    RUTA_DATASET,
    cargar_dataset,
    chequear_balance,
    comprobar_modo_desarrollador,
    construir_configuracion_peft,
    construir_ejemplos,
    ejemplos_raw,
    generar_casos_rotos,
    huella_archivo,
    referencias_disponibles,
    resumir_balance,
    revisar_dataset,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=RUTA_DATASET)
    parser.add_argument(
        "--comprobar-validador",
        action="store_true",
        help="Rompe copias del dataset a propósito y confirma que cada defecto se detecta.",
    )
    parser.add_argument(
        "--comprobar-api",
        action="store_true",
        help="Revisa sin red si la API para desarrolladores aceptaría la configuración PEFT.",
    )
    args = parser.parse_args(argv)
    try:
        dataset = cargar_dataset(args.dataset)
        referencias = referencias_disponibles()
    except ValueError as error:
        parser.exit(1, f"{error}\n")

    pares = ejemplos_raw(dataset)
    examples = construir_ejemplos(pares)
    print("Paso 1: dataset")
    print(f"{len(examples)} ejemplos construidos")
    print(examples[0])
    print(f"huella sha256: {huella_archivo(args.dataset)}")

    print("\nPaso 2: balance por ruta")
    balance = resumir_balance(chequear_balance(pares, "ruta"))
    for ruta, cuenta in balance["conteos"].items():
        print(f"{ruta}: {cuenta}")
    razon = balance["razon_max_min"]
    texto_razon = "sin definir: hay una ruta sin ejemplos" if razon is None else f"{razon:.1f}x"
    print(f"razon max/min: {texto_razon} (umbral del proyecto: {RAZON_BALANCE_MAXIMA:.1f}x)")
    con_articulo = sum(salida["articulo"] is not None for _, salida in pares)
    print(f"con articulo: {con_articulo}; sin articulo: {len(pares) - con_articulo}")

    print("\nPaso 3: validación")
    problemas = revisar_dataset(examples, referencias)
    print(f"{len(examples)} ejemplos, {len(problemas)} problemas encontrados")
    for problema in problemas:
        print(" -", problema)
    resultado = 0 if not problemas and balance["aceptable"] else 1

    if args.comprobar_validador:
        print("\nComprobación del validador con copias rotas a propósito")
        for descripcion, rotos in generar_casos_rotos(examples):
            hallados = revisar_dataset(rotos, referencias)
            estado = "detectado" if hallados else "NO DETECTADO"
            print(f"- {descripcion}: {estado}: {'; '.join(hallados)}")
            if not hallados:
                resultado = 1

    if args.comprobar_api:
        print("\nPaso 4 sin red: configuración PEFT demostrativa")
        config = construir_configuracion_peft()
        print(
            f"tuning_mode={config.tuning_mode}, adapter_size={config.adapter_size}, "
            f"epoch_count={config.epoch_count}"
        )
        motivo = comprobar_modo_desarrollador(config)
        if motivo:
            print("La API para desarrolladores la rechazaría antes de enviar:")
            print(f"  {motivo}")
            print("No se envía ningún trabajo: PEFT requiere Gemini Enterprise Agent Platform.")
        else:
            print("La conversión local no encontró parámetros incompatibles.")
    return resultado


if __name__ == "__main__":
    raise SystemExit(main())
