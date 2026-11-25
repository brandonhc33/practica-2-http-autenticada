"""Mide la recuperación con las dos normas: precisión, exhaustividad y norma esperada.

`--motor palabras` es local y sirve de referencia. `--motor gemini` usa el índice
persistido y consume un embedding por pregunta: requiere --confirmar-consumo.
"""

import argparse
import json
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from scripts.rag_comun import abrir_salida_nueva, exigir_consumo
from src.gobernanza.prompts import guardar_json
from src.rag.evaluacion import evaluar_recuperacion, promediar
from src.rag.indice import crear_embeddings
from src.rag.indice_normas import abrir_indice_normas, actualizar_indice
from src.rag.normas import NORMAS, RAIZ, preparar_norma
from src.rag.recuperacion import validar_consulta
from src.rag.simulado import DIMENSIONES_LEXICO, MODELO_LEXICO, EmbeddingsDePalabras

RUTA_CASOS = RAIZ / "datos" / "evaluacion" / "recuperacion_normas.json"
KS = (3, 5)
# Fijados antes de medir con Gemini; no se ajustan al resultado.
CRITERIOS = {"una_norma": 0.9, "cruce": 0.75}


def cargar_casos(ruta: Path = RUTA_CASOS) -> list[dict[str, Any]]:
    """Rechaza etiquetas hechas sobre otro texto u otro corte."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    ids: set[str] = set()
    for norma, esperada in datos["huellas_normas"].items():
        chunks, resumen = preparar_norma(norma)
        if resumen["huella"] != esperada:
            raise ValueError(f"Las etiquetas de {norma} corresponden a otro texto. Revísalas.")
        ids |= {str(c.id) for c in chunks}
    preguntas = [c["pregunta"] for c in datos["casos"]]
    if len(preguntas) != len(set(preguntas)):
        raise ValueError("Hay preguntas repetidas.")
    for caso in datos["casos"]:
        validar_consulta(caso["pregunta"], max(KS))
        if not set(caso["ids_relevantes"]) <= ids or not caso["criterio"]:
            raise ValueError(f"Etiqueta incompleta o ausente del corpus: {caso['id']}.")
        if bool(caso["ids_relevantes"]) == (caso["grupo"] == "fuera"):
            raise ValueError(f"El grupo no corresponde a las etiquetas: {caso['id']}.")
    return datos["casos"]


def norma_de(id_chunk: str) -> str:
    return "ley-20920" if id_chunk.startswith("ley20920-") else "ds-12-2020"


def resumir(resultados: list[dict[str, Any]], k: int) -> dict[str, dict[str, Any]]:
    """Por grupo: promedios, casos con evidencia y casos con todas las normas esperadas."""
    resumen: dict[str, dict[str, Any]] = {}
    grupos: dict[str, tuple[str, ...]] = {
        "ley": ("ley",), "ds12": ("ds12",), "una_norma": ("ley", "ds12"), "cruce": ("cruce",),
    }
    for nombre, incluidos in grupos.items():
        casos = [r for r in resultados if r["grupo"] in incluidos]
        con_evidencia = con_normas = 0
        for r in casos:
            recuperados = r["por_k"][str(k)]["ids_recuperados"]
            con_evidencia += bool(set(recuperados) & set(r["ids_relevantes"]))
            # Cuenta evidencia de cada norma, no cualquier fragmento de esa norma.
            acertados = set(recuperados) & set(r["ids_relevantes"])
            con_normas += {norma_de(i) for i in acertados} == {
                norma_de(i) for i in r["ids_relevantes"]
            }
        resumen[nombre] = {
            "casos": len(casos),
            "precision": promediar(r["por_k"][str(k)]["precision"] for r in casos),
            "recall": promediar(r["por_k"][str(k)]["recall"] for r in casos),
            "con_evidencia": con_evidencia,
            "con_todas_las_normas": con_normas,
        }
    return resumen


def evaluar(
    indice: Chroma, embeddings: Embeddings, datos: dict[str, Any], motor: str
) -> dict[str, Any]:
    casos = cargar_casos()
    if set(datos["normas"]) != set(NORMAS):
        raise ValueError("La evaluación necesita las dos normas en el índice.")
    resultado = evaluar_recuperacion(indice, embeddings, casos, datos, KS)
    resultados = resultado["corridas"][0]["resultados"]
    resultado["motor"] = motor
    resultado["por_grupo"] = {str(k): resumir(resultados, k) for k in KS}
    en_5 = resultado["por_grupo"]["5"]
    resultado["criterios"] = {
        "una norma: evidencia entre los 5 primeros": {
            "minimo": CRITERIOS["una_norma"],
            "obtenido": en_5["una_norma"]["con_evidencia"] / en_5["una_norma"]["casos"],
        },
        "cruce: evidencia de todas las normas entre los 5 primeros": {
            "minimo": CRITERIOS["cruce"],
            "obtenido": en_5["cruce"]["con_todas_las_normas"] / en_5["cruce"]["casos"],
        },
    }
    for criterio in resultado["criterios"].values():
        criterio["cumple"] = criterio["obtenido"] >= criterio["minimo"]
    return resultado


def formatear(resultado: dict[str, Any]) -> str:
    lineas = [
        f"Motor: {resultado['motor']} | huella del índice: {resultado['huella_indice'][:12]}",
        f"Fecha UTC: {resultado['timestamp']}",
    ]
    for k, grupos in resultado["por_grupo"].items():
        lineas.append(f"\nk={k} | casos | precisión | exhaustividad | con evidencia | todas las normas")
        for nombre, g in grupos.items():
            lineas.append(
                f"{nombre} | {g['casos']} | {g['precision']:.3f} | {g['recall']:.3f} | "
                f"{g['con_evidencia']} | {g['con_todas_las_normas']}"
            )
    lineas.append("\nDetalle con k=5: exhaustividad | precisión | caso | pregunta")
    for r in resultado["corridas"][0]["resultados"]:
        m = r["por_k"]["5"]
        recall = "n/a" if m["recall"] is None else f"{m['recall']:.2f}"
        lineas.append(f"{recall} | {m['precision']:.2f} | {r['id']} | {r['pregunta']}")
    lineas.append("\nCriterios fijados antes de medir:")
    for nombre, c in resultado["criterios"].items():
        lineas.append(f"- {'cumple' if c['cumple'] else 'NO CUMPLE'}: {nombre}: "
                      f"{c['obtenido']:.2f}, mínimo {c['minimo']:.2f}")
    lineas.append("Mide los fragmentos recuperados, no la veracidad de la respuesta.")
    return "\n".join(lineas) + "\n"


def evaluar_palabras() -> dict[str, Any]:
    """Índice temporal con las dos normas; no depende de las aprobadas."""
    with tempfile.TemporaryDirectory() as carpeta:
        activas = Path(carpeta) / "activas.json"
        guardar_json(activas, {
            "normas": {n: {"huella": preparar_norma(n)[1]["huella"]} for n in NORMAS},
        })
        opciones: dict[str, Any] = {
            "modelo_embeddings": MODELO_LEXICO, "dimensiones": DIMENSIONES_LEXICO,
            "ruta_activas": activas,
        }
        embeddings = EmbeddingsDePalabras()
        actualizar_indice(embeddings, Path(carpeta) / "indice", **opciones)
        indice, datos = abrir_indice_normas(Path(carpeta) / "indice", **opciones)
        return evaluar(indice, embeddings, datos, "palabras")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motor", choices=["palabras", "gemini"], default="palabras")
    parser.add_argument("--salida", type=Path, help="TXT nuevo; también crea su .json.")
    parser.add_argument("--confirmar-consumo", action="store_true")
    args = parser.parse_args(argv)
    if args.salida and args.salida.suffix != ".txt":
        parser.error("--salida debe terminar en .txt.")
    try:
        abierto: tuple[Chroma, dict[str, Any]] | None = None
        if args.motor == "gemini":
            abierto = abrir_indice_normas()
            exigir_consumo(args.confirmar_consumo)
        with ExitStack() as pila:
            archivos = [
                pila.enter_context(abrir_salida_nueva(r))
                for r in (args.salida, args.salida.with_suffix(".json"))
            ] if args.salida else []
            if abierto is None:
                resultado = evaluar_palabras()
            else:
                indice, datos = abierto
                resultado = evaluar(indice, crear_embeddings(), datos, "gemini")
            texto = formatear(resultado)
            print(texto, end="")
            if archivos:
                archivos[0].write(texto)
                archivos[1].write(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n")
        return 0
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    except Exception as error:
        parser.exit(1, f"Evaluación interrumpida: {type(error).__name__}; no se inventan métricas.\n")


if __name__ == "__main__":
    sys.exit(main())
