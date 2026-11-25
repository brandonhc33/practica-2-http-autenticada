"""Autoevaluación del Gate 2: promedio ponderado y los cuatro no compensables.

Los puntajes vienen de un archivo con su justificación. Los no compensables no se
declaran: se obtienen ejecutando test_gate2.py.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
RUTA = RAIZ / "datos" / "evaluacion" / "autoevaluacion_gate2.json"
UMBRAL = 80
PRUEBAS = {
    "pipeline_corre_de_punta_a_punta": "test_1_pipeline_sin_excepciones",
    "respuestas_citan_fuente": "test_2_respuesta_cita_fuente",
    "logs_sin_contenido_crudo": "test_3_logs_sin_contenido_crudo",
    "supervision_humana_funciona": "test_4_supervision_pausa_y_reanuda",
}


def validar(dimensiones: dict[str, dict[str, Any]], raiz: Path = RAIZ) -> None:
    if round(sum(d["peso"] for d in dimensiones.values()), 9) != 1:
        raise ValueError("Los pesos deben sumar 1.")
    for nombre, d in dimensiones.items():
        if not 0 <= d["puntaje"] <= 100:
            raise ValueError(f"Puntaje fuera de 0 a 100: {nombre}.")
        if not d["a_favor"] or not d["en_contra"] or not (raiz / d["evidencia"]).is_file():
            raise ValueError(f"Falta justificación o evidencia: {nombre}.")


def promedio_ponderado(dimensiones: dict[str, dict[str, Any]]) -> float:
    return sum(d["puntaje"] * d["peso"] for d in dimensiones.values())


def evaluar_gate(promedio: float, no_compensables: dict[str, bool]) -> bool:
    return promedio >= UMBRAL and len(no_compensables) == 4 and all(no_compensables.values())


def ejecutar_pruebas() -> dict[str, bool]:
    resultado = {}
    for nombre, prueba in PRUEBAS.items():
        proceso = subprocess.run(
            [sys.executable, "-m", "pytest", f"test_gate2.py::{prueba}", "-q"],
            cwd=RAIZ, capture_output=True, text=True, check=False,
        )
        resultado[nombre] = proceso.returncode == 0
    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archivo", type=Path, default=RUTA)
    args = parser.parse_args(argv)
    try:
        datos = json.loads(args.archivo.read_text(encoding="utf-8"))
        validar(datos["dimensiones"])
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Autoevaluación no válida: {error}\n")
    print(datos["procedencia"])
    for nombre, d in datos["dimensiones"].items():
        print(f"\n{nombre}: {d['puntaje']} x {d['peso']:.2f} = {d['puntaje'] * d['peso']:.2f}")
        print(f"  a favor: {d['a_favor']}\n  en contra: {d['en_contra']}")
    promedio = promedio_ponderado(datos["dimensiones"])
    no_compensables = ejecutar_pruebas()
    print(f"\npromedio: {promedio:.1f} (umbral {UMBRAL})")
    for nombre, cumple in no_compensables.items():
        print(f"- {'cumple' if cumple else 'NO CUMPLE'}: {nombre}")
    aprueba = evaluar_gate(promedio, no_compensables)
    print("listo para entregar:", "sí" if aprueba else "no")
    return 0 if aprueba else 1


if __name__ == "__main__":
    sys.exit(main())
