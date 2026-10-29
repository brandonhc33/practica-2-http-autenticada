"""Política común de reintentos; una sola capa controla esperas e intentos."""

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from random import uniform
from time import monotonic, sleep

from .errores_cliente import (
    ErrorCliente,
    ErrorTemporalProveedor,
    ErrorTimeoutLectura,
    ReintentosAgotados,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PoliticaReintento:
    """Los intentos incluyen el primero; los timeouts se ajustan al tiempo restante.

    espera_maxima limita el backoff base; Retry-After y jitter pueden superarla.
    """

    intentos: int = 3
    espera_inicial: float = 1.0
    espera_maxima: float = 8.0
    jitter: float = 0.25
    presupuesto_segundos: float = 90.0
    timeout_conexion: float = 10.0
    timeout_lectura: float = 60.0
    reintentar_lectura: bool = False

    def __post_init__(self) -> None:
        if (
            isinstance(self.intentos, bool)
            or not isinstance(self.intentos, int)
            or self.intentos < 1
        ):
            raise ValueError("intentos debe ser un entero mayor o igual a 1.")
        for campo in ("espera_inicial", "espera_maxima", "jitter"):
            valor = getattr(self, campo)
            if isinstance(valor, bool) or not math.isfinite(valor) or valor < 0:
                raise ValueError(f"{campo} debe ser finito y mayor o igual a 0.")
        for campo in ("presupuesto_segundos", "timeout_conexion", "timeout_lectura"):
            valor = getattr(self, campo)
            if isinstance(valor, bool) or not math.isfinite(valor) or valor <= 0:
                raise ValueError(f"{campo} debe ser finito y mayor que 0.")
        if not isinstance(self.reintentar_lectura, bool):
            raise ValueError("reintentar_lectura debe ser un booleano.")

    def timeout(self, restante: float) -> tuple[float, float]:
        escala = min(1.0, restante / (self.timeout_conexion + self.timeout_lectura))
        return self.timeout_conexion * escala, self.timeout_lectura * escala


POLITICA_PREDETERMINADA = PoliticaReintento()
SIN_REINTENTOS = PoliticaReintento(intentos=1)


def parsear_retry_after(valor: object, *, ahora: datetime | None = None) -> float | None:
    """Acepta segundos enteros o fecha HTTP; un encabezado inválido usa el backoff."""
    if not isinstance(valor, str) or not valor.strip():
        return None
    valor = valor.strip()
    try:
        if valor.isascii() and valor.isdecimal():
            # Un entero enorme sigue siendo una espera válida: excederá el presupuesto,
            # en lugar de ignorarse y provocar otro intento antes de lo indicado.
            return float(valor)
        else:
            fecha = parsedate_to_datetime(valor)
            if fecha.tzinfo is None:
                fecha = fecha.replace(tzinfo=UTC)
            segundos = (fecha - (ahora or datetime.now(UTC))).total_seconds()
    except (ValueError, TypeError, OverflowError):
        return None
    return max(0.0, segundos) if math.isfinite(segundos) else None


def con_reintento[T](
    funcion: Callable[[float], T],
    politica: PoliticaReintento = POLITICA_PREDETERMINADA,
) -> T:
    """Ejecuta la operación pasándole su presupuesto restante, sin repetir errores permanentes."""
    inicio = monotonic()
    espera = min(politica.espera_inicial, politica.espera_maxima)
    ultimo_error: ErrorTemporalProveedor | None = None
    for intento in range(1, politica.intentos + 1):
        restante = politica.presupuesto_segundos - (monotonic() - inicio)
        if restante <= 0:
            raise ReintentosAgotados(intento - 1, ultimo_error, presupuesto_agotado=True) from None
        inicio_intento = monotonic()
        try:
            resultado = funcion(restante)
        except ErrorCliente as error:
            logger.info(
                "Intento %s/%s: %s, HTTP=%s, duración=%.3fs",
                intento,
                politica.intentos,
                type(error).__name__,
                error.codigo_http,
                monotonic() - inicio_intento,
            )
            if not isinstance(error, ErrorTemporalProveedor) or (
                isinstance(error, ErrorTimeoutLectura) and not politica.reintentar_lectura
            ):
                raise
            # Una medición sin reintentos conserva la categoría original del error.
            if politica.intentos == 1:
                raise
            restante = politica.presupuesto_segundos - (monotonic() - inicio)
            if intento == politica.intentos or restante <= 0:
                raise ReintentosAgotados(
                    intento, error, presupuesto_agotado=restante <= 0
                ) from None
            pausa_base = min(politica.espera_maxima, espera)
            if error.retry_after is not None:
                pausa_base = max(pausa_base, error.retry_after)
            pausa = pausa_base + uniform(0, politica.jitter)
            if pausa >= restante:
                # No se acorta Retry-After para forzar otro intento antes de tiempo.
                raise ReintentosAgotados(intento, error, presupuesto_agotado=True) from None
            logger.warning(
                "Intento %s/%s falló (%s, HTTP=%s); reintentando en %.3fs.",
                intento,
                politica.intentos,
                type(error).__name__,
                error.codigo_http,
                pausa,
            )
            sleep(pausa)
            espera = min(politica.espera_maxima, espera * 2)
            ultimo_error = error
        else:
            logger.info(
                "Intento %s/%s: completado, duración=%.3fs",
                intento,
                politica.intentos,
                monotonic() - inicio_intento,
            )
            return resultado
    raise AssertionError("La política debe permitir al menos un intento.")
