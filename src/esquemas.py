"""Contrato de respuestas y validaciones de las consultas de la API."""

import re
from datetime import date
from decimal import Decimal
from typing import Annotated, ClassVar, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    ValidationInfo,
    field_serializer,
    field_validator,
)
from pydantic_core import PydanticCustomError

from .catalogo import AGENTES

LIMITES_CONSULTA = {"agente": 32, "modelo": 64, "mensaje": 4_000}
EJEMPLO_CONSULTA = {
    "agente": "gemini",
    "modelo": "flash-lite",
    "mensaje": "Hola, ¿en qué puedes ayudarme?",
}


class RespuestaAPI[Detalle](BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    error: bool
    codigo: int = Field(ge=100, le=599)
    mensaje: str
    detalles: Detalle


class ValidacionCampo(BaseModel):
    campo: str
    errores: list[str]


class EstadoAPI(BaseModel):
    estado: Literal["ok"] = "ok"


class Consulta(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", strict=True, json_schema_extra={"examples": [dict(EJEMPLO_CONSULTA)]}
    )

    agente: str = Field(min_length=1, max_length=LIMITES_CONSULTA["agente"])
    modelo: str = Field(min_length=1, max_length=LIMITES_CONSULTA["modelo"])
    mensaje: str = Field(min_length=1, max_length=LIMITES_CONSULTA["mensaje"])

    @field_validator("agente", "modelo", "mensaje", mode="before")
    @classmethod
    def validar_texto(cls, valor: object, info: ValidationInfo) -> object:
        # Pydantic se encarga de rechazar los tipos distintos de str.
        if not isinstance(valor, str):
            return valor

        errores: list[str] = []
        campo = info.field_name
        if campo is None:
            raise RuntimeError("El validador de texto debe estar asociado a un campo.")
        if len(valor) > LIMITES_CONSULTA[campo]:
            errores.append(f"No puede superar los {LIMITES_CONSULTA[campo]} caracteres.")
        if not valor.strip():
            errores.append("No puede estar vacío ni contener solo espacios.")
        elif campo in ("agente", "modelo") and not re.fullmatch(r"[a-z0-9_-]+", valor):
            errores.append(
                "Usa solo letras minúsculas, números, guiones o guiones bajos, sin espacios."
            )
        if errores:
            raise PydanticCustomError(
                "texto_invalido", "{mensaje}", {"mensaje": " ".join(errores), "errores": errores}
            )
        return valor

    @field_validator("agente")
    @classmethod
    def agente_disponible(cls, valor: str) -> str:
        if valor not in AGENTES:
            raise PydanticCustomError(
                "agente_no_disponible",
                "Agente no disponible. Usa: {disponibles}.",
                {"disponibles": ", ".join(AGENTES)},
            )
        return valor

    @field_validator("modelo")
    @classmethod
    def modelo_del_agente(cls, valor: str, info: ValidationInfo) -> str:
        # agente se valida primero; si falla, no se puede comprobar la combinación.
        agente = info.data.get("agente")
        if agente is not None and valor not in AGENTES[agente]["modelos"]:
            raise PydanticCustomError(
                "modelo_no_disponible",
                "Modelo no disponible para {agente}. Usa: {disponibles}.",
                {"agente": agente, "disponibles": ", ".join(AGENTES[agente]["modelos"])},
            )
        return valor


def decimal_fijo(valor: Decimal) -> str:
    """Conserva todos los decimales significativos, con un mínimo de dos."""
    entero, _, decimales = format(valor, "f").partition(".")
    return f"{entero}.{decimales.rstrip('0').ljust(2, '0')}"


# Los importes se publican como texto para conservar el símbolo y evitar exponentes.
type ImporteUSD = Annotated[
    Decimal,
    Field(ge=0),
    PlainSerializer(lambda valor: f"US$ {decimal_fijo(valor)}", return_type=str, when_used="json"),
]
type ImporteCLP = Annotated[
    Decimal,
    Field(ge=0),
    PlainSerializer(lambda valor: f"$ {decimal_fijo(valor)}", return_type=str, when_used="json"),
]


class UsoTokens(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", strict=True)

    entrada: int = Field(ge=0)
    salida: int = Field(ge=0, description="Incluye los tokens de razonamiento.")
    total: int = Field(ge=0)
    entrada_cache: int = Field(default=0, ge=0, description="Parte de la entrada reutilizada.")


class TarifasTokens(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    entrada: ImporteUSD
    entrada_cache: ImporteUSD
    salida: ImporteUSD


class TarifasTokensCLP(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    entrada: ImporteCLP
    entrada_cache: ImporteCLP
    salida: ImporteCLP


class CostosMoneda(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    moneda: Literal["USD", "CLP"]
    entrada: Decimal = Field(ge=0)
    salida: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)

    @field_serializer("entrada", "salida", "total", when_used="json")
    def formatear_importe(self, valor: Decimal) -> str:
        simbolo = "US$" if self.moneda == "USD" else "$"
        return f"{simbolo} {decimal_fijo(valor)}"


class TipoCambio(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    clp_por_usd: Annotated[
        Decimal,
        Field(gt=0),
        PlainSerializer(decimal_fijo, return_type=str, when_used="json"),
    ]
    fecha: date | None
    fuente: str


class CostoEstimado(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    modelo: str
    usd: CostosMoneda
    clp: CostosMoneda | None
    tipo_cambio: TipoCambio | None
    tarifas_por_millon_usd: TarifasTokens
    tarifas_por_millon_clp: TarifasTokensCLP | None
    aviso_clp: str | None = Field(
        default=None,
        description="Es null cuando la conversión a CLP se completa; contiene un aviso si falla.",
    )


class Resultado(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    respuesta: str
    uso: UsoTokens | None = None
    costo_estimado: CostoEstimado | None = None
