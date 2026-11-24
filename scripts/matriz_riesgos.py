"""Actividad 32, paso 3: valida y ordena la matriz de riesgos del proyecto."""

import argparse
import sys
from pathlib import Path

from src.gobernanza.riesgos import (
    RUTA_MATRIZ,
    cargar_matriz,
    esta_en_el_limite,
    evaluar_matriz,
    tabla_markdown,
    validar_matriz,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matriz", type=Path, default=RUTA_MATRIZ)
    parser.add_argument("--markdown", action="store_true", help="Imprime la tabla para el documento.")
    args = parser.parse_args(argv)
    try:
        matriz = cargar_matriz(args.matriz)
        problemas = validar_matriz(matriz)
        if problemas:
            print(f"{len(problemas)} problemas:")
            print("\n".join(f"- {p}" for p in problemas))
            return 1
        filas = evaluar_matriz(matriz)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Matriz no válida: {type(error).__name__}: {error}\n")
    if args.markdown:
        print(tabla_markdown(filas))
        return 0
    print(f"{len(filas)} riesgos, 0 problemas")
    for f in filas:
        marca = " [AL LIMITE]" if f["al_limite"] else ""
        print(f"{f['categoria']:8} ({f['puntaje']:2}) - {f['riesgo']}{marca}")
        if f["supervision"]:
            s = f["supervision"]
            print(f"{'':16}supervisión: {s['control']} (B{s['bloque']})")
    print("\nRevisar con otra persona:", ", ".join(f["id"] for f in filas if f["al_limite"]))
    print("Contraste (1 x 1):", "al límite" if esta_en_el_limite(1, 1) else "no está al límite")
    return 0


if __name__ == "__main__":
    sys.exit(main())
