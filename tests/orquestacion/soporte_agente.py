"""Aísla los archivos y las sesiones del agente tanto con pytest como con unittest."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class PruebaAgente(unittest.TestCase):
    def setUp(self):
        self.directorio = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.trazas = self.directorio / "trazas.jsonl"
        self.aprobaciones = self.directorio / "aprobaciones.jsonl"
        self.informes = self.directorio / "informes"
        self.enterContext(patch("src.orquestacion.supervision.RUTA_TRAZAS", self.trazas))
        self.enterContext(
            patch("src.orquestacion.supervision.RUTA_APROBACIONES", self.aprobaciones)
        )
        self.enterContext(
            patch("src.orquestacion.herramientas.DIRECTORIO_INFORMES", self.informes)
        )
        self.enterContext(
            patch.dict("src.orquestacion.agente_con_herramientas.historiales", clear=True)
        )
