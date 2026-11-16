"""Aprobación humana, trazas y revisión de repeticiones del agente de Ley REP."""

import argparse
import getpass
import json
import logging
import select
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)
DIRECTORIO_SALIDA = Path(__file__).resolve().parents[2] / "output" / "agente"
RUTA_APROBACIONES = DIRECTORIO_SALIDA / "aprobaciones.jsonl"
RUTA_TRAZAS = DIRECTORIO_SALIDA / "trazas_agente.jsonl"


def _leer_aprobacion(mensaje: str, tiempo_limite_segundos: float) -> tuple[bool, str]:
    """Lee una decisión y su motivo sin confundir una n con EOF, silencio o error."""
    try:
        print(
            f"{mensaje}\n¿Aprobar esta entrega simulada? [s/N] "
            f"(límite: {tiempo_limite_segundos:g} s)\n"
            "Escribe s o n y pulsa Enter; no es un menú de selección.",
            file=sys.stderr,
            flush=True,
        )
        if tiempo_limite_segundos <= 0:
            return False, "límite no positivo"
        if not sys.stdin.isatty():
            return False, "entrada no interactiva"
        disponibles, _, _ = select.select([sys.stdin], [], [], tiempo_limite_segundos)
        if not disponibles:
            return False, "tiempo agotado sin respuesta"
        linea = sys.stdin.readline()
        if linea == "":
            return False, "fin de entrada (EOF)"
        respuesta = linea.strip().lower()
        if respuesta == "s":
            return True, "s recibida: aprobación explícita"
        if respuesta == "n":
            return False, "n recibida: rechazo explícito"
        if not respuesta:
            return False, "línea vacía recibida (Enter sin s ni n)"
        # No registrar el texto: el usuario podría haber pegado un dato privado por error.
        return False, "respuesta distinta de s o n"
    except KeyboardInterrupt:
        return False, "cancelación con Ctrl+C"
    except (OSError, ValueError) as error:
        return False, f"error de terminal ({type(error).__name__}: {error})"


def esperar_aprobacion(mensaje: str, tiempo_limite_segundos: float = 300) -> bool:
    """Aprueba solo con s y muestra por qué terminó la espera; cualquier fallo rechaza."""
    inicio = monotonic()
    aprobado, motivo = _leer_aprobacion(mensaje, tiempo_limite_segundos)
    # Visible también al invocarla sin configurar logging; no cambia el contrato booleano.
    try:
        print(
            f"Resultado de aprobación: {motivo}; espera: {monotonic() - inicio:.1f} s.",
            file=sys.stderr,
            flush=True,
        )
    except (OSError, ValueError):
        return False
    return aprobado


def _agregar_jsonl(ruta: Path, evento: dict[str, Any]) -> None:
    """Agrega un evento completo en UTF-8, sin sobrescribir los anteriores."""
    linea = json.dumps(evento, ensure_ascii=False) + "\n"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as archivo:
        archivo.write(linea)


def registrar_aprobacion(
    session_id: str, titulo: str, contenido: str, aprobado: bool, ruta: Path | None = None
) -> str:
    """Registra la decisión antes de actuar y devuelve su identificador."""
    identificador = uuid4().hex
    _agregar_jsonl(
        ruta if ruta is not None else RUTA_APROBACIONES,
        {
            "id_aprobacion": identificador,
            "fecha": datetime.now(UTC).isoformat(),
            "session_id": session_id,
            # Identifica la cuenta local, no autentica a una persona.
            "supervisor_local": getpass.getuser(),
            "herramienta": "entregar_informe",
            "titulo": titulo,
            "contenido": contenido,
            "aprobado": aprobado,
        },
    )
    return identificador


def registrar_traza(
    session_id: str,
    entrada: str,
    resultado: dict[str, Any],
    ruta: Path | None = None,
    *,
    mensajes_en_historial_antes: int = 0,
    error: dict[str, str] | None = None,
) -> None:
    """Registra una consulta con sus pasos y respuesta, incluso si el ejecutor falló."""
    _agregar_jsonl(
        ruta if ruta is not None else RUTA_TRAZAS,
        {
            "fecha": datetime.now(UTC).isoformat(),
            "session_id": session_id,
            "entrada": entrada,
            "mensajes_en_historial_antes": mensajes_en_historial_antes,
            "pasos": [
                {
                    "herramienta": accion.tool,
                    "argumentos": accion.tool_input,
                    "observacion": str(observacion),
                }
                for accion, observacion in resultado.get("intermediate_steps", [])
            ],
            "respuesta": resultado.get("output", ""),
            "error": error,
        },
    )


def marcar_repeticiones_sospechosas(ruta: Path | None = None) -> list[str]:
    """Devuelve las sesiones con dos usos consecutivos de la misma herramienta."""
    origen = ruta if ruta is not None else RUTA_TRAZAS
    if not origen.exists():
        logger.warning("No existe el archivo de trazas: %s", origen)
        return []
    anteriores: dict[str, str] = {}
    sospechosas: list[str] = []
    with origen.open(encoding="utf-8") as archivo:
        for numero, linea in enumerate(archivo, 1):
            traza = json.loads(linea)
            sesion = traza["session_id"]
            for paso in traza.get("pasos", []):
                herramienta = paso["herramienta"]
                if anteriores.get(sesion) == herramienta:
                    logger.warning(
                        "Repetición para revisar: sesión %s, herramienta %s, línea %s",
                        sesion,
                        herramienta,
                        numero,
                    )
                    if sesion not in sospechosas:
                        sospechosas.append(sesion)
                anteriores[sesion] = herramienta
    return sospechosas


def main() -> None:
    """Revisa trazas locales sin llamar al modelo ni repetir las acciones."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trazas", type=Path, default=RUTA_TRAZAS)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(marcar_repeticiones_sospechosas(args.trazas), ensure_ascii=False))


if __name__ == "__main__":
    main()
