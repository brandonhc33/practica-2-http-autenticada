"""Consumo conocido por sesión, independiente del formato de salida del cliente."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from threading import Lock

from .esquemas import CostosMoneda, UsoTokens, decimal_fijo

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResumenCostosSesion:
    respuestas_con_costo: int = 0
    respuestas_sin_costo: int = 0
    consultas_fallidas: int = 0
    intentos_http: int = 0
    intentos_sin_uso: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    tokens_total: int = 0
    costo_conocido_usd: Decimal = Decimal("0")

    def como_dict(self) -> dict[str, int | str]:
        """Serializa el importe sin redondear ni convertirlo en un float."""
        return {**asdict(self), "costo_conocido_usd": decimal_fijo(self.costo_conocido_usd)}


class RegistroCostosSesion:
    """Acumula una vez por consulta; el bloqueo protege el uso entre hilos."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._resumen = ResumenCostosSesion()

    def resumen(self) -> ResumenCostosSesion:
        with self._lock:
            return self._resumen

    def registrar_respuesta(
        self, uso: UsoTokens | None, costo: CostosMoneda | None, *, intentos: int
    ) -> None:
        with self._lock:
            previo = self._resumen
            self._resumen = replace(
                previo,
                respuestas_con_costo=previo.respuestas_con_costo + (costo is not None),
                respuestas_sin_costo=previo.respuestas_sin_costo + (costo is None),
                intentos_http=previo.intentos_http + intentos,
                intentos_sin_uso=previo.intentos_sin_uso + intentos - (uso is not None),
                tokens_entrada=previo.tokens_entrada + (uso.entrada if uso else 0),
                tokens_salida=previo.tokens_salida + (uso.salida if uso else 0),
                tokens_total=previo.tokens_total + (uso.total if uso else 0),
                costo_conocido_usd=previo.costo_conocido_usd
                + (costo.total if costo is not None else Decimal("0")),
            )
            acumulado = self._resumen.costo_conocido_usd
        logger.info(
            "Operación: tokens=%s, costo_usd=%s, acumulado_usd=%s, intentos=%s",
            uso.total if uso is not None else "desconocidos",
            decimal_fijo(costo.total) if costo is not None else "desconocido",
            decimal_fijo(acumulado),
            intentos,
        )

    def registrar_fallo(self, *, intentos: int) -> None:
        with self._lock:
            previo = self._resumen
            self._resumen = replace(
                previo,
                consultas_fallidas=previo.consultas_fallidas + 1,
                intentos_http=previo.intentos_http + intentos,
                intentos_sin_uso=previo.intentos_sin_uso + intentos,
            )


# El total predeterminado dura lo que dura este proceso. Una sesión explícita
# permite separar ensayos y usuarios sin añadir parámetros a API, CLI o agentes.
_REGISTRO_PROCESO = RegistroCostosSesion()
_REGISTRO_ACTUAL: ContextVar[RegistroCostosSesion] = ContextVar(
    "registro_costos_actual", default=_REGISTRO_PROCESO
)


def obtener_registro_costos() -> RegistroCostosSesion:
    return _REGISTRO_ACTUAL.get()


@contextmanager
def sesion_costos() -> Iterator[RegistroCostosSesion]:
    """Las llamadas dentro del contexto comparten un total nuevo y aislado."""
    registro = RegistroCostosSesion()
    token = _REGISTRO_ACTUAL.set(registro)
    try:
        yield registro
    finally:
        _REGISTRO_ACTUAL.reset(token)
