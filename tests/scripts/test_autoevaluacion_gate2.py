"""Un promedio alto no compensa un criterio crítico."""

import unittest
from unittest.mock import patch

from scripts import autoevaluacion_gate2 as auto

TODAS = dict.fromkeys(auto.PRUEBAS, True)


class TestAutoevaluacion(unittest.TestCase):
    def test_los_casos_de_la_rubrica(self):
        self.assertTrue(auto.evaluar_gate(88.8, TODAS))
        self.assertFalse(auto.evaluar_gate(88.8, {**TODAS, "logs_sin_contenido_crudo": False}))
        self.assertFalse(auto.evaluar_gate(73.8, TODAS))
        self.assertFalse(auto.evaluar_gate(100, {}))

    def test_pesos_puntajes_y_evidencia(self):
        base = {"peso": 1.0, "puntaje": 90, "a_favor": "a", "en_contra": "b",
                "evidencia": "README.md"}
        auto.validar({"x": base})
        for cambio in ({"peso": 0.9}, {"puntaje": 101}, {"en_contra": ""}, {"evidencia": "no.md"}):
            with self.subTest(cambio), self.assertRaises(ValueError):
                auto.validar({"x": {**base, **cambio}})

    def test_los_no_compensables_salen_de_las_pruebas(self):
        with patch("subprocess.run") as correr:
            correr.return_value.returncode = 1
            self.assertEqual(auto.ejecutar_pruebas(), dict.fromkeys(auto.PRUEBAS, False))
        self.assertEqual(correr.call_count, 4)
