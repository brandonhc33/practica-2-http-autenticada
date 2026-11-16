import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from langchain_core.agents import AgentAction

from src.orquestacion.supervision import (
    esperar_aprobacion,
    main,
    marcar_repeticiones_sospechosas,
    registrar_aprobacion,
    registrar_traza,
)
from tests.orquestacion.soporte_agente import PruebaAgente

SUPERVISION = "src.orquestacion.supervision"


class TestEsperarAprobacion(unittest.TestCase):
    def setUp(self):
        self.entrada = self.enterContext(patch(f"{SUPERVISION}.sys.stdin"))
        self.entrada.isatty.return_value = True
        self.esperar = self.enterContext(patch(f"{SUPERVISION}.select.select"))
        self.esperar.return_value = ([self.entrada], [], [])
        self.salida, self.errores = io.StringIO(), io.StringIO()
        self.enterContext(redirect_stdout(self.salida))
        self.enterContext(redirect_stderr(self.errores))

    def test_esperar_aprobacion_solo_acepta_s(self):
        casos = (
            ("s\n", True),
            (" S \n", True),
            ("n\n", False),
            ("si\n", False),
            ("\n", False),
            ("", False),
        )
        for texto, esperado in casos:
            with self.subTest(texto=texto):
                self.entrada.readline.return_value = texto
                self.assertEqual(esperar_aprobacion("Informe íntegro"), esperado)
        self.assertEqual(self.salida.getvalue(), "")
        self.assertIn("Informe íntegro", self.errores.getvalue())
        self.esperar.assert_called_with([self.entrada], [], [], 300)

    def test_esperar_aprobacion_sin_respuesta_no_lee(self):
        self.esperar.return_value = ([], [], [])
        self.assertFalse(esperar_aprobacion("Informe", 0.1))
        self.entrada.readline.assert_not_called()

    def test_esperar_aprobacion_rechaza_entrada_no_interactiva(self):
        self.entrada.isatty.return_value = False
        self.entrada.readline.return_value = "s\n"
        self.assertFalse(esperar_aprobacion("Informe"))
        self.esperar.assert_not_called()
        self.entrada.readline.assert_not_called()

    def test_esperar_aprobacion_rechaza_limite_no_positivo(self):
        self.assertFalse(esperar_aprobacion("Informe", 0))
        self.esperar.assert_not_called()

    def test_esperar_aprobacion_rechaza_errores_y_cancelacion(self):
        for error in (OSError("sin terminal"), ValueError("cerrada"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                self.esperar.side_effect = error
                self.assertFalse(esperar_aprobacion("Informe"))
        self.entrada.readline.assert_not_called()


class TestRegistros(PruebaAgente):
    def test_registrar_aprobacion_conserva_decisiones_y_contenido(self):
        with patch(f"{SUPERVISION}.getpass.getuser", return_value="alumno"):
            primero = registrar_aprobacion("cliente-1", "Título", "Línea 1\nLínea 2", True)
            segundo = registrar_aprobacion("cliente-2", "Otro", "No entregar", False)
        eventos = [json.loads(linea) for linea in self.aprobaciones.read_text().splitlines()]
        self.assertEqual(len(eventos), 2)
        self.assertNotEqual(primero, segundo)
        self.assertEqual(eventos[0]["id_aprobacion"], primero)
        self.assertEqual(eventos[0]["contenido"], "Línea 1\nLínea 2")
        self.assertEqual(eventos[0]["supervisor_local"], "alumno")
        self.assertEqual([e["aprobado"] for e in eventos], [True, False])
        self.assertEqual(eventos[1]["session_id"], "cliente-2")

    def test_registrar_traza_con_y_sin_intermediate_steps(self):
        accion = AgentAction(tool="obtener_articulo", tool_input={"numero": "12"}, log="")
        registrar_traza(
            "cliente-1", "Consulta\ncon salto",
            {"output": "Respuesta", "intermediate_steps": [(accion, "Artículo completo")]},
            mensajes_en_historial_antes=2,
        )
        registrar_traza(
            "cliente-2", "Consulta fallida", {"output": "Mensaje seguro"},
            error={"tipo": "ConnectionError", "mensaje": "simulado"},
        )
        eventos = [json.loads(linea) for linea in self.trazas.read_text().splitlines()]
        self.assertEqual(len(eventos), 2)
        self.assertEqual(eventos[0]["entrada"], "Consulta\ncon salto")
        self.assertEqual(eventos[0]["mensajes_en_historial_antes"], 2)
        self.assertEqual(eventos[0]["pasos"], [{
            "herramienta": "obtener_articulo",
            "argumentos": {"numero": "12"},
            "observacion": "Artículo completo",
        }])
        self.assertEqual(eventos[0]["respuesta"], "Respuesta")
        self.assertIsNone(eventos[0]["error"])
        self.assertEqual(eventos[1]["pasos"], [])
        self.assertEqual(eventos[1]["error"]["tipo"], "ConnectionError")

    def test_registros_admiten_ruta_explicita(self):
        ruta = self.directorio / "otra" / "eventos.jsonl"
        registrar_aprobacion("sesion", "Título", "Contenido", False, ruta)
        registrar_traza("sesion", "Pregunta", {"output": "Respuesta"}, ruta)
        self.assertEqual(len(ruta.read_text().splitlines()), 2)

    def test_marcar_repeticiones_separa_sesiones_y_detecta_entre_turnos(self):
        def registrar(sesion: str, *herramientas: str):
            registrar_traza(sesion, "Consulta", {
                "output": "Respuesta",
                "intermediate_steps": [
                    (AgentAction(tool=h, tool_input={}, log=""), "Observación")
                    for h in herramientas
                ],
            })

        registrar("repite", "obtener_articulo")
        registrar("otra", "buscar_en_ley")
        registrar("repite", "obtener_articulo", "obtener_articulo")
        registrar("no-repite", "buscar_en_ley", "obtener_articulo", "buscar_en_ley")
        registrar("mismo-turno", "buscar_en_ley", "buscar_en_ley")
        registrar("sin-herramientas")
        with self.assertLogs(SUPERVISION, level="WARNING"):
            sesiones = marcar_repeticiones_sospechosas()
        self.assertEqual(sesiones, ["repite", "mismo-turno"])

    def test_marcar_repeticiones_archivo_inexistente_avisa(self):
        with self.assertLogs(SUPERVISION, level="WARNING") as registros:
            self.assertEqual(marcar_repeticiones_sospechosas(), [])
        self.assertIn("No existe", registros.output[0])

    def test_main_revisa_sin_ejecutar_acciones(self):
        self.trazas.write_text("", encoding="utf-8")
        salida = io.StringIO()
        with (
            patch("sys.argv", ["supervision", "--trazas", str(self.trazas)]),
            redirect_stdout(salida),
        ):
            main()
        self.assertEqual(json.loads(salida.getvalue()), [])
