"""API local con endpoints protegidos mediante un Bearer token propio."""

import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.agentes import AgenteNoConfigurado, consultar_agente
from src.esquemas import Consulta, EstadoAPI, RespuestaAPI, Resultado
from src.respuestas import ErrorAPI, registrar_manejadores

CARPETA_PROYECTO = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    load_dotenv(CARPETA_PROYECTO / ".env")
    token = os.getenv("API_BEARER_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Falta API_BEARER_TOKEN. Configura el token de tu API en .env.")
    app.state.bearer_token = token.encode("utf-8")
    yield


bearer = HTTPBearer(auto_error=False)


def validar_bearer(
    request: Request,
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    if credenciales is None or not secrets.compare_digest(
        credenciales.credentials.encode("utf-8"), request.app.state.bearer_token
    ):
        raise ErrorAPI(
            codigo=401,
            mensaje="No se pudo autenticar la solicitud.",
            detalles={
                "causa": "Bearer token ausente o inválido.",
                "encabezado_requerido": "Authorization: Bearer <API_BEARER_TOKEN>",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


app = FastAPI(
    title="Práctica 2 - API autenticada",
    lifespan=lifespan,
    dependencies=[Depends(validar_bearer)],
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    redirect_slashes=False,
)
registrar_manejadores(app)


@app.get("/health", response_model=RespuestaAPI[EstadoAPI])
def health() -> RespuestaAPI[EstadoAPI]:
    return RespuestaAPI(
        error=False, codigo=200, mensaje="La API está disponible.", detalles=EstadoAPI()
    )


@app.post("/consultar", response_model=RespuestaAPI[Resultado])
def consultar(consulta: Consulta) -> RespuestaAPI[Resultado]:
    try:
        resultado = consultar_agente(consulta)
    except AgenteNoConfigurado as error:
        raise ErrorAPI(
            codigo=503,
            mensaje="El agente no está configurado en el servidor.",
            detalles={"agente": error.agente, "configuracion_requerida": error.clave},
        ) from None
    except ValueError as error:
        raise ErrorAPI(
            codigo=502,
            mensaje="No se pudo completar la consulta al agente.",
            detalles={"agente": consulta.agente, "modelo": consulta.modelo, "causa": str(error)},
        ) from None
    return RespuestaAPI(
        error=False, codigo=200, mensaje="Consulta realizada correctamente.", detalles=resultado
    )
