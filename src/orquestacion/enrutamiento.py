"""Clasificación y rutas del Bloque 19 para consultas de Ley REP."""

import re
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable, RunnableBranch, RunnablePassthrough

from src.evaluacion.texto import limpiar_texto
from src.orquestacion.cadena_tres_pasos import REGLAS_TEXTO
from src.prompts.contexto_ley_rep import obtener_fragmento_ley_rep

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
    )


def construir_cadena_aclaracion(modelo: Runnable) -> Runnable:
    """Arma la ruta por defecto: pide antecedentes y no recibe texto de la ley."""
    return plantilla_aclaracion | modelo | StrOutputParser()


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
