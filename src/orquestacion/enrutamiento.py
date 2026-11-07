"""Clasificación, rutas y manejo de errores de los bloques 19 y 20 para Ley REP."""

import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
)

from src.catalogo import AGENTES
from src.costos.registro import sesion_costos
from src.evaluacion.texto import limpiar_texto
from src.orquestacion.cadena_tres_pasos import REGLAS_TEXTO, construir_cadena
from src.orquestacion.modelo import crear_modelo, exigir_texto
from src.prompts.contexto_ley_rep import obtener_fragmento_ley_rep

logger = logging.getLogger(__name__)

TEXTO_RESPALDO = (
    "No pudimos responder tu consulta en este momento. Eso no significa que no existan "
    "obligaciones para tu caso: intenta de nuevo más tarde o revisa la Ley 20.920."
)
MENSAJE_SEGURO = (
    "No pudimos procesar tu consulta en este momento. Eso no significa que no existan "
    "obligaciones para tu caso: intenta de nuevo más tarde."
)
MENSAJE_VACIO = "Escribe una consulta sobre la Ley REP para poder ayudarte."

# Los grupos capturan el artículo, si dice "transitorio" y si enumera otro: "artículo 9 y 10".
PATRON_ARTICULO = re.compile(
    r"\bart(?:[ií]culo|\.)\s*(\d+|primero|segundo|tercero|cuarto)[º°]?"
    r"(\s+transitorio)?(\s*(?:,|y)\s*(?:el\s+)?\d)?",
    re.IGNORECASE,
)

plantilla_clasificacion = PromptTemplate.from_template(
    REGLAS_TEXTO + "\n\n"
    "Clasifica la consulta en una sola palabra: normativa, resumen o aclaracion. Usa normativa "
    "si pregunta qué dice la ley o qué obligaciones establece; resumen si pide resumir un "
    "artículo específico; aclaracion si no se entiende, no trata de la Ley REP o no permite "
    "saber qué se pide. Responde solo con esa palabra.\n\n"
    "<consulta>{mensaje}</consulta>"
)

plantilla_resumen = PromptTemplate.from_template(
    REGLAS_TEXTO + "\n\n"
    "Resume solo el fragmento en dos o tres oraciones, indicando su referencia. Agrega una línea "
    "final con lo que este fragmento no permite concluir. No completes el texto de memoria ni "
    "conviertas un objetivo general en una obligación concreta.\n\n"
    "<consulta>{mensaje}</consulta>\n"
    "<fragmento>{fragmento}</fragmento>"
)

plantilla_aclaracion = PromptTemplate.from_template(
    REGLAS_TEXTO + "\n\n"
    "No respondas la consulta ni afirmes nada sobre lo que dice la ley. Explica en una oración "
    "que faltan antecedentes para revisarla y haz hasta tres preguntas concretas para "
    "obtenerlos.\n\n"
    "<consulta>{mensaje}</consulta>"
)


def construir_paso_clasificacion(modelo: Runnable) -> Runnable:
    """Arma el paso que recibe {"mensaje": str} y devuelve la categoría normalizada."""
    return plantilla_clasificacion | modelo | StrOutputParser() | limpiar_texto


def buscar_fragmento(mensaje: str) -> dict[str, Any] | None:
    """Devuelve el único artículo nombrado en el mensaje, o None si no hay uno claro."""
    coincidencias = list(PATRON_ARTICULO.finditer(mensaje))
    if len(coincidencias) != 1:
        return None
    articulo, transitorio, otro_articulo = coincidencias[0].groups()
    # En la copia local los ordinales son transitorios: "artículo primero" podría ser el 1.
    if otro_articulo or articulo.isdigit() == bool(transitorio):
        return None
    try:
        return obtener_fragmento_ley_rep(articulo)
    except ValueError:
        return None


def construir_cadena_resumen(modelo: Runnable) -> Runnable:
    """Arma la ruta que resume el fragmento que encontró el enrutamiento."""
    return (
        RunnablePassthrough.assign(
            fragmento=lambda x: f"[{x['fragmento']['referencia']}]\n{x['fragmento']['texto']}"
        )
        | plantilla_resumen
        | modelo
        | StrOutputParser()
        | exigir_texto
    )


def construir_cadena_aclaracion(modelo: Runnable) -> Runnable:
    """Arma la ruta por defecto: pide antecedentes y no recibe texto de la ley."""
    return plantilla_aclaracion | modelo | StrOutputParser() | exigir_texto


def construir_cadena_con_enrutamiento(
    paso_clasificacion: Runnable,
    cadena_normativa: Runnable | None = None,
    cadena_resumen: Runnable | None = None,
    cadena_aclaracion: Runnable | None = None,
) -> Runnable:
    """Clasifica la consulta y ejecuta solo la ruta que le corresponde."""
    cadena_normativa = cadena_normativa or RunnablePassthrough()
    cadena_resumen = cadena_resumen or RunnablePassthrough()
    cadena_aclaracion = cadena_aclaracion or RunnablePassthrough()
    bifurcacion = RunnableBranch(
        (lambda x: x["categoria"] == "normativa", cadena_normativa),
        (lambda x: x["categoria"] == "resumen" and x["fragmento"] is not None, cadena_resumen),
        cadena_aclaracion,
    )
    return (
        RunnablePassthrough.assign(
            categoria=paso_clasificacion,
            fragmento=lambda x: buscar_fragmento(x["mensaje"]),
        )
        | bifurcacion
    )


def registrar_error(entrada: dict[str, Any]) -> dict[str, Any]:
    """Registra el tipo y el mensaje del error; la traza solo aparece en nivel DEBUG."""
    error = entrada["error"]
    logger.error("Falló el flujo (%s): %s", type(error).__name__, error)
    logger.debug("Traza del error", exc_info=error)
    return entrada


def construir_ruta_segura(ruta: Runnable, alternativa: Runnable | None = None) -> Runnable:
    """Protege una ruta: primero la alternativa, si existe, y después el texto de respaldo."""
    respaldo = RunnableLambda(registrar_error) | (lambda _: TEXTO_RESPALDO)
    alternativas = [respaldo]
    if alternativa is not None:
        # exception_key solo entrega el último error: el del principal se registra aquí.
        alternativas.insert(0, RunnableLambda(registrar_error) | alternativa)
    return ruta.with_fallbacks(alternativas, exception_key="error")


def procesar_consulta_segura(cadena: Runnable, mensaje: str) -> str:
    """Ejecuta el flujo completo y devuelve siempre un texto, sin propagar excepciones."""
    if not mensaje.strip():
        return MENSAJE_VACIO
    try:
        return cadena.invoke({"mensaje": mensaje})
    except Exception as error:
        registrar_error({"error": error})
        return MENSAJE_SEGURO


def main() -> None:
    """Responde una consulta por terminal y muestra el consumo en stderr."""
    parser = argparse.ArgumentParser(description="Responde una consulta de Ley REP.")
    parser.add_argument("consulta", help="Consulta sobre la Ley REP.")
    consulta = parser.parse_args().consulta
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    clave = AGENTES["gemini"]["clave"]
    if not os.getenv(clave, "").strip():
        sys.exit(f"Falta configurar {clave} en el archivo .env.")
    logging.basicConfig(level=logging.INFO)
    principal, secundario = crear_modelo(), crear_modelo("flash")
    cadena = construir_cadena_con_enrutamiento(
        construir_paso_clasificacion(principal),
        construir_ruta_segura(construir_cadena(principal), construir_cadena(secundario)),
        construir_ruta_segura(
            construir_cadena_resumen(principal), construir_cadena_resumen(secundario)
        ),
        construir_ruta_segura(
            construir_cadena_aclaracion(principal), construir_cadena_aclaracion(secundario)
        ),
    )
    with sesion_costos() as registro:
        print(procesar_consulta_segura(cadena, consulta))
    print(registro.resumen().como_dict(), file=sys.stderr)


if __name__ == "__main__":
    main()
