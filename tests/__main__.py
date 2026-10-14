"""Ejecuta todos los módulos test_*.py mediante descubrimiento de unittest."""

import sys
import unittest
from pathlib import Path

from tests.ejecutor import EjecutorConColor

if __name__ == "__main__":
    directorio = Path(__file__).resolve().parent
    unittest.main(
        module=None,
        testRunner=EjecutorConColor,
        argv=[
            sys.argv[0],
            "discover",
            "-s",
            str(directorio),
            "-t",
            str(directorio.parent),
            *sys.argv[1:],
        ],
    )
