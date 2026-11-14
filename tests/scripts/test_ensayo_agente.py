"""El ensayo del agente compara la herramienta elegida con la esperada, sin red ni tokens."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage

from scripts.ensayo_agente import CASOS, ejecutar_ensayo, main
from src.orquestacion.agente_con_herramientas import HERRAMIENTAS, construir_ejecutor
from src.orquestacion.modelo import RegistroLlamadas
from tests.orquestacion.modelo_falso import ModeloFalso, crear_modelo_falso, pedir_herramienta

ENSAYO = "scripts.ensayo_agente"
USO = {"input_tokens": 1_000, "output_tokens": 2_000, "total_tokens": 3_000}


def crear_modelo_del_ensayo() -> ModeloFalso:
    """Acierta en el primer y el tercer caso; en el segundo busca en vez de leer el artículo."""
    respuestas = (
        pedir_herramienta("buscar_en_ley", consulta="obligaciones consumidores"),
        AIMessage(content="Los consumidores deben entregar los residuos (artículo 34)."),
        pedir_herramienta("buscar_en_ley", consulta="artículo 12"),
        AIMessage(content="No encontré el artículo por tema."),
        AIMessage(content="Respondo consultas sobre la Ley REP."),
    )
    return crear_modelo_falso(
        (respuesta.model_copy(update={"usage_metadata": USO}) for respuesta in respuestas),
        callbacks=[RegistroLlamadas("gemini-3.5-flash-lite")],
    )


class TestEnsayoAgente(unittest.TestCase):
    def test_ensayo_agente_compara_herramienta_esperada(self):
        ejecutor = construir_ejecutor(crear_modelo_del_ensayo(), HERRAMIENTAS)

        resultado = ejecutar_ensayo(ejecutor, CASOS[21])

        casos = resultado["casos"]
        self.assertEqual(
            [caso["herramienta_esperada"] for caso in casos],
            ["buscar_en_ley", "obtener_articulo", None],
        )
        self.assertEqual(
            [caso["herramienta_elegida"] for caso in casos], ["buscar_en_ley", "buscar_en_ley", None]
        )
        self.assertEqual([caso["coincide"] for caso in casos], [True, False, True])
        self.assertEqual(resultado["coincidencias"], 2)
        self.assertEqual(casos[0]["pasos"][0]["argumentos"], {"consulta": "obligaciones consumidores"})
        self.assertGreater(casos[0]["pasos"][0]["caracteres_observacion"], 0)
        self.assertEqual(casos[2]["pasos"], [])
        self.assertEqual(casos[2]["respuesta"], "Respondo consultas sobre la Ley REP.")
        for caso, llamadas in zip(casos, (2, 2, 1), strict=True):
            with self.subTest(consulta=caso["consulta"]):
                self.assertEqual(caso["llamadas_esperadas"], llamadas)
                self.assertEqual(caso["llamadas_registradas"], llamadas)
                self.assertEqual(caso["consumo"]["tokens_total"], 3_000 * llamadas)
        self.assertEqual(resultado["consumo_total"]["respuestas_con_costo"], 5)
        self.assertEqual(resultado["consumo_total"]["tokens_total"], 15_000)
        # 5 x (1.000 x 0,30 + 2.000 x 2,50) / 1.000.000
        self.assertEqual(resultado["consumo_total"]["costo_conocido_usd"], "0.0265")


class TestMain(unittest.TestCase):
    def setUp(self):
        self.directorio = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.cargar = self.enterContext(patch(f"{ENSAYO}.load_dotenv"))
        self.enterContext(patch(f"{ENSAYO}.logging.basicConfig"))

    def test_main_guarda_la_evidencia_del_bloque(self):
        salida = self.directorio / "evidencias" / "ensayo.json"
        texto = io.StringIO()

        with (
            patch("sys.argv", ["ensayo", "--bloque", "21", "--salida", str(salida)]),
            patch.dict(os.environ, {"GEMINI_API_KEY": "clave-ficticia"}, clear=True),
            patch(f"{ENSAYO}.crear_modelo", return_value=crear_modelo_del_ensayo()),
            redirect_stdout(texto),
        ):
            main()

        evidencia = json.loads(salida.read_text(encoding="utf-8"))
        self.assertEqual(evidencia["bloque"], 21)
        self.assertEqual(evidencia["modelo"], "gemini-3.5-flash-lite")
        self.assertEqual(evidencia["coincidencias"], 2)
        self.assertEqual(len(evidencia["casos"]), 3)
        self.assertIn("NO coincide: buscar_en_ley", texto.getvalue())

    def test_main_no_sobrescribe_una_evidencia_anterior(self):
        salida = self.directorio / "ensayo.json"
        salida.write_text("original")

        with (
            patch("sys.argv", ["ensayo", "--bloque", "21", "--salida", str(salida)]),
            patch(f"{ENSAYO}.crear_modelo") as crear,
            redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            main()

        self.assertEqual(salida.read_text(), "original")
        self.cargar.assert_not_called()
        crear.assert_not_called()

    def test_main_sin_clave_no_crea_el_modelo(self):
        errores = io.StringIO()

        with (
            patch("sys.argv", ["ensayo", "--bloque", "21", "--salida", str(self.directorio / "x")]),
            patch.dict(os.environ, {}, clear=True),
            patch(f"{ENSAYO}.crear_modelo") as crear,
            redirect_stderr(errores),
            self.assertRaises(SystemExit),
        ):
            main()

        self.assertIn("Falta configurar GEMINI_API_KEY", errores.getvalue())
        crear.assert_not_called()
        self.assertFalse((self.directorio / "x").exists())
