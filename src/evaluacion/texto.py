"""Pipeline de los bloques 15–16: no mide significado ni veracidad."""

import re
from collections import Counter
from statistics import mean


def limpiar_texto(texto: str) -> str:
    """Normaliza formato; conserva letras españolas, números y negaciones."""
    if not isinstance(texto, str):
        raise TypeError("Se esperaba texto (str).")
    # Sustituir por espacio evita fusionar palabras como reciclaje/reutilización.
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", texto.lower())).strip()


def tokenizar(texto_limpio: str) -> list[str]:
    return texto_limpio.split()


def procesar_texto(texto: str) -> list[str]:
    return tokenizar(limpiar_texto(texto))


def vectorizar(tokens: list[str]) -> Counter[str]:
    return Counter(tokens)


def contar_coincidencias(referencia: list[str], respuesta: list[str]) -> int:
    return sum((vectorizar(referencia) & vectorizar(respuesta)).values())


def calcular_precision_cobertura_f1(
    referencia: list[str], respuesta: list[str]
) -> dict[str, float]:
    if not referencia or not respuesta:
        return {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}
    coincidencias = contar_coincidencias(referencia, respuesta)
    precision = coincidencias / len(respuesta)
    cobertura = coincidencias / len(referencia)
    f1 = 2 * precision * cobertura / (precision + cobertura) if coincidencias else 0.0
    return {"precision": precision, "cobertura": cobertura, "f1": f1}


def calcular_metricas(referencia: str, respuesta: str) -> dict[str, float]:
    return calcular_precision_cobertura_f1(procesar_texto(referencia), procesar_texto(respuesta))


def coincidencia_simple(referencia: list[str], respuesta: list[str]) -> float:
    """Cobertura por palabras únicas usada en el bloque 15."""
    return len(set(referencia) & set(respuesta)) / len(set(referencia)) if referencia else 0.0


def comparar_antes_despues(referencia: str, respuesta: str) -> dict[str, float]:
    return {
        "crudo": coincidencia_simple(referencia.split(), respuesta.split()),
        "procesado": coincidencia_simple(procesar_texto(referencia), procesar_texto(respuesta)),
    }


def resumir_metricas(resultados: list[dict[str, float]]) -> dict[str, float]:
    return {
        f"{campo}_promedio": mean(r[campo] for r in resultados) if resultados else 0.0
        for campo in ("precision", "cobertura", "f1")
    }
