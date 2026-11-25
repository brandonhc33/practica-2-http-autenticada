"""Comandos del Gate 2 sin red: ensayo, evaluación y verificación del entorno."""

import contextlib
import io
import os
import unittest
from unittest.mock import patch

import servicio_rag
import verificar_entorno
from scripts import evaluar_normas


def ejecutar(funcion, *args) -> tuple[int, str]:
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(salida):
        try:
            codigo = funcion(*args)
        except SystemExit as fin:
            codigo = int(fin.code or 0)
    return codigo, salida.getvalue()


class TestGate2(unittest.TestCase):
    def test_ensayo_completo(self):
        codigo, texto = ejecutar(servicio_rag.main, [])
        self.assertEqual(codigo, 0, texto)
        self.assertNotIn("FALLA", texto)
        self.assertIn("Proceso terminado sin errores.", texto)
        self.assertNotIn(servicio_rag.CORREO, texto)

    def test_los_comandos_reales_exigen_confirmacion(self):
        with patch.object(servicio_rag, "abrir_indice_normas", return_value=(None, {})):
            codigo, texto = ejecutar(servicio_rag.main, ["preguntar", "¿Qué es un envase?"])
        self.assertEqual(codigo, 1)
        self.assertIn("consume cuota", texto)
        with patch.object(
            servicio_rag, "planificar", return_value={"embeddings_por_calcular": 3}
        ):
            codigo, texto = ejecutar(servicio_rag.main, ["indexar"])
        self.assertEqual(codigo, 1)
        self.assertIn("consume cuota", texto)

    def test_un_error_del_proveedor_no_muestra_su_mensaje(self):
        with patch.object(servicio_rag, "planificar", side_effect=RuntimeError("secreto")):
            codigo, texto = ejecutar(servicio_rag.main, ["estado"])
        self.assertEqual(codigo, 1)
        self.assertNotIn("secreto", texto)

    def test_evaluacion_local_por_palabras(self):
        codigo, texto = ejecutar(evaluar_normas.main, [])
        self.assertEqual(codigo, 0, texto)
        self.assertIn("Motor: palabras", texto)
        self.assertIn("cumple: una norma", texto)

    def test_evaluacion_real_exige_indice_o_confirmacion(self):
        with patch.object(evaluar_normas, "abrir_indice_normas", return_value=(None, {})):
            codigo, texto = ejecutar(evaluar_normas.main, ["--motor", "gemini"])
        self.assertEqual(codigo, 1)
        self.assertIn("consume cuota", texto)

    def test_el_entorno_incompleto_termina_con_error_y_sin_mostrar_claves(self):
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "clave-de-prueba"}),
            patch("src.rag.indice_normas.leer_manifiesto", side_effect=ValueError("ausente")),
        ):
            codigo, texto = ejecutar(verificar_entorno.main)
        self.assertEqual(codigo, 1)
        self.assertIn("indexar con", texto)
        self.assertNotIn("clave-de-prueba", texto)
