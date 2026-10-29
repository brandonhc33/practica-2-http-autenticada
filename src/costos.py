"""Estimación por consulta con tarifas estándar de pago y conversión de USD a CLP."""

from decimal import Decimal

from .esquemas import CostoEstimado, CostosMoneda, TarifasTokens, TarifasTokensCLP, UsoTokens
from .tipo_cambio import obtener_tipo_cambio

# Tarifas estándar por 1.000.000 de tokens, verificadas el 2026-10-20.
# https://ai.google.dev/gemini-api/docs/pricing
# Son una referencia de pago: no permiten conocer la facturación de la cuenta.
# Flash 3.6 y 3.8 tienen precios promocionales hasta el 2026-12-31; el evaluador
# exige actualizarlos después de esa fecha antes de generar nuevas evidencias.
TARIFAS_GEMINI: dict[str, TarifasTokens] = {
    "gemini-3.5-flash-lite": TarifasTokens(
        entrada=Decimal("0.30"), entrada_cache=Decimal("0.03"), salida=Decimal("2.50")
    ),
    "gemini-3.8-flash": TarifasTokens(
        entrada=Decimal("0.75"), entrada_cache=Decimal("0.075"), salida=Decimal("3.75")
    ),
    "gemini-3.6-flash": TarifasTokens(
        entrada=Decimal("0.75"), entrada_cache=Decimal("0.075"), salida=Decimal("3.75")
    ),
}


def calcular_costo_usd_gemini(modelo: str, uso: UsoTokens | None) -> CostosMoneda | None:
    """Calcula únicamente USD; no consulta la red ni registra la operación."""
    tarifas = TARIFAS_GEMINI.get(modelo)
    if uso is None or tarifas is None:
        return None

    # La entrada ya contiene los tokens de caché; se cobran una sola vez.
    entrada = (
        (uso.entrada - uso.entrada_cache) * tarifas.entrada
        + uso.entrada_cache * tarifas.entrada_cache
    ) / Decimal(1_000_000)
    salida = uso.salida * tarifas.salida / Decimal(1_000_000)
    total = entrada + salida
    return CostosMoneda(moneda="USD", entrada=entrada, salida=salida, total=total)


def calcular_costo_gemini(modelo: str, uso: UsoTokens | None) -> CostoEstimado | None:
    usd = calcular_costo_usd_gemini(modelo, uso)
    if usd is None:
        return None
    tarifas = TARIFAS_GEMINI[modelo]
    tipo_cambio = None
    clp = None
    tarifas_clp = None
    aviso_clp = None
    try:
        tipo_cambio = obtener_tipo_cambio()
        tarifas_clp = TarifasTokensCLP(
            entrada=tarifas.entrada * tipo_cambio.clp_por_usd,
            entrada_cache=tarifas.entrada_cache * tipo_cambio.clp_por_usd,
            salida=tarifas.salida * tipo_cambio.clp_por_usd,
        )
        clp = CostosMoneda(
            moneda="CLP",
            entrada=usd.entrada * tipo_cambio.clp_por_usd,
            salida=usd.salida * tipo_cambio.clp_por_usd,
            total=usd.total * tipo_cambio.clp_por_usd,
        )
    except ValueError as error:
        # La falta de conversión no descarta una consulta ya completada por Gemini.
        aviso_clp = str(error)
    return CostoEstimado(
        modelo=modelo,
        usd=usd,
        clp=clp,
        tipo_cambio=tipo_cambio,
        tarifas_por_millon_usd=tarifas,
        tarifas_por_millon_clp=tarifas_clp,
        aviso_clp=aviso_clp,
    )
