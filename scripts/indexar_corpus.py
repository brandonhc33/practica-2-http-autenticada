"""Compara cortes, crea el índice una vez o verifica su persistencia sin API."""

import argparse
import json
from pathlib import Path

from scripts.rag_comun import abrir_salida_nueva, exigir_consumo
from src.rag.corpus import CHUNK_OVERLAP, CHUNK_SIZE, cargar_corpus, comparar_chunking
from src.rag.indice import (
    DIRECTORIO_EJEMPLO,
    DIRECTORIO_INDICE,
    abrir_indice,
    crear_embeddings,
    indexar_corpus,
    preparar_indice,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--comparar", action="store_true", help="Solo chunking local, sin API.")
    modo.add_argument("--verificar", action="store_true", help="Recarga el índice sin embeddings.")
    parser.add_argument("--corpus", choices=["ley-rep", "ejemplo"], default="ley-rep")
    parser.add_argument("--directorio", type=Path)
    parser.add_argument("--chunk-size", type=int)
    parser.add_argument("--chunk-overlap", type=int)
    parser.add_argument("--estrategia", choices=["recursivo", "fijo"], default="recursivo")
    parser.add_argument("--salida", type=Path, help="JSON nuevo opcional, nunca se sobrescribe.")
    parser.add_argument("--confirmar-consumo", action="store_true")
    args = parser.parse_args(argv)
    directorio = args.directorio or (
        DIRECTORIO_INDICE if args.corpus == "ley-rep" else DIRECTORIO_EJEMPLO
    )
    archivo = None
    try:
        if args.salida:
            archivo = abrir_salida_nueva(args.salida)
        if args.comparar:
            resultado = comparar_chunking(cargar_corpus(args.corpus))
        elif args.verificar:
            _, resultado = abrir_indice(directorio)
        else:
            tamano = args.chunk_size if args.chunk_size is not None else (
                CHUNK_SIZE if args.corpus == "ley-rep" else 150
            )
            overlap = args.chunk_overlap if args.chunk_overlap is not None else (
                CHUNK_OVERLAP if args.corpus == "ley-rep" else 20
            )
            chunks, datos = preparar_indice(args.corpus, tamano, overlap, args.estrategia)
            if directorio.exists():
                _, resultado = abrir_indice(directorio)
                if resultado["huella_indice"] != datos["huella_indice"]:
                    raise ValueError("Hay otro índice en esa carpeta. Usa --directorio nuevo.")
                resultado = {**resultado, "reutilizado": True}
            else:
                exigir_consumo(args.confirmar_consumo)
                resultado = indexar_corpus(chunks, datos, crear_embeddings(), directorio)
        texto = json.dumps(resultado, ensure_ascii=False, indent=2) + "\n"
        if archivo:
            archivo.write(texto)
        print(texto, end="")
        return 0
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")
    except Exception as error:
        parser.exit(1, f"No se pudo indexar: {type(error).__name__}. No se reintenta el flujo.\n")
    finally:
        if archivo:
            archivo.close()


if __name__ == "__main__":
    raise SystemExit(main())
