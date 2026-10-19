"""Coordina la configuración, selección y ejecución de los agentes registrados."""

import os
from collections.abc import Callable

from .agente_gemini import consultar_gemini
from .catalogo import AGENTES
from .esquemas import Consulta, Resultado

CLIENTES: dict[str, Callable[[str, str], Resultado]] = {"gemini": consultar_gemini}


class AgenteNoConfigurado(ValueError):
    """El agente necesita una credencial que aún no está configurada."""

    def __init__(self, agente: str, clave: str) -> None:
        super().__init__(f"Falta configurar {clave} en el servidor.")
        self.agente = agente
        self.clave = clave


def consultar_agente(consulta: Consulta) -> Resultado:
    configuracion = AGENTES[consulta.agente]
    clave = configuracion["clave"]
    if not os.getenv(clave, "").strip():
        raise AgenteNoConfigurado(consulta.agente, clave)

    cliente = CLIENTES.get(consulta.agente)
    if cliente is None:
        raise ValueError(f"Falta implementar el cliente del agente {consulta.agente}.")
    modelo = configuracion["modelos"][consulta.modelo]
    return cliente(modelo, consulta.mensaje)
