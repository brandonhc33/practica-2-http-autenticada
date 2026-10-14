"""Respuestas JSON y manejadores de errores compartidos por todos los endpoints."""

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .esquemas import EJEMPLO_CONSULTA, Consulta, RespuestaAPI, ValidacionCampo

logger = logging.getLogger(__name__)


class ErrorAPI(HTTPException):
    """Error previsto con un mensaje breve y detalles útiles para el cliente."""

    def __init__(
        self,
        codigo: int,
        mensaje: str,
        detalles: dict[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=codigo, detail=mensaje, headers=headers)
        self.detalles: dict[str, Any] = detalles or {}


def respuesta_json(
    codigo: int,
    mensaje: str,
    detalles: dict[str, Any],
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    respuesta = RespuestaAPI(error=codigo >= 400, codigo=codigo, mensaje=mensaje, detalles=detalles)
    return JSONResponse(
        status_code=codigo, content=respuesta.model_dump(mode="json"), headers=headers
    )


def mensajes_validacion(error: Mapping[str, Any], campo: str) -> list[str]:
    tipo = error["type"]
    contexto = error.get("ctx", {})
    if tipo == "texto_invalido":
        return contexto["errores"]
    if tipo in ("agente_no_disponible", "modelo_no_disponible"):
        return [error["msg"]]
    if tipo == "missing":
        return [
            "El cuerpo de la solicitud es obligatorio."
            if campo == "cuerpo"
            else "El campo es obligatorio."
        ]
    if tipo == "extra_forbidden":
        if campo == "pregunta":
            return ["El campo no está permitido. Envía el texto de la consulta en 'mensaje'."]
        return ["El campo no está permitido."]
    if tipo == "string_type":
        return ["Debe ser una cadena de texto."]
    if tipo == "string_too_short":
        return [f"Debe contener al menos {contexto['min_length']} caracteres."]
    if tipo == "string_too_long":
        return [f"No puede superar los {contexto['max_length']} caracteres."]
    if tipo == "json_invalid":
        return ["El cuerpo debe ser un JSON válido. Revisa las comillas, las comas y las llaves."]
    if tipo in ("model_type", "model_attributes_type", "dict_type"):
        return ["Debe ser un objeto JSON con los campos requeridos."]
    return ["El valor no cumple las validaciones del campo."]


async def manejar_validacion(request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, RequestValidationError):
        return await manejar_error_interno(request, error)
    por_campo: dict[str, list[str]] = {}
    for validacion in error.errors():
        ubicacion = validacion.get("loc", ())
        ruta = (
            ubicacion[1:]
            if ubicacion and ubicacion[0] in ("body", "query", "path", "header", "cookie")
            else ubicacion
        )
        campo = ".".join(str(parte) for parte in ruta) or "cuerpo"
        if validacion["type"] == "json_invalid":
            campo = "cuerpo"
        mensajes = por_campo.setdefault(campo, [])
        for mensaje in mensajes_validacion(validacion, campo):
            if mensaje not in mensajes:
                mensajes.append(mensaje)

    detalles: dict[str, Any] = {
        "validaciones": [
            ValidacionCampo(campo=campo, errores=errores).model_dump()
            for campo, errores in por_campo.items()
        ]
    }
    if request.url.path == "/consultar":
        detalles["campos_permitidos"] = list(Consulta.model_fields)
        detalles["ejemplo"] = EJEMPLO_CONSULTA
    return respuesta_json(422, "Revisa los campos de la solicitud.", detalles)


async def manejar_error_http(request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, StarletteHTTPException):
        return await manejar_error_interno(request, error)
    if isinstance(error, ErrorAPI):
        return respuesta_json(error.status_code, error.detail, error.detalles, error.headers)

    mensajes = {
        400: "La solicitud no es válida.",
        401: "No se pudo autenticar la solicitud.",
        403: "No tienes permiso para realizar esta operación.",
        404: "La ruta solicitada no existe.",
        405: "El método HTTP no está permitido para esta ruta.",
        413: "El cuerpo de la solicitud supera el tamaño permitido.",
        415: "El formato del contenido no es compatible.",
        429: "Se alcanzó el límite de solicitudes. Intenta más tarde.",
        500: "Ocurrió un error interno en el servidor.",
        502: "No se pudo completar la consulta al agente.",
        503: "El servicio no está disponible temporalmente.",
        504: "El servicio tardó demasiado en responder.",
    }
    detalles: dict[str, Any] = {"ruta": request.url.path, "metodo": request.method}
    if error.status_code == 405 and error.headers:
        detalles["metodos_permitidos"] = [
            metodo.strip() for metodo in error.headers.get("Allow", "").split(",") if metodo.strip()
        ]
    elif error.status_code not in (404, 500) and error.detail:
        detalles["causa"] = error.detail
    return respuesta_json(
        error.status_code,
        mensajes.get(error.status_code, "No se pudo completar la solicitud."),
        detalles,
        error.headers,
    )


async def manejar_error_interno(request: Request, error: Exception) -> JSONResponse:
    logger.error("Error no controlado en %s %s", request.method, request.url.path, exc_info=error)
    return respuesta_json(
        500,
        "Ocurrió un error interno en el servidor.",
        {
            "accion": "Intenta nuevamente más tarde. Si el problema persiste, contacta al administrador."
        },
    )


def registrar_manejadores(app: FastAPI) -> None:
    # Starlette también genera HTTPException para rutas y métodos inexistentes.
    app.add_exception_handler(StarletteHTTPException, manejar_error_http)
    app.add_exception_handler(RequestValidationError, manejar_validacion)
    app.add_exception_handler(Exception, manejar_error_interno)
