"""Prueba el circuito completo de aprobación con una pseudoterminal, sin Gemini."""

import os
import select
import subprocess
import sys
import time
import unittest
from pathlib import Path


@unittest.skipUnless(os.name == "posix", "El diagnóstico interactivo usa una terminal POSIX.")
class TestEnsayoTerminal(unittest.TestCase):
    def ejecutar(self, entradas: tuple[bytes, bytes]) -> str:
        import pty

        maestro, esclavo = pty.openpty()
        self.addCleanup(os.close, maestro)
        self.addCleanup(os.close, esclavo)
        proceso = subprocess.Popen(
            [sys.executable, "-m", "tests.orquestacion.ensayo_terminal", "--tiempo-limite", "2"],
            cwd=Path(__file__).resolve().parents[2],
            stdin=esclavo,
            stdout=esclavo,
            stderr=esclavo,
        )
        try:
            salida = b""
            enviados = 0
            limite = time.monotonic() + 15
            aviso = b"Escribe s o n y pulsa Enter; no es un men"
            while time.monotonic() < limite:
                disponibles, _, _ = select.select([maestro], [], [], 0.1)
                if disponibles:
                    salida += os.read(maestro, 65536)
                    if salida.count(aviso) > enviados and enviados < len(entradas):
                        os.write(maestro, entradas[enviados])
                        enviados += 1
                if b"Fin del diagn" in salida:
                    proceso.wait(timeout=3)
                    self.assertEqual(proceso.returncode, 0, salida.decode(errors="replace"))
                    return salida.decode()
                if not disponibles and proceso.poll() is not None:
                    self.fail(salida.decode(errors="replace"))
            self.fail(f"El diagnóstico no terminó: {salida.decode(errors='replace')}")
        finally:
            if proceso.poll() is None:
                proceso.kill()
            proceso.wait()

    def test_agente_lee_s_y_n_en_la_misma_terminal(self):
        salida = self.ejecutar((b"s\n", b"n\n"))
        self.assertIn("s recibida: aprobación explícita", salida)
        self.assertIn("n recibida: rechazo explícito", salida)
        self.assertIn("Decisiones simuladas: [true, false]", salida)
        self.assertNotIn("tiempo agotado", salida)

    def test_enter_vacio_rechaza_sin_ocultar_el_motivo(self):
        salida = self.ejecutar((b"\n", b"n\n"))
        self.assertIn("línea vacía recibida", salida)
        self.assertIn("n recibida: rechazo explícito", salida)
        self.assertIn("Decisiones simuladas: [false, false]", salida)
