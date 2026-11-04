import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.evaluar_texto import (
    evaluar_caso,
    generar,
    guardar,
    preparar_revision,
    validar_casos,
    validar_revision,
)
from src.clientes.errores import ErrorCliente
from src.evaluacion.casos import construir_casos


class TestEvaluador(unittest.TestCase):
    def setUp(self):
        self.casos = construir_casos()
        self.registro = {
            "casos": self.casos,
            "intentos": [
                {
                    "id": caso["id"],
                    "estado": "ok",
                    "respuesta": "texto de prueba",
                    "salida_estructurada": {},
                    "metricas": {"precision": i / 20, "cobertura": i / 20, "f1": i / 20},
                }
                for i, caso in enumerate(self.casos)
            ],
        }

    def test_casos_distintos_con_fuentes(self):
        validar_casos(self.casos)
        self.assertEqual(len(self.casos), 20)
        with self.assertRaises(ValueError):
            validar_casos(self.casos + self.casos[:1])

    def test_extremos_y_empates_sin_duplicados(self):
        revision = preparar_revision(self.registro)
        self.assertEqual(
            [c["id"] for c in revision["casos"]],
            [f"rep-{i:02d}" for i in [1, 2, 3, 4, 5, 16, 17, 18, 19, 20]],
        )
        self.assertIsNone(revision["casos"][0]["correccion_factual"])
        for r in self.registro["intentos"]:
            r["metricas"]["f1"] = 1
        self.assertEqual(len({c["id"] for c in preparar_revision(self.registro)["casos"]}), 10)

    def test_no_acepta_menos_de_20_exitos(self):
        self.registro["intentos"][0]["estado"] = "error"
        with self.assertRaises(ValueError):
            preparar_revision(self.registro)

    def test_revision_pendiente_completa_y_evidencia_modificada(self):
        revision = preparar_revision(self.registro)
        with self.assertRaises(ValueError):
            validar_revision(self.registro, revision)
        revision.update(revisor="Estudiante", fecha_revision="2026-11-04")
        for caso in revision["casos"]:
            caso.update(
                correccion_factual="si",
                completitud="parcial",
                contradiccion="no",
                nota="Justificación de prueba.",
            )
        validar_revision(self.registro, revision)
        alterada = copy.deepcopy(revision)
        alterada["casos"][0]["respuesta"] = "cambio"
        with self.assertRaises(ValueError):
            validar_revision(self.registro, alterada)
        self.registro["intentos"][0]["respuesta"] = "otra"
        with self.assertRaises(ValueError):
            validar_revision(self.registro, revision)

    @patch("scripts.evaluar_texto.consultar_gemini_raw")
    def test_mide_solo_respuesta_y_no_envia_referencia(self, consultar):
        salida = {
            "estado": "respondida",
            "respuesta": self.casos[0]["referencia"],
            "citas": [
                {"id_fragmento": "ley20920-articulo-1", "cita_textual": "Texto de prueba distinto."}
            ],
            "antecedentes_faltantes": [],
        }
        consultar.return_value = {
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(salida)}}]
        }
        resultado = evaluar_caso(self.casos[0], "gemini-3.5-flash-lite")
        self.assertEqual(resultado["estado"], "ok")
        self.assertEqual(resultado["metricas"]["f1"], 1)
        entrada = json.loads(consultar.call_args.args[1])
        self.assertNotIn("referencia", entrada)
        self.assertIsNone(resultado["costo_usd_estimado"])

    @patch("scripts.evaluar_texto.consultar_gemini_raw")
    def test_fallos_no_se_convierten_en_metricas(self, consultar):
        consultar.side_effect = ErrorCliente("fallo de prueba")
        resultado = evaluar_caso(self.casos[0], "modelo")
        self.assertEqual(resultado["estado"], "error")
        self.assertNotIn("metricas", resultado)
        consultar.side_effect = KeyboardInterrupt
        self.assertEqual(evaluar_caso(self.casos[0], "modelo")["estado"], "interrumpido")

    @patch("scripts.evaluar_texto.evaluar_caso")
    def test_reanudacion_conserva_fallos_y_no_repite_exitos(self, evaluar):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "resultado.json"
            evaluar.side_effect = [
                self.registro["intentos"][0],
                {"id": "rep-02", "estado": "error"},
            ]
            self.assertFalse(generar(self.casos[:2], "modelo", ruta, False, 0))
            evaluar.reset_mock(side_effect=True)
            evaluar.return_value = self.registro["intentos"][1]
            self.assertTrue(generar(self.casos[:2], "modelo", ruta, True, 0))
            self.assertEqual(evaluar.call_count, 1)
            self.assertEqual(len(json.loads(ruta.read_text())["intentos"]), 3)
            with self.assertRaises(ValueError):
                generar(self.casos[:2], "otro-modelo", ruta, True, 0)
            with self.assertRaises(ValueError):
                generar(self.casos[:2], "modelo", ruta, False, 0)
            self.assertFalse(ruta.with_suffix(".json.tmp").exists())

    def test_guardado_crea_directorios(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "sub" / "datos.json"
            guardar(ruta, {"texto": "niño"})
            self.assertEqual(json.loads(ruta.read_text()), {"texto": "niño"})
