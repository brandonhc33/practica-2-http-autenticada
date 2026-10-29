"""La suite automática falla si alguna dependencia intenta usar la red real."""

from typing import NoReturn

import pytest


@pytest.fixture(autouse=True)
def bloquear_conexiones_externas(monkeypatch: pytest.MonkeyPatch) -> None:
    def impedir_conexion(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("Conexión externa no simulada dentro de la suite automática.")

    for ruta in (
        "socket.create_connection",
        "socket.socket.connect",
        "socket.socket.connect_ex",
        "socket.getaddrinfo",
    ):
        monkeypatch.setattr(ruta, impedir_conexion)
