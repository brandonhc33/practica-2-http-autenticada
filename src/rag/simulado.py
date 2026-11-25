"""Embeddings y modelo locales para ensayar el servicio sin clave, red ni costo.

No reemplazan a Gemini: los embeddings comparan palabras, no significado, y el modelo
solo copia el comienzo del primer fragmento. Sirven también de referencia de comparación.
"""

import hashlib
import json
import math
import re
import unicodedata
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

MODELO_LEXICO = "local/palabras-v1"
DIMENSIONES_LEXICO = 2048
NOMBRE_MODELO_SIMULADO = "simulado"
PALABRAS_VACIAS = frozenset(
    "a al ante como con cual cuales cuando de del desde donde el ella en entre es esta este esto "
    "estos han hasta la las le les lo los mas mi mis no o para pero por que quien quienes se segun "
    "ser si sin sobre son su sus un una uno unos y ya".split()
)


def palabras(texto: str) -> list[str]:
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    limpio = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    # Quitar la s final acerca «envase» y «envases»; no es un análisis del idioma.
    return [
        p.rstrip("s") or p
        for p in re.findall(r"[a-z0-9]+", limpio)
        if p not in PALABRAS_VACIAS
    ]


class EmbeddingsDePalabras(Embeddings):
    """Cada palabra suma en una posición fija; textos con palabras comunes quedan cerca."""

    def _vector(self, texto: str) -> list[float]:
        conteos: dict[int, int] = {}
        for palabra in palabras(texto):
            posicion = int.from_bytes(hashlib.sha256(palabra.encode()).digest()[:4], "big")
            posicion %= DIMENSIONES_LEXICO
            conteos[posicion] = conteos.get(posicion, 0) + 1
        vector = [0.0] * DIMENSIONES_LEXICO
        for posicion, veces in conteos.items():
            vector[posicion] = 1 + math.log(veces)
        norma = math.sqrt(sum(v * v for v in vector))
        if not norma:
            # Un vector nulo no tiene dirección que comparar.
            vector[0] = norma = 1.0
        return [v / norma for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class ModeloQueCita(BaseChatModel):
    """Responde con el comienzo del primer fragmento del contexto y su cita."""

    @property
    def _llm_type(self) -> str:
        return NOMBRE_MODELO_SIMULADO

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        texto = str(messages[-1].content)
        encontrado = re.search(r"<contexto_json>\n(.*?)\n</contexto_json>", texto, re.DOTALL)
        if encontrado is None:
            raise ValueError("El prompt no trae el contexto esperado.")
        primero = json.loads(encontrado[1])[0]
        extracto = " ".join(primero["texto"].split())[:200]
        mensaje = AIMessage(content=f"Respuesta simulada: {extracto} [{primero['cita']}]")
        return ChatResult(generations=[ChatGeneration(message=mensaje)])
