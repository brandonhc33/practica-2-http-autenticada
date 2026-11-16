"""Herramientas del agente de Ley REP: buscar por tema y leer un artículo de la copia local."""

import re
import unicodedata
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field, ValidationError
from pydantic.v1 import ValidationError as ValidationErrorV1

from src.evaluacion.texto import limpiar_texto
from src.prompts.contexto_ley_rep import (
    TRANSITORIOS,
    cargar_documento_ley_rep,
    obtener_fragmento_ley_rep,
)

MAXIMO_ARTICULOS = 3
LIMITE_CARACTERES = 1_500
# Palabras sin tema propio. "ley", "rep" y "artículo" aparecen en casi cualquier consulta, y
# los números de artículo los resuelve obtener_articulo: así las dos herramientas no compiten.
PALABRAS_VACIAS = frozenset(
    "al ante como con cual cuales cuando de del donde el ella ellas ellos en entre es esa ese esta "
    "este esto estos estas ha han hay la las le les lo los mas me mi muy no nos para pero por que "
    "quien quienes se segun ser si sin sobre son su sus tu un una uno unos unas debe deben dice "
    "dicen establece establecen habla hacer indica menciona puede pueden senala tiene tienen trata "
    "ley rep articulo articulos art".split()
)
# "Artículo 12º.- Metas de recolección y valorización." -> el título llega hasta el primer punto.
PATRON_TITULO = re.compile(r"Art[ií]culo [^.]*?\.-\s*([^.]*)")
# {"primero": "1", ..., "cuarto": "4"}: el ordinal solo indica un transitorio si transitorio=true.
POSICION_DEL_ORDINAL = {ordinal: str(i) for i, ordinal in enumerate(TRANSITORIOS, 1)}


def _raiz(palabra: str) -> str:
    """Quita el plural simple para que "gestores" coincida con "gestor" y "metas" con "meta"."""
    if len(palabra) > 4 and palabra.endswith("es") and palabra[-3] in "rlndz":
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def extraer_palabras(texto: str) -> set[str]:
    """Normaliza el texto y deja las palabras con tema, sin tildes, números ni plurales."""
    descompuesto = unicodedata.normalize("NFD", limpiar_texto(texto))
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return {
        _raiz(palabra)
        for palabra in sin_tildes.split()
        # "12º" no pasa isdigit(): se descarta toda palabra con un dígito.
        if len(palabra) > 2 and not re.search(r"\d", palabra) and palabra not in PALABRAS_VACIAS
    }


def _puntuar(palabras: set[str], fragmento: dict[str, Any]) -> int:
    """Cuenta las palabras de la consulta en el artículo; las del título valen el triple."""
    titulo = PATRON_TITULO.match(fragmento["texto"])
    en_titulo = palabras & extraer_palabras(titulo[1]) if titulo else set()
    # El título también es parte del texto: cada palabra suya suma 2 aquí y 1 abajo.
    return 2 * len(en_titulo) + len(palabras & extraer_palabras(fragmento["texto"]))


def _recortar(fragmento: dict[str, Any]) -> str:
    """Da el artículo con su referencia y, si es largo, avisa cómo leerlo completo."""
    texto = fragmento["texto"]
    if len(texto) <= LIMITE_CARACTERES:
        return f"[{fragmento['referencia']}]\n{texto}"
    # "ley20920-articulo-20" -> "20"; "ley20920-transitorio-primero" -> "primero".
    _, tipo, numero = fragmento["id_fragmento"].split("-")
    argumentos = f'numero="{numero}"' + (", transitorio=true" if tipo == "transitorio" else "")
    return (
        f"[{fragmento['referencia']}]\n{texto[:LIMITE_CARACTERES]}…\n"
        f"(Recortado: se muestran {LIMITE_CARACTERES} de {len(texto)} caracteres. "
        f"Para leerlo completo, usa obtener_articulo con {argumentos}.)"
    )


@tool
def buscar_en_ley(consulta: str) -> str:
    """Busca en la Ley REP (Ley 20.920) los artículos que tratan un tema y devuelve hasta tres.
    Usar cuando la consulta pregunta qué dice la ley sobre un tema, como metas, sanciones,
    gestores u obligaciones de un actor, y no nombra un artículo específico."""
    palabras = extraer_palabras(consulta)
    if not palabras:
        return (
            "La búsqueda necesita un tema, como 'metas de recolección' o 'sanciones'. "
            "Para leer un artículo por su número, usa obtener_articulo."
        )
    try:
        fragmentos = cargar_documento_ley_rep()["fragmentos"]
    except ValueError as error:
        return f"No pude buscar en la ley: {error}"
    puntajes = [(_puntuar(palabras, fragmento), fragmento) for fragmento in fragmentos]
    # sorted es estable: ante un empate queda primero el artículo que aparece antes en la ley.
    encontrados = sorted((p for p in puntajes if p[0] > 0), key=lambda p: -p[0])
    if not encontrados:
        return (
            f"No encontré artículos sobre '{consulta}' en la copia local de la Ley 20.920. "
            "Prueba con otras palabras; que no aparezcan no significa que no existan obligaciones."
        )
    return "\n\n".join(_recortar(f) for _, f in encontrados[:MAXIMO_ARTICULOS])


class ArgumentosArticulo(BaseModel):
    """Argumentos de obtener_articulo, cada uno con la descripción que lee el modelo."""

    numero: str = Field(
        description=(
            'Solo el número del artículo, como "12". Para un transitorio, su número ("1") '
            'o su ordinal ("primero"), del primero al cuarto.'
        )
    )
    transitorio: bool = Field(
        default=False,
        description=(
            'true solo si la consulta pide un artículo transitorio, como "artículo primero '
            'transitorio". Sin él, "primero" se lee como el artículo 1.'
        ),
    )


def explicar_argumentos_invalidos(error: ValidationError | ValidationErrorV1) -> str:
    """Devuelve el error de validación como observación, para que el agente corrija la llamada."""
    detalles = "; ".join(
        f"{'.'.join(str(parte) for parte in detalle['loc'])}: {detalle['msg']}"
        for detalle in error.errors()
    )
    return f"Argumentos inválidos ({detalles}). Revisa la descripción de cada campo."


def _identificar(numero: str, transitorio: bool) -> str:
    """Traduce número y tipo al identificador de la copia local: "12" o "primero"."""
    posicion = POSICION_DEL_ORDINAL.get(numero, numero)
    if not transitorio:
        return posicion
    if posicion not in POSICION_DEL_ORDINAL.values():
        raise ValueError("Artículo no disponible. Los transitorios van del primero al cuarto.")
    return TRANSITORIOS[int(posicion) - 1]


@tool(args_schema=ArgumentosArticulo)
def obtener_articulo(numero: str, transitorio: bool = False) -> str:
    """Lee completo un artículo de la Ley REP (Ley 20.920) por su número.
    Usar cuando la consulta nombra un artículo, o para leer entero uno que buscar_en_ley
    mostró recortado."""
    tipo = " transitorio" if transitorio else ""
    try:
        fragmento = obtener_fragmento_ley_rep(_identificar(numero.strip().lower(), transitorio))
    except ValueError as error:
        return f"No pude leer el artículo {numero}{tipo}: {error}"
    return f"[{fragmento['referencia']}]\n{fragmento['texto']}"


# @tool no recibe esta opción. Sin ella, un argumento inválido corta toda la ejecución del agente.
obtener_articulo.handle_validation_error = explicar_argumentos_invalidos
