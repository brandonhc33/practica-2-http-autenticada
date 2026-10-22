"""Coordina la configuración, selección y ejecución de los agentes registrados."""

import os
from typing import Any, Protocol

from prompts.banco import NombrePrompt

from .agente_gemini import consultar_gemini, consultar_gemini_raw
from .catalogo import AGENTES
from .esquemas import Consulta, Resultado


class Cliente[T](Protocol):
    def __call__(self, modelo: str, mensaje: str, *, prompt: NombrePrompt | None = None) -> T: ...


CLIENTES: dict[str, Cliente[Resultado]] = {"gemini": consultar_gemini}
CLIENTES_RAW: dict[str, Cliente[dict[str, Any]]] = {"gemini": consultar_gemini_raw}


class AgenteNoConfigurado(ValueError):
    """El agente necesita una credencial que aún no está configurada."""

    def __init__(self, agente: str, clave: str) -> None:
        super().__init__(f"Falta configurar {clave} en el servidor.")
        self.agente = agente
        self.clave = clave


def obtener_modelo_configurado(consulta: Consulta) -> str:
    configuracion = AGENTES[consulta.agente]
    clave = configuracion["clave"]
    if not os.getenv(clave, "").strip():
        raise AgenteNoConfigurado(consulta.agente, clave)
    return configuracion["modelos"][consulta.modelo]


def consultar_agente(consulta: Consulta) -> Resultado:
    modelo = obtener_modelo_configurado(consulta)
    cliente = CLIENTES.get(consulta.agente)
    if cliente is None:
        raise ValueError(f"Falta implementar el cliente del agente {consulta.agente}.")
    if consulta.prompt is not None:
        return cliente(modelo, consulta.mensaje, prompt=consulta.prompt)
    return cliente(modelo, consulta.mensaje)


def consultar_agente_raw(consulta: Consulta) -> dict[str, Any]:
    modelo = obtener_modelo_configurado(consulta)
    cliente = CLIENTES_RAW.get(consulta.agente)
    if cliente is None:
        raise ValueError(f"Falta implementar el cliente raw del agente {consulta.agente}.")
    if consulta.prompt is not None:
        return cliente(modelo, consulta.mensaje, prompt=consulta.prompt)
    return cliente(modelo, consulta.mensaje)
