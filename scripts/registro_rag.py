"""Registra consultas reales o las cuatro corridas mínimas de la actividad 28."""

import argparse
import json
from pathlib import Path

from scripts.rag_comun import abrir_salida_nueva, exigir_consumo
from src.catalogo import AGENTES
from src.orquestacion.modelo import crear_modelo
from src.rag.evaluacion import cargar_casos
from src.rag.indice import (
    DIRECTORIO_INDICE,
    abrir_indice,
    crear_embeddings,
    exigir_embeddings_reales,
)
from src.rag.recuperacion import validar_consulta
from src.rag.registro import registrar_consulta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("preguntas", nargs="*")
    parser.add_argument("--actividad-28", action="store_true", help="Tres preguntas, primera con k=3 y 6.")
    parser.add_argument("--k", type=int, choices=range(1, 21), default=3)
    parser.add_argument("--directorio", type=Path, default=DIRECTORIO_INDICE)
    parser.add_argument("--salida", type=Path, required=True, help="JSONL nuevo; guarda cada corrida inmediatamente.")
    parser.add_argument("--confirmar-consumo", action="store_true")
    args = parser.parse_args(argv)
    if args.actividad_28 and (args.preguntas or args.k != 3):
        parser.error("--actividad-28 fija sus preguntas y k; no se combina con preguntas ni otro --k.")
    if not args.actividad_28 and not args.preguntas:
        parser.error("Indica una pregunta o --actividad-28.")
    try:
        for pregunta in args.preguntas:
            validar_consulta(pregunta, args.k)
        indice, datos = abrir_indice(args.directorio)
        exigir_embeddings_reales(datos)
        if args.actividad_28:
            casos = cargar_casos(datos, set(indice.get()["ids"]))
            consultas = [(c["pregunta"], 3) for c in casos[:3]]
            consultas.append((casos[0]["pregunta"], 6))
        else:
            consultas = [(p, args.k) for p in args.preguntas]
        exigir_consumo(args.confirmar_consumo)
        with abrir_salida_nueva(args.salida) as archivo:
            embeddings = crear_embeddings()
            modelo = crear_modelo("flash-lite")
            for pregunta, k in consultas:
                registro = registrar_consulta(
                    pregunta, indice, datos, embeddings, modelo,
                    AGENTES["gemini"]["modelos"]["flash-lite"], k,
                    tipo_ejecucion="real",
                )
                archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
                archivo.flush()
                print(json.dumps(registro, ensure_ascii=False, indent=2))
                if registro["estado"] != "ok":
                    return 1
        return 0
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    except Exception as error:
        parser.exit(1, f"No se pudo iniciar el ensayo: {type(error).__name__}.\n")


if __name__ == "__main__":
    raise SystemExit(main())
