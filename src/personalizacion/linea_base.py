"""Línea base del bloque 30: cómo clasifica hoy el flujo, antes de pensar en entrenar.

Mide el clasificador real del bloque 19 (prompt sin entrenamiento) y la regla local
que detecta el artículo. Separa los errores del modelo de los errores de la regla:
solo los primeros podrían corregirse entrenando un modelo.
"""

import hashlib
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser

from src.evaluacion.texto import limpiar_texto
from src.orquestacion.enrutamiento import buscar_fragmento, plantilla_clasificacion
from src.personalizacion.dataset import RUTAS
from src.rag.registro import consumo_generacion

# Criterio del bloque 30 para la pregunta de formato o tono: 3 de 20 respuestas (15 %).
MUESTRA_MINIMA = 20
UMBRAL_INCUMPLIMIENTO = 0.15


def ruta_efectiva(categoria: str, hay_articulo: bool) -> str:
    """Repite la bifurcación del bloque 19: resumen sin artículo único termina en aclaración."""
    if categoria == "normativa":
        return "normativa"
    if categoria == "resumen" and hay_articulo:
        return "resumen"
    return "aclaracion"


def categorias_que_llegan(ruta_esperada: str, hay_articulo: bool) -> list[str]:
    """Palabras del modelo con las que el flujo llegaría a la ruta etiquetada."""
    return [c for c in RUTAS if ruta_efectiva(c, hay_articulo) == ruta_esperada]


def categorias_aceptables(ejemplo: dict[str, Any]) -> list[str]:
    """Lo que debe responder el modelo: la ruta etiquetada, salvo excepción escrita.

    No se deduce del flujo: «resumen» sin artículo termina en aclaración, así que
    obedecer una consulta que intenta cambiar las instrucciones pasaría por acierto.
    """
    return ejemplo.get("categorias_modelo", [ejemplo["salida"]["ruta"]])


def detectar_articulo(consulta: str) -> str | None:
    fragmento = buscar_fragmento(consulta)
    return None if fragmento is None else fragmento["referencia"]


def evaluar_regla_articulos(dataset: dict[str, Any]) -> dict[str, Any]:
    """Compara la regla local con las etiquetas, sin Gemini y sin costo."""
    casos = []
    for ejemplo in dataset["ejemplos"]:
        detectado = detectar_articulo(ejemplo["consulta"])
        esperado = ejemplo["salida"]["articulo"]
        llegan = categorias_que_llegan(ejemplo["salida"]["ruta"], detectado is not None)
        casos.append(
            {
                "id": ejemplo["id"],
                "articulo_esperado": esperado,
                "articulo_detectado": detectado,
                "articulo_correcto": detectado == esperado,
                # Lista vacía: ninguna respuesta del modelo llevaría a la ruta etiquetada.
                "ruta_alcanzable": bool(llegan),
            }
        )
    return {
        "casos": casos,
        "articulos_correctos": sum(c["articulo_correcto"] for c in casos),
        "rutas_inalcanzables": [c["id"] for c in casos if not c["ruta_alcanzable"]],
        "total": len(casos),
    }


def huella_prompt() -> str:
    return hashlib.sha256(plantilla_clasificacion.template.encode("utf-8")).hexdigest()


def medir_linea_base(
    dataset: dict[str, Any],
    modelo: BaseChatModel,
    nombre_modelo: str,
    *,
    previos: list[dict[str, Any]] | None = None,
    pausa_segundos: float = 0,
    dormir: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Una respuesta por consulta; se detiene en el primer error.

    Con `previos` conserva las respuestas de un tramo interrumpido y solo consulta las que
    faltan: repetir todo permitiría elegir entre dos corridas.
    """
    registros: list[dict[str, Any]] = list(previos or [])
    respondidas = {r["id"] for r in registros}
    pendientes = [e for e in dataset["ejemplos"] if e["id"] not in respondidas]
    error: dict[str, str] | None = None
    for numero, ejemplo in enumerate(pendientes):
        if numero and pausa_segundos:
            dormir(pausa_segundos)
        consulta = ejemplo["consulta"]
        esperado = ejemplo["salida"]
        try:
            mensaje = modelo.invoke(plantilla_clasificacion.invoke({"mensaje": consulta}))
        except Exception as fallo:  # El proveedor puede fallar de muchas formas; se registra.
            error = {"id": ejemplo["id"], "tipo_error": type(fallo).__name__}
            break
        cruda = StrOutputParser().invoke(mensaje)
        normalizada = limpiar_texto(cruda)
        detectado = detectar_articulo(consulta)
        # No depende del artículo detectado: un fallo de la regla local no es del modelo.
        aceptables = categorias_aceptables(ejemplo)
        utilizable = normalizada in RUTAS
        coherente = utilizable and normalizada in aceptables
        ruta = ruta_efectiva(normalizada, detectado is not None)
        consumo = (
            consumo_generacion(mensaje, nombre_modelo)
            if isinstance(mensaje, AIMessage)
            else {"tokens": None, "costo_generacion_usd": None}
        )
        registros.append(
            {
                "id": ejemplo["id"],
                "consulta": consulta,
                "esperado": esperado,
                "salida_cruda": cruda,
                "categoria_normalizada": normalizada,
                "formato_estricto": cruda.strip() in RUTAS,
                "formato_utilizable": utilizable,
                "categorias_aceptables": aceptables,
                "coincidencia_exacta": normalizada == esperado["ruta"],
                "modelo_coherente": coherente,
                "articulo_detectado": detectado,
                "ruta_efectiva": ruta,
                "ruta_correcta": ruta == esperado["ruta"],
                "articulo_correcto": detectado == esperado["articulo"],
                "origen_discrepancia": origen_discrepancia(ruta == esperado["ruta"], coherente),
                "tokens": consumo["tokens"],
                "costo_usd": consumo["costo_generacion_usd"],
            }
        )
    return {"registros": registros, "error": error, "resumen": resumir(registros, error)}


def origen_discrepancia(ruta_correcta: bool, modelo_coherente: bool) -> str | None:
    """Si el modelo respondió lo esperado y aun así falló la ruta, la causa es la regla local."""
    if ruta_correcta:
        return None
    return "regla_local" if modelo_coherente else "modelo"


def resumir(registros: list[dict[str, Any]], error: dict[str, str] | None) -> dict[str, Any]:
    incumplimientos = [r["id"] for r in registros if not r["modelo_coherente"]]
    muestra = len(registros)
    proporcion = len(incumplimientos) / muestra if muestra else None
    completa = error is None and muestra >= MUESTRA_MINIMA
    return {
        "respuestas": len(registros),
        "formato_estricto": sum(r["formato_estricto"] for r in registros),
        "formato_utilizable": sum(r["formato_utilizable"] for r in registros),
        "coincidencias_exactas": sum(r["coincidencia_exacta"] for r in registros),
        "modelo_coherente": sum(r["modelo_coherente"] for r in registros),
        "rutas_correctas": sum(r["ruta_correcta"] for r in registros),
        "articulos_correctos": sum(r["articulo_correcto"] for r in registros),
        "discrepancias_modelo": [
            r["id"] for r in registros if r["origen_discrepancia"] == "modelo"
        ],
        "discrepancias_regla_local": [
            r["id"] for r in registros if r["origen_discrepancia"] == "regla_local"
        ],
        "muestra_modelo": muestra,
        "incumplimientos_modelo": incumplimientos,
        "proporcion_incumplimiento": proporcion,
        "umbral": UMBRAL_INCUMPLIMIENTO,
        "muestra_minima": MUESTRA_MINIMA,
        "completa": completa,
        # None significa "no medido", no "sin problemas": la decisión no puede inventarlo.
        "supera_umbral": (
            proporcion >= UMBRAL_INCUMPLIMIENTO if completa and proporcion is not None else None
        ),
    }


def ahora_utc() -> str:
    return datetime.now(UTC).isoformat()
