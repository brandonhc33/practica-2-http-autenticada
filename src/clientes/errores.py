"""Errores públicos del cliente, sin cuerpos ni credenciales del proveedor."""


class ErrorCliente(Exception):
    """Fallo previsto al consultar el proveedor."""

    def __init__(self, mensaje: str, *, codigo_http: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo_http = codigo_http


class ErrorAutenticacion(ErrorCliente):
    """La credencial del proveedor es inválida o carece de permisos."""


class ErrorPeticion(ErrorCliente):
    """La petición o su configuración necesita una corrección."""


class ErrorRespuesta(ErrorCliente):
    """El proveedor respondió, pero su salida no cumple el contrato."""


class ErrorTemporalProveedor(ErrorCliente):
    """Fallo potencialmente recuperable mediante una nueva petición."""

    def __init__(
        self,
        mensaje: str,
        *,
        codigo_http: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(mensaje, codigo_http=codigo_http)
        self.retry_after = retry_after


class ErrorTimeoutLectura(ErrorTemporalProveedor):
    """La petición pudo procesarse; repetirla requiere habilitación explícita."""


class ReintentosAgotados(ErrorCliente):
    """La política impidió continuar por cantidad de intentos o por tiempo."""

    def __init__(
        self,
        intentos: int,
        ultimo_error: ErrorTemporalProveedor | None,
        *,
        presupuesto_agotado: bool = False,
    ) -> None:
        motivo = (
            "Se agotó el presupuesto de tiempo"
            if presupuesto_agotado
            else "Se agotaron los intentos permitidos"
        )
        mensaje = f"{motivo} tras {intentos} intento(s). Intenta más tarde."
        if ultimo_error is not None:
            mensaje += f" Última causa: {ultimo_error}"
        super().__init__(
            mensaje, codigo_http=ultimo_error.codigo_http if ultimo_error is not None else None
        )
        self.intentos = intentos
        self.ultimo_error = ultimo_error
        self.presupuesto_agotado = presupuesto_agotado
