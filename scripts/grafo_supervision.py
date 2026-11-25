"""Actividad 32, paso 2: pausar acciones de alto riesgo hasta una decisión humana.

`demo` recorre aprobación y rechazo con copias temporales y decisiones simuladas. Los
demás comandos trabajan con el estado real guardado en output/gobernanza/.
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from src.gobernanza.prompts import (
    RAIZ,
    RUTA_ACTIVO,
    RUTA_PROMPTS,
    RegistroDePrompts,
    diff_prompts,
    leer_activo,
)
from src.gobernanza.supervision import (
    Acciones,
    abrir_guardado,
    construir_grafo,
    hilos_pendientes,
    pendiente,
    proponer,
    registrar_decision,
    resolver,
)
from src.rag.normas import MARCA_TABLA, NORMAS, cargar_norma, preparar_norma
from src.rag.servicio import nombre_fuente


def demo() -> int:
    """No toca el prompt activo del proyecto."""
    with tempfile.TemporaryDirectory() as carpeta:
        prompts = Path(carpeta) / "prompts.json"
        activo = Path(carpeta) / "activo.json"
        shutil.copy(RUTA_PROMPTS, prompts)
        shutil.copy(RUTA_ACTIVO, activo)
        acciones = Acciones(prompts, activo)
        grafo = construir_grafo(acciones, InMemorySaver())
        base = leer_activo(activo)["huella"]
        nueva = next(
            v.huella for v in RegistroDePrompts.cargar(prompts).versiones if v.huella != base
        )
        objeto = {"huella": nueva, "base": base}
        for aprobar in (False, True):
            hilo = proponer(grafo, acciones, "activar_prompt", objeto)
            print("1) pausado, pendiente:", pendiente(grafo, hilo))
            print("   activo mientras espera:", leer_activo(activo)["huella"])
            print(f"2) decisión simulada = {aprobar}:", resolver(grafo, hilo, aprobar, nueva))
            print("   activo después:", leer_activo(activo)["huella"])
            try:
                resolver(grafo, hilo, True, nueva)
            except ValueError as error:
                print("3) segundo intento sobre el mismo hilo:", error)
    print("Demostración con copias temporales: el prompt del proyecto no cambió.")
    return 0


def mostrar_objeto(espera: dict[str, Any], raiz: Path = RAIZ) -> None:
    """Todo lo que la persona necesita para decidir, sin abrir otros archivos."""
    objeto = espera["objeto"]
    if "base" in objeto:
        registro = RegistroDePrompts.cargar()
        print("\n".join(diff_prompts(
            registro.buscar(objeto["base"]), registro.buscar(espera["huella"])
        )))
    if "borrador" in objeto:
        borrador = json.loads((raiz / objeto["borrador"]).read_text(encoding="utf-8"))
        print(f"\nConsulta: {borrador['pregunta']}\n\n{borrador['respuesta']}\n")
        for fuente in borrador["fuentes"]:
            print(f"--- Texto de [{fuente['cita']}] {nombre_fuente(fuente)}\n{fuente['texto']}\n")
        print("Comprueba que cada afirmación, número, condición y categoría esté en su fuente.")
    if "norma" in objeto:
        for articulo in cargar_norma(objeto["norma"], raiz):
            # Lo transcrito es lo que más necesita una revisión contra la publicación.
            if MARCA_TABLA in articulo.page_content:
                tabla = articulo.page_content.split(MARCA_TABLA, 1)[1].split("\n\n", 1)[0]
                print(f"{articulo.metadata['referencia']} {MARCA_TABLA}{tabla}\n")
        for campo, valor in preparar_norma(objeto["norma"], raiz)[1].items():
            print(f"{campo}: {valor}")
        print("Comprueba la fuente oficial, la fecha, las tablas y si hubo cambios posteriores.")


def leer_decision() -> bool | None:
    """Solo s o n en una terminal deciden; lo demás deja la solicitud pendiente."""
    if not sys.stdin.isatty():
        return None
    try:
        respuesta = input("¿Aprobar esta acción? [s/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return None
    return {"s": True, "n": False}.get(respuesta)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("demo", help="Aprobación y rechazo simulados, sin efectos.")
    p = comandos.add_parser("proponer-prompt", help="Pausar la activación de una versión.")
    p.add_argument("huella")
    p = comandos.add_parser("proponer-evidencia", help="Pausar la copia a docs/evidencias/.")
    p.add_argument("origen")
    p.add_argument("destino")
    for nombre, ayuda in (
        ("proponer-norma", "Pausar la activación de una norma."),
        ("proponer-retiro", "Pausar el retiro de una norma."),
    ):
        p = comandos.add_parser(nombre, help=ayuda)
        p.add_argument("norma", choices=sorted(NORMAS))
    comandos.add_parser("pendientes", help="Listar lo que espera una decisión.")
    p = comandos.add_parser("decidir", help="Revisar y decidir en la terminal.")
    p.add_argument("hilo")
    args = parser.parse_args(argv)
    if args.comando == "demo":
        return demo()
    try:
        acciones = Acciones()
        guardado = abrir_guardado()
        grafo = construir_grafo(acciones, guardado)
        if args.comando == "pendientes":
            hilos = hilos_pendientes(guardado, grafo)
            for hilo in hilos:
                print(hilo, pendiente(grafo, hilo))
            if not hilos:
                print("No hay acciones pendientes.")
            return 0
        if args.comando == "decidir":
            espera = pendiente(grafo, args.hilo)
            if espera is None:
                raise ValueError("Ese hilo no tiene ninguna aprobación pendiente.")
            print(f"Acción: {espera['motivo']}\nObjeto: {espera['objeto']}\nHuella: {espera['huella']}")
            mostrar_objeto(espera)
            decision = leer_decision()
            if decision is None:
                print("Sin decisión explícita: la acción sigue pendiente.")
                return 1
            resultado = resolver(grafo, args.hilo, decision, espera["huella"], registrar_decision)
            print(resultado)
            return 0 if decision is False or not resultado.startswith("no aplicada") else 1
        if args.comando == "proponer-prompt":
            accion = "activar_prompt"
            objeto = {"huella": args.huella, "base": leer_activo()["huella"]}
        elif args.comando in ("proponer-norma", "proponer-retiro"):
            accion = "activar_norma" if args.comando == "proponer-norma" else "retirar_norma"
            objeto = {"norma": args.norma}
        else:
            accion = "publicar_evidencia"
            objeto = {"origen": args.origen, "destino": args.destino}
        hilo = proponer(grafo, acciones, accion, objeto)
        print(f"Pausado: no se aplicó ningún cambio. Hilo: {hilo}")
        print(f"Para revisar y decidir: uv run python -m scripts.grafo_supervision decidir {hilo}")
        return 0
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    sys.exit(main())
