"""Bloque 30: aplica el método de decisión al clasificador de rutas y genera el documento base."""

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.rag_comun import abrir_salida_nueva
from src.personalizacion.dataset import (
    RAIZ,
    RUTA_DATASET,
    cargar_dataset,
    construir_ejemplos,
    ejemplos_raw,
    huella_archivo,
    validar_dataset,
)
from src.personalizacion.decision import (
    PREGUNTAS,
    analizar_sensibilidad,
    derivar_respuestas,
    escenarios_pendientes,
    estimar_horas_faltantes,
    generar_esqueleto_decision,
    recomendar_estrategia,
)
from src.personalizacion.linea_base import huella_prompt

RUTA_HECHOS = RAIZ / "datos" / "personalizacion" / "hechos_decision.json"
OBJETIVO_EJEMPLOS = 200


def cargar_linea_base(ruta: Path, dataset: Path) -> dict[str, Any]:
    """Rechaza una medición hecha con otro dataset u otro prompt: no describiría este caso."""
    informe = json.loads(ruta.read_text(encoding="utf-8"))
    if informe.get("huella_dataset") != huella_archivo(dataset):
        raise ValueError("La línea base se midió con otra versión del dataset.")
    if informe.get("huella_prompt") != huella_prompt():
        raise ValueError("La línea base se midió con otra versión del prompt de clasificación.")
    return informe["resultado"]["resumen"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linea-base", type=Path, help="JSON de scripts.linea_base_rutas.")
    parser.add_argument("--hechos", type=Path, default=RUTA_HECHOS)
    parser.add_argument("--dataset", type=Path, default=RUTA_DATASET)
    parser.add_argument("--salida", type=Path, help="Markdown nuevo con el documento base.")
    args = parser.parse_args(argv)
    try:
        hechos = json.loads(args.hechos.read_text(encoding="utf-8"))
        examples = construir_ejemplos(ejemplos_raw(cargar_dataset(args.dataset)))
        linea_base = cargar_linea_base(args.linea_base, args.dataset) if args.linea_base else None
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"{error}\n")
    contradicciones = sum("contradice" in p for p in validar_dataset(examples))
    respuestas = derivar_respuestas(hechos["hechos"], len(examples), contradicciones, linea_base)

    print(f"Caso: {hechos['caso']}\n")
    for pregunta in PREGUNTAS:
        respuesta = respuestas[pregunta.clave]
        valor = "pendiente" if respuesta.valor is None else respuesta.valor
        print(f"- {pregunta.clave}: {valor}\n  {respuesta.evidencia}")
    valores = {clave: r.valor for clave, r in respuestas.items()}

    horas = estimar_horas_faltantes(
        len(examples), OBJETIVO_EJEMPLOS, hechos["supuestos_etiquetado"]
    )
    print(
        f"\nPara llegar a {OBJETIVO_EJEMPLOS} ejemplos faltan {horas['faltan']}: "
        f"{horas['horas_total']} horas ({horas['jornadas_de_8_horas']} jornadas), con los "
        "supuestos orientativos del curso."
    )

    if any(valor is None for valor in valores.values()):
        print("\nFalta medir una respuesta. Lo que recomendaría el método con cada resultado:")
        for escenario in escenarios_pendientes(valores):
            print(
                f"- {escenario['clave']} = {escenario['valor']}: {escenario['puntos']} "
                f"-> {', '.join(escenario['ganadoras'])}"
            )
        if args.salida:
            parser.exit(1, "No se genera el documento hasta tener la línea base completa.\n")
        return 0

    puntos, ganadoras = recomendar_estrategia(valores)
    sensibilidad = analizar_sensibilidad(valores)
    print(f"\nPuntos: {puntos}\nCandidatas: {ganadoras}\n\nSensibilidad:")
    for fila in sensibilidad:
        estado = "CAMBIA" if fila["cambia"] else "igual"
        print(f"- {fila['clave']} -> {fila['valor_probado']}: {fila['ganadoras']} [{estado}]")
    esqueleto = generar_esqueleto_decision(
        hechos["problema"], respuestas, puntos, ganadoras, sensibilidad
    )
    if args.salida:
        try:
            with abrir_salida_nueva(args.salida) as archivo:
                archivo.write(esqueleto)
        except OSError as error:
            parser.exit(1, f"{error}\n")
        print(f"\nDocumento base guardado en {args.salida}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
