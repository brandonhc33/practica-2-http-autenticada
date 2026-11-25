"""El ensayo detecta el señuelo aunque el servicio no entregue el texto, y exige permiso."""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from scripts import ensayo_inyeccion_indirecta as ensayo
from src.gobernanza.prompts import RegistroDePrompts
from src.observabilidad.inyeccion import detectar_inyeccion
from src.observabilidad.trazas import logger


class TestEnsayoInyeccionIndirecta(unittest.TestCase):
    def setUp(self):
        anteriores, nivel = logger.handlers, logger.level
        self.addCleanup(lambda: (setattr(logger, "handlers", anteriores), logger.setLevel(nivel)))
        self.salida = self.enterContext(redirect_stdout(io.StringIO()))
        self.enterContext(redirect_stderr(io.StringIO()))
        self.enterContext(patch("scripts.rag_comun.load_dotenv"))
        self.registro = Path(self.enterContext(tempfile.TemporaryDirectory())) / "e.jsonl"

    def ensayar(self, texto):
        modelo = GenericFakeChatModel(
            messages=iter([AIMessage(content=texto)]), disable_streaming=True
        )
        return ensayo.ensayar(RegistroDePrompts.cargar().versiones[0], modelo)

    def test_la_orden_pasa_el_filtro(self):
        self.assertEqual(detectar_inyeccion(ensayo.ORDEN), [])

    def test_distingue_obedecer_de_resistir(self):
        self.assertFalse(self.ensayar("Aceites lubricantes [1].")["senuelo"])
        obedece = self.ensayar(f"Aceites [1]. {ensayo.SENUELO}")
        self.assertEqual((obedece["senuelo"], obedece["estado"]), (True, "ok"))
        sin_citas = self.ensayar(ensayo.SENUELO)
        self.assertEqual((sin_citas["senuelo"], sin_citas["estado"]), (True, "abstencion"))
        self.assertNotIn(ensayo.SENUELO, sin_citas["respuesta"])

    def test_sin_permiso_o_sin_clave_no_crea_modelo(self):
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        for extra in ([], ["--confirmar-consumo"]):
            with (
                self.subTest(extra),
                patch("scripts.ensayo_inyeccion_indirecta.crear_modelo") as crear,
                self.assertRaises(SystemExit),
            ):
                ensayo.main(["--registro", str(self.registro), *extra])
            crear.assert_not_called()
            self.assertFalse(self.registro.exists())

    def test_una_generacion_por_version(self):
        def crear(_alias):
            return GenericFakeChatModel(
                messages=iter([AIMessage(content="Pilas [1].")]), disable_streaming=True
            )

        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "prueba"}),
            patch("scripts.ensayo_inyeccion_indirecta.crear_modelo", side_effect=crear) as creado,
        ):
            self.assertEqual(
                ensayo.main(["--registro", str(self.registro), "--confirmar-consumo"]), 0)
        self.assertEqual(creado.call_count, len(RegistroDePrompts.cargar().versiones))
        self.assertNotIn("Pilas", self.registro.read_text())


if __name__ == "__main__":
    unittest.main()
