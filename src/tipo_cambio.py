"""Dólar observado para convertir la estimación de USD a pesos chilenos."""

import os
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from time import monotonic

import requests
from pydantic import ValidationError

from .esquemas import TipoCambio

ENDPOINT_DOLAR = "https://indicadores.cl/api/v1/dolar.json"
CACHE_SEGUNDOS = 3_600


@lru_cache(maxsize=1)
def consultar_dolar(_intervalo: int) -> TipoCambio:
    """Reutiliza la tasa durante un máximo de una hora dentro del proceso."""
    try:
        # Esta petición pública no recibe claves ni el mensaje enviado a Gemini.
        with requests.get(ENDPOINT_DOLAR, timeout=(3, 5), allow_redirects=False) as respuesta:
            if respuesta.status_code != 200:
                raise ValueError("Respuesta HTTP no válida.")
            datos = respuesta.json(parse_float=Decimal)
        if not isinstance(datos, dict) or datos.get("indicador") != "dolar":
            raise ValueError("Indicador no válido.")
        if not isinstance(datos.get("fecha"), str):
            raise ValueError("Falta la fecha del tipo de cambio.")
        return TipoCambio.model_validate(
            {
                "clp_por_usd": datos.get("valor"),
                "fecha": datos.get("fecha"),
                "fuente": ENDPOINT_DOLAR,
            }
        )
    except (requests.exceptions.RequestException, ValueError):
        raise ValueError(
            "No se pudo obtener el dólar observado. Configura USD_CLP en .env "
            "para calcular el costo en pesos chilenos."
        ) from None


def obtener_tipo_cambio() -> TipoCambio:
    tasa_configurada = os.getenv("USD_CLP", "").strip()
    if tasa_configurada:
        try:
            return TipoCambio(
                clp_por_usd=Decimal(tasa_configurada), fecha=None, fuente="USD_CLP (.env)"
            )
        except (InvalidOperation, ValidationError):
            raise ValueError("USD_CLP debe ser un número decimal positivo y finito.") from None
    return consultar_dolar(int(monotonic() // CACHE_SEGUNDOS))
