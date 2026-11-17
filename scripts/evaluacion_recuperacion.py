"""Evalúa los casos etiquetados sin generación y conserva TXT y JSON de la corrida."""

import argparse
import json
from contextlib import ExitStack
from pathlib import Path

from scripts.rag_comun import abrir_salida_nueva, exigir_consumo
from src.rag.evaluacion import cargar_casos, evaluar_recuperacion, formatear_resultados
from src.rag.indice import (
    DIRECTORIO_INDICE,
    abrir_indice,
    crear_embeddings,
    exigir_embeddings_reales,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directorio", type=Path, default=DIRECTORIO_INDICE)
    parser.add_argument("--salida", type=Path, required=True, help="TXT nuevo; también crea su .json.")
    parser.add_argument("--k", type=int, nargs="+", default=[3, 5], choices=range(1, 21))
    parser.add_argument("--repeticiones", type=int, choices=[1, 2], default=1)
    parser.add_argument("--confirmar-consumo", action="store_true")
    args = parser.parse_args(argv)
    if args.salida.suffix != ".txt":
        parser.error("--salida debe terminar en .txt; su JSON usa el mismo nombre.")
    try:
        indice, datos = abrir_indice(args.directorio)
        exigir_embeddings_reales(datos)
        casos = cargar_casos(datos, set(indice.get()["ids"]))
        exigir_consumo(args.confirmar_consumo)
        with ExitStack() as pila:
            txt = pila.enter_context(abrir_salida_nueva(args.salida))
            salida_json = pila.enter_context(abrir_salida_nueva(args.salida.with_suffix(".json")))
            resultado = evaluar_recuperacion(
                indice, crear_embeddings(), casos, datos,
                tuple(dict.fromkeys(args.k)), args.repeticiones,
            )
            resultado["tipo_ejecucion"] = "real"
            texto = formatear_resultados(resultado)
            txt.write(texto)
            json.dump(resultado, salida_json, ensure_ascii=False, indent=2)
            salida_json.write("\n")
            print(texto, end="")
        return 0
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    except Exception as error:
        parser.exit(1, f"Evaluación interrumpida: {type(error).__name__}; no se inventan métricas.\n")


if __name__ == "__main__":
    raise SystemExit(main())
