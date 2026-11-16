"""Aprobación humana, trazas y revisión de repeticiones del agente de Ley REP."""

import argparse
import getpass
import json
import logging
import select
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)
DIRECTORIO_SALIDA = Path(__file__).resolve().parents[2] / "output" / "agente"
RUTA_APROBACIONES = DIRECTORIO_SALIDA / "aprobaciones.jsonl"
RUTA_TRAZAS = DIRECTORIO_SALIDA / "trazas_agente.jsonl"


def esperar_aprobacion(mensaje: str, tiempo_limite_segundos: float = 300) -> bool:
    """Aprueba solo con s en una terminal interactiva; cualquier fallo rechaza la acción."""
    try:
        print(
            f"{mensaje}\n¿Aprobar esta entrega simulada? [s/N] "
            f"(límite: {tiempo_limite_segundos:g} s)",
            file=sys.stderr,
            flush=True,
        )
        if tiempo_limite_segundos <= 0 or not sys.stdin.isatty():
            return False
        disponibles, _, _ = select.select([sys.stdin], [], [], tiempo_limite_segundos)
        return bool(disponibles) and sys.stdin.readline().strip().lower() == "s"
    except (OSError, ValueError, KeyboardInterrupt):
        return False


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
