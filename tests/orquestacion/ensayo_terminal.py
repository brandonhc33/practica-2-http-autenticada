"""Diagnóstico interactivo del agente con modelo falso, sin Gemini ni archivos de operación."""

import argparse
import json
import logging
import os
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage

from src.orquestacion.agente_con_herramientas import (
    HERRAMIENTAS,
    construir_agente_con_memoria,
    construir_ejecutor,
    consultar_agente,
)
from src.orquestacion.supervision import esperar_aprobacion
from tests.orquestacion.modelo_falso import crear_modelo_falso, pedir_herramienta


def main() -> None:
    """Pide s y n por el circuito del agente, con registros solo en una carpeta temporal."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiempo-limite", type=float, default=60)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    print(
        "DIAGNÓSTICO SIN GEMINI: modelo falso, red bloqueada y archivos temporales.\n"
        "Las decisiones de esta prueba no autorizan ninguna entrega real.",
        flush=True,
    )
    respuestas = []
    for tecla in ("s", "n"):
        respuestas.extend([
            pedir_herramienta("obtener_articulo", numero="34"),
            pedir_herramienta(
                "entregar_informe",
                titulo=f"Diagnóstico simulado: escribe {tecla}",
                contenido=f"Prueba sin Gemini. Escribe {tecla} y pulsa Enter.",
            ),
            AIMessage(content="Fin del turno simulado."),
        ])
    with tempfile.TemporaryDirectory() as directorio, ExitStack() as contexto:
        raiz = Path(directorio)
        contexto.enter_context(patch.dict(os.environ, {
            "LANGSMITH_TRACING": "false",
            "LANGCHAIN_TRACING": "false",
            "LANGCHAIN_TRACING_V2": "false",
        }))
        contexto.enter_context(patch("src.orquestacion.supervision.RUTA_TRAZAS", raiz / "trazas"))
        contexto.enter_context(
            patch("src.orquestacion.supervision.RUTA_APROBACIONES", raiz / "aprobaciones")
        )
        contexto.enter_context(
            patch("src.orquestacion.herramientas.DIRECTORIO_INFORMES", raiz / "informes")
        )
        contexto.enter_context(
            patch.dict("src.orquestacion.agente_con_herramientas.historiales", clear=True)
        )
        # Conserva la lectura real de stdin y select; solo acorta la espera del diagnóstico.
        contexto.enter_context(patch(
            "src.orquestacion.herramientas.esperar_aprobacion",
            side_effect=lambda mensaje: esperar_aprobacion(mensaje, args.tiempo_limite),
        ))
        for ruta in (
            "socket.create_connection",
            "socket.socket.connect",
            "socket.socket.connect_ex",
            "socket.getaddrinfo",
        ):
            contexto.enter_context(patch(
                ruta, side_effect=AssertionError("El diagnóstico no permite conexiones de red.")
            ))
        agente = construir_agente_con_memoria(
            construir_ejecutor(crear_modelo_falso(respuestas), HERRAMIENTAS)
        )
        for tecla in ("s", "n"):
            resultado = consultar_agente(
                agente, f"Prueba de entrada {tecla}, sin Gemini.", f"diagnostico-{tecla}"
            )
            print(resultado["output"], flush=True)
        ruta = raiz / "aprobaciones"
        decisiones = [
            json.loads(linea)["aprobado"] for linea in ruta.read_text().splitlines()
        ]
        print(f"Decisiones simuladas: {json.dumps(decisiones)}", flush=True)
    print("Fin del diagnóstico; los archivos temporales se eliminaron.", flush=True)


if __name__ == "__main__":
    main()
