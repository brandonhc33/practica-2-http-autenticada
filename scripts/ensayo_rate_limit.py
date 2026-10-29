"""Ensayo acotado de 429 con el mismo cliente: simulado o contra Gemini real."""

import argparse
import json
import logging
import math
import os
from contextlib import ExitStack
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import monotonic
from typing import Any
from unittest.mock import MagicMock, patch

from dotenv import load_dotenv

from src.agente_gemini import consultar_gemini_raw
from src.catalogo import AGENTES
from src.errores_cliente import ErrorCliente, ErrorTemporalProveedor, ReintentosAgotados
from src.esquemas import decimal_fijo
from src.registro_costos import sesion_costos
from src.reintentos import POLITICA_PREDETERMINADA, PoliticaReintento

RAIZ = Path(__file__).resolve().parent.parent


def ahora() -> str:
    return datetime.now(UTC).isoformat()


class CapturaEnsayo(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.consulta_actual = 0
        self.primer_429: dict[str, Any] | None = None
        self.eventos: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        mensaje = record.getMessage()
        evento = {
            "fecha": ahora(),
            "consulta": self.consulta_actual,
            "nivel": record.levelname,
            "mensaje": mensaje,
        }
        self.eventos.append(evento)
        if "HTTP=429" in mensaje and self.primer_429 is None:
            self.primer_429 = evento.copy()
        print(f"{record.levelname}: {mensaje}", flush=True)


def configurar_simulacion(contextos: ExitStack) -> None:
    codigos = iter((200, 429, 503, 200))

    def post_simulado(*args: object, **kwargs: object) -> MagicMock:
        respuesta = MagicMock(status_code=next(codigos, 200), headers={})
        respuesta.__enter__.return_value = respuesta
        respuesta.json.return_value = {
            "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1_000, "completion_tokens": 2_000, "total_tokens": 3_000},
        }
        return respuesta

    reloj = [0.0]

    def esperar(segundos: float) -> None:
        reloj[0] += segundos

    contextos.enter_context(patch.dict(os.environ, {"GEMINI_API_KEY": "clave-simulada"}))
    contextos.enter_context(patch("src.agente_gemini.requests.post", side_effect=post_simulado))
    contextos.enter_context(patch("src.reintentos.monotonic", side_effect=lambda: reloj[0]))
    contextos.enter_context(patch("src.reintentos.sleep", side_effect=esperar))
    contextos.enter_context(patch("src.reintentos.uniform", return_value=0.125))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument("--simulado", action="store_true", help="Sin red, tokens ni esperas reales.")
    modo.add_argument("--real", action="store_true", help="Consultas reales, con cuota y consumo.")
    parser.add_argument(
        "--modelo", choices=tuple(AGENTES["gemini"]["modelos"]), default="flash-lite"
    )
    parser.add_argument(
        "--consultas", type=int, default=20, help="Máximo de consultas; entre 1 y 40."
    )
    parser.add_argument(
        "--max-envios", type=int, default=30, help="Incluye los reintentos; máximo 60."
    )
    parser.add_argument(
        "--presupuesto-total", type=float, default=120, help="Segundos; máximo 300."
    )
    parser.add_argument("--max-costo-conocido-usd", default="0.01")
    parser.add_argument(
        "--salida", type=Path, required=True, help="JSON nuevo; no sobrescribe evidencia."
    )
    args = parser.parse_args()
    if not 1 <= args.consultas <= 40 or not 1 <= args.max_envios <= 60:
        parser.error("consultas debe estar entre 1 y 40 y max-envios entre 1 y 60.")
    if not math.isfinite(args.presupuesto_total) or not 0 < args.presupuesto_total <= 300:
        parser.error("presupuesto-total debe ser finito, mayor que 0 y hasta 300 segundos.")
    try:
        limite_costo = Decimal(args.max_costo_conocido_usd)
    except InvalidOperation:
        parser.error("max-costo-conocido-usd debe ser un decimal positivo.")
    if not limite_costo.is_finite() or limite_costo <= 0:
        parser.error("max-costo-conocido-usd debe ser un decimal finito y positivo.")
    if args.salida.exists():
        parser.error("La salida ya existe. Usa otra ruta para conservar la evidencia.")
    if args.real:
        load_dotenv(RAIZ / ".env")
        if not os.getenv("GEMINI_API_KEY", "").strip():
            parser.error("Falta configurar GEMINI_API_KEY en .env.")

    captura = CapturaEnsayo()
    nombre_modo = "real" if args.real else "simulado"
    modelo = AGENTES["gemini"]["modelos"][args.modelo]
    evidencia: dict[str, Any] = {
        "modo": nombre_modo,
        "modelo": modelo,
        "inicio": ahora(),
        "limites": {
            "consultas": args.consultas,
            "envios_http": args.max_envios,
            "presupuesto_segundos": args.presupuesto_total,
            "costo_conocido_usd": str(limite_costo),
        },
        "nota_costo": (
            "Estimación con tarifas de pago; no acredita facturación. "
            "Los intentos sin uso reportado conservan consumo desconocido. "
            "El umbral de costo conocido se comprueba entre consultas, no es un tope de facturación."
        ),
        "consultas": [],
        "eventos": captura.eventos,
    }
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    # La creación exclusiva protege evidencias anteriores incluso si otra ejecución
    # creó el mismo archivo después de la comprobación inicial.
    with args.salida.open("x", encoding="utf-8") as archivo:
        json.dump(evidencia, archivo, ensure_ascii=False, indent=2)

    def guardar() -> None:
        temporal = args.salida.with_suffix(args.salida.suffix + ".tmp")
        temporal.write_text(json.dumps(evidencia, ensure_ascii=False, indent=2) + "\n")
        temporal.replace(args.salida)

    print(f"ENSAYO {nombre_modo.upper()} | modelo={modelo}", flush=True)
    print(
        f"Límites: {args.consultas} consultas, {args.max_envios} envíos HTTP, "
        f"{args.presupuesto_total:g}s, umbral de costo conocido US$ {limite_costo}",
        flush=True,
    )
    inicio = monotonic()
    motivo = "maximo_de_consultas"
    interrumpido = False
    with ExitStack() as contextos:
        if args.simulado:
            configurar_simulacion(contextos)
        for nombre in ("src.reintentos", "src.registro_costos"):
            logger = logging.getLogger(nombre)
            anteriores = logger.handlers[:], logger.level, logger.propagate

            def restaurar(logger=logger, anteriores=anteriores):
                logger.handlers, logger.level, logger.propagate = anteriores

            contextos.callback(restaurar)
            logger.handlers = [captura]
            logger.setLevel(logging.INFO)
            logger.propagate = False
        registro = contextos.enter_context(sesion_costos())
        try:
            for numero in range(1, args.consultas + 1):
                resumen = registro.resumen()
                restante = args.presupuesto_total - (monotonic() - inicio)
                envios_disponibles = args.max_envios - resumen.intentos_http
                if restante <= 0:
                    motivo = "presupuesto_total"
                    break
                if envios_disponibles <= 0:
                    motivo = "maximo_de_envios"
                    break
                if resumen.costo_conocido_usd >= limite_costo:
                    motivo = "umbral_costo_conocido"
                    break
                captura.consulta_actual = numero
                consulta: dict[str, Any] = {"numero": numero, "inicio": ahora()}
                evidencia["consultas"].append(consulta)
                politica = PoliticaReintento(
                    intentos=min(POLITICA_PREDETERMINADA.intentos, envios_disponibles),
                    presupuesto_segundos=min(
                        POLITICA_PREDETERMINADA.presupuesto_segundos, restante
                    ),
                )
                error_permanente = False
                try:
                    datos = consultar_gemini_raw(
                        modelo, f"Prueba {numero}. Responde únicamente OK.", politica=politica
                    )
                    consulta.update(estado="completada", respuesta_original=datos)
                except ErrorCliente as error:
                    consulta.update(
                        estado="fallida", tipo_error=type(error).__name__, error=str(error)
                    )
                    error_permanente = not isinstance(
                        error, ErrorTemporalProveedor | ReintentosAgotados
                    )
                finally:
                    consulta["fin"] = ahora()
                    consulta["resumen_sesion"] = registro.resumen().como_dict()
                    evidencia["primer_429"] = captura.primer_429
                    guardar()
                print(
                    f"Consulta {numero}: {consulta['estado']}; "
                    f"costo conocido acumulado US$ {decimal_fijo(registro.resumen().costo_conocido_usd)}",
                    flush=True,
                )
                if captura.primer_429 is not None:
                    motivo = "primer_429_observado"
                    break
                if error_permanente:
                    motivo = "error_no_reintentable"
                    break
        except KeyboardInterrupt:
            interrumpido = True
            motivo = "interrumpido"
            if evidencia["consultas"]:
                evidencia["consultas"][-1]["estado"] = "interrumpida"
        finally:
            evidencia.update(
                fin=ahora(),
                motivo_fin=motivo,
                primer_429=captura.primer_429,
                resumen=registro.resumen().como_dict(),
                duracion_segundos=round(monotonic() - inicio, 3),
            )
            guardar()
    print(f"Resultado: {motivo}", flush=True)
    print(json.dumps(evidencia["resumen"], ensure_ascii=False, indent=2), flush=True)
    print(f"Evidencia: {args.salida}", flush=True)
    return 130 if interrumpido else (0 if captura.primer_429 is not None else 1)


if __name__ == "__main__":
    raise SystemExit(main())
