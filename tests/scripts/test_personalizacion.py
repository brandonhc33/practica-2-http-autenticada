"""Los comandos de los bloques 29 y 30 funcionan sin clave y protegen la evidencia."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage

from scripts import dataset_tuning, decision_personalizacion, linea_base_rutas
from src.personalizacion.dataset import RUTA_DATASET, cargar_dataset, huella_archivo
from src.personalizacion.linea_base import huella_prompt
from tests.orquestacion.modelo_falso import crear_modelo_falso


class TestComandosPersonalizacion(unittest.TestCase):
    def setUp(self):
        self.salida = self.enterContext(redirect_stdout(io.StringIO()))
        self.enterContext(redirect_stderr(io.StringIO()))
        self.temporal = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.enterContext(patch("scripts.rag_comun.load_dotenv"))

    def test_dataset_tuning_no_necesita_clave_ni_red(self):
        codigo = dataset_tuning.main(["--comprobar-validador", "--comprobar-api"])
        texto = self.salida.getvalue()
        self.assertEqual(codigo, 0)
        self.assertIn("24 ejemplos construidos", texto)
        self.assertIn("24 ejemplos, 0 problemas encontrados", texto)
        self.assertEqual(texto.count(": detectado:"), 10)
        self.assertIn("Enterprise Agent Platform", texto)

    def test_dataset_con_problemas_termina_con_error(self):
        dataset = cargar_dataset()
        dataset["ejemplos"][0]["salida"]["ruta"] = "otra"
        ruta = self.temporal / "roto.json"
        ruta.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(dataset_tuning.main(["--dataset", str(ruta)]), 1)

    def test_regla_local_no_crea_modelo(self):
        with patch("scripts.linea_base_rutas.crear_modelo") as crear:
            self.assertEqual(linea_base_rutas.main(["--solo-regla-local"]), 0)
        crear.assert_not_called()
        self.assertIn("23 de 24", self.salida.getvalue())

    def test_sin_consentimiento_o_sin_clave_no_mide_ni_crea_archivo(self):
        destino = self.temporal / "linea.json"
        for argumentos in (
            ["--salida", str(destino)],
            ["--salida", str(destino), "--confirmar-consumo"],
        ):
            with (
                self.subTest(argumentos=argumentos),
                patch("scripts.linea_base_rutas.crear_modelo") as crear,
            ):
                with self.assertRaises(SystemExit) as salida:
                    linea_base_rutas.main(argumentos)
                self.assertEqual(salida.exception.code, 1)
                crear.assert_not_called()
                self.assertFalse(destino.exists())

    def test_salida_existente_se_conserva(self):
        destino = self.temporal / "linea.json"
        destino.write_text("anterior", encoding="utf-8")
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "ficticia"}),
            patch("scripts.linea_base_rutas.crear_modelo") as crear,
            self.assertRaises(SystemExit),
        ):
            linea_base_rutas.main(["--salida", str(destino), "--confirmar-consumo"])
        crear.assert_not_called()
        self.assertEqual(destino.read_text(encoding="utf-8"), "anterior")

    def medir_con_modelo_falso(self, destino: Path) -> int:
        dataset = cargar_dataset()
        respuestas = [
            AIMessage(
                content=e["salida"]["ruta"],
                usage_metadata={"input_tokens": 90, "output_tokens": 2, "total_tokens": 92},
            )
            for e in dataset["ejemplos"]
        ]
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "ficticia"}),
            patch(
                "scripts.linea_base_rutas.crear_modelo", return_value=crear_modelo_falso(respuestas)
            ),
        ):
            return linea_base_rutas.main(["--salida", str(destino), "--confirmar-consumo"])

    def test_medicion_guarda_huellas_y_decision_genera_documento(self):
        linea = self.temporal / "linea.json"
        self.assertEqual(self.medir_con_modelo_falso(linea), 0)
        informe = json.loads(linea.read_text(encoding="utf-8"))
        self.assertEqual(informe["huella_dataset"], huella_archivo(RUTA_DATASET))
        self.assertEqual(informe["huella_prompt"], huella_prompt())
        self.assertTrue(informe["resultado"]["resumen"]["completa"])
        self.assertEqual(informe["resultado"]["resumen"]["discrepancias_regla_local"], ["r08"])

        documento = self.temporal / "decision.md"
        codigo = decision_personalizacion.main(
            ["--linea-base", str(linea), "--salida", str(documento)]
        )
        self.assertEqual(codigo, 0)
        texto = documento.read_text(encoding="utf-8")
        self.assertIn("**Mayor puntaje: RAG.**", texto)
        self.assertIn("## 4. Qué se necesitaría para ejecutarla", texto)
        with self.assertRaises(SystemExit):
            decision_personalizacion.main(["--linea-base", str(linea), "--salida", str(documento)])

    def test_decision_sin_medicion_muestra_escenarios_y_no_escribe(self):
        documento = self.temporal / "decision.md"
        self.assertEqual(decision_personalizacion.main([]), 0)
        self.assertIn("problema_de_formato_o_tono = True", self.salida.getvalue())
        with self.assertRaises(SystemExit):
            decision_personalizacion.main(["--salida", str(documento)])
        self.assertFalse(documento.exists())

    def test_linea_base_de_otro_dataset_se_rechaza(self):
        linea = self.temporal / "linea.json"
        linea.write_text(
            json.dumps(
                {"huella_dataset": "otra", "huella_prompt": huella_prompt(), "resultado": {}}
            ),
            encoding="utf-8",
        )
        with self.assertRaises(SystemExit) as salida:
            decision_personalizacion.main(["--linea-base", str(linea)])
        self.assertEqual(salida.exception.code, 1)
