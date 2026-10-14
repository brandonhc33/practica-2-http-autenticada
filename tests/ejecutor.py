"""Colores para la salida estándar de unittest, sin cambiar su ejecución."""

import os
import sys
import unittest
from typing import TextIO


class SalidaConColor:
    def __init__(self, stream: TextIO):
        self.stream = stream
        self.activo = (
            stream.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"
        )

    def write(self, texto: str):
        color = None
        if texto in {"ok", ".", "OK"}:
            color = "32"
        elif texto in {"FAIL", "ERROR", "F", "E", "FAILED", "u", "unexpected success"}:
            color = "31"
        elif texto in {"s", "x", "expected failure", "NO TESTS RAN"} or texto.startswith(
            "skipped "
        ):
            color = "33"
        elif texto.startswith(("FAIL: ", "ERROR: ", "UNEXPECTED SUCCESS: ")):
            color = "31"
        if self.activo and color:
            texto = f"\033[{color}m{texto}\033[0m"
        return self.stream.write(texto)

    def flush(self):
        self.stream.flush()


class EjecutorConColor(unittest.TextTestRunner):
    def __init__(self, stream: TextIO | None = None, **kwargs):
        super().__init__(stream=SalidaConColor(stream or sys.stderr), **kwargs)
