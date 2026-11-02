"""El ensayo manual conserva evidencias y respeta los límites con transporte simulado."""

import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.ensayo_rate_limit import main


class EnsayoRateLimitTests(unittest.TestCase):
    def test_simulado_documenta_429_recuperacion_y_suma_sin_red(self):
        with tempfile.TemporaryDirectory() as directorio:
            salida = Path(directorio) / "evidencia.json"
            with (
                patch("sys.argv", ["ensayo", "--simulado", "--salida", str(salida)]),
                patch("sys.stdout", new_callable=StringIO),
                patch("scripts.ensayo_rate_limit.load_dotenv") as cargar,
            ):
                self.assertEqual(main(), 0)
            evidencia = json.loads(salida.read_text())
        cargar.assert_not_called()
        self.assertEqual(evidencia["modo"], "simulado")
        self.assertEqual(evidencia["primer_429"]["consulta"], 2)
        self.assertEqual(evidencia["resumen"]["intentos_http"], 4)
        self.assertEqual(evidencia["resumen"]["respuestas_con_costo"], 2)
        self.assertEqual(evidencia["resumen"]["costo_conocido_usd"], "0.0106")
        self.assertEqual(evidencia["consultas"][-1]["estado"], "completada")

    def test_maximo_de_envios_incluye_reintentos(self):
        with tempfile.TemporaryDirectory() as directorio:
            salida = Path(directorio) / "evidencia.json"
            with (
                patch(
                    "sys.argv",
                    ["ensayo", "--simulado", "--max-envios", "2", "--salida", str(salida)],
                ),
                patch("sys.stdout", new_callable=StringIO),
            ):
                self.assertEqual(main(), 0)
            evidencia = json.loads(salida.read_text())
        self.assertEqual(evidencia["resumen"]["intentos_http"], 2)
        self.assertEqual(evidencia["resumen"]["consultas_fallidas"], 1)

    def test_no_sobrescribe_una_evidencia_anterior(self):
        with tempfile.TemporaryDirectory() as directorio:
            salida = Path(directorio) / "evidencia.json"
            salida.write_text("original")
            with (
                patch("sys.argv", ["ensayo", "--real", "--salida", str(salida)]),
                patch("sys.stderr", new_callable=StringIO),
                patch("scripts.ensayo_rate_limit.load_dotenv") as cargar,
                self.assertRaises(SystemExit),
            ):
                main()
            self.assertEqual(salida.read_text(), "original")
        cargar.assert_not_called()

    def test_configuracion_invalida_falla_antes_de_cargar_la_clave(self):
        casos = (
            ["--consultas", "0"],
            ["--max-envios", "61"],
            ["--presupuesto-total", "nan"],
            ["--max-costo-conocido-usd", "NaN"],
        )
        for argumentos in casos:
            with (
                self.subTest(argumentos=argumentos),
                patch("sys.argv", ["ensayo", "--real", "--salida", "sin-crear.json", *argumentos]),
                patch("sys.stderr", new_callable=StringIO),
                patch("scripts.ensayo_rate_limit.load_dotenv") as cargar,
                self.assertRaises(SystemExit),
            ):
                main()
            cargar.assert_not_called()
