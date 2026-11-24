"""Actividad 32, paso 1: versiones del prompt RAG, la activa y la diferencia entre ellas."""

import argparse
import sys

from src.gobernanza.prompts import (
    NOMBRE_PROMPT,
    RegistroDePrompts,
    diff_prompts,
    leer_activo,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diff", nargs=2, metavar=("ANTERIOR", "NUEVA"), help="Dos huellas.")
    args = parser.parse_args(argv)
    try:
        registro = RegistroDePrompts.cargar()
        activa = leer_activo()["huella"]
        versiones = [v for v in registro.versiones if v.nombre == NOMBRE_PROMPT]
        for v in versiones:
            print(f"{v.huella} - {v.fecha} - {v.nota}")
            print(f"  autor: {v.autor} | probado con: {v.modelo_probado or 'sin medir'}")
        print("huellas distintas:", len({v.huella for v in versiones}) == len(versiones))
        ultima = registro.ultima(NOMBRE_PROMPT)
        print("última registrada:", ultima.huella if ultima else "ninguna")
        print("activa:", registro.buscar(activa).huella)
        if args.diff:
            par = [registro.buscar(h) for h in args.diff]
        else:
            par = versiones[-2:]
        if len(par) == 2:
            print("\n" + "\n".join(diff_prompts(par[0], par[1])))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Registro de prompts no válido: {error}\n")


if __name__ == "__main__":
    sys.exit(main())
