"""El ensayo del agente compara la herramienta elegida con la esperada, sin red ni tokens."""

import io
import json
import os
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from langchain_core.messages import AIMessage

from scripts.ensayo_agente import CASOS, ejecutar_ensayo, main
from src.orquestacion.agente_con_herramientas import (
    HERRAMIENTAS,
    construir_agente_con_memoria,
    construir_ejecutor,
)
from src.orquestacion.modelo import RegistroLlamadas
from tests.orquestacion.modelo_falso import ModeloFalso, crear_modelo_falso, pedir_herramienta
from tests.orquestacion.soporte_agente import PruebaAgente

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


class TestEnsayoAgente(PruebaAgente):
    def test_ensayo_agente_compara_herramienta_esperada(self):
        ejecutor = construir_ejecutor(crear_modelo_del_ensayo(), HERRAMIENTAS)

        resultado = ejecutar_ensayo(ejecutor, CASOS[21])

        casos = resultado["casos"]
        self.assertEqual(
            [caso["herramienta_esperada"] for caso in casos],
            ["buscar_en_ley", "obtener_articulo", None],
        )
        self.assertEqual(
            [caso["herramienta_elegida"] for caso in casos],
            ["buscar_en_ley", "buscar_en_ley", None],
        )
        self.assertEqual([caso["coincide"] for caso in casos], [True, False, True])
        self.assertEqual(resultado["coincidencias"], 2)
        primer_paso = casos[0]["pasos"][0]
        self.assertEqual(primer_paso["argumentos"], {"consulta": "obligaciones consumidores"})
        self.assertEqual(primer_paso["primera_linea"], "[Artículo 34]")
        self.assertGreater(primer_paso["caracteres_observacion"], 0)
        # Sin "sesion", cada caso empieza una conversación nueva.
        self.assertEqual([caso["sesion"] for caso in casos], ["caso-1", "caso-2", "caso-3"])
        self.assertEqual([caso["mensajes_en_historial_antes"] for caso in casos], [0, 0, 0])
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

    def test_ensayo_bloque_22_mantiene_y_aisla_sesiones(self):
        modelo = crear_modelo_falso(
            [
                pedir_herramienta("obtener_articulo", numero="primero", transitorio=True),
                AIMessage(content="Trata de la certificación de recicladores de base."),
                pedir_herramienta("obtener_articulo", numero="2", transitorio=True),
                AIMessage(content="El segundo transitorio trata de la obligación de informar."),
                AIMessage(content="En esta conversación no me has preguntado por un artículo."),
            ]
        )
        agente = construir_agente_con_memoria(construir_ejecutor(modelo, HERRAMIENTAS))

        resultado = ejecutar_ensayo(agente, CASOS[22])

        casos = resultado["casos"]
        self.assertEqual(resultado["coincidencias"], 3)
        self.assertEqual(
            [caso["sesion"] for caso in casos], ["cliente-1", "cliente-1", "cliente-2"]
        )
        self.assertEqual([caso["mensajes_en_historial_antes"] for caso in casos], [0, 2, 0])
        self.assertEqual(casos[1]["pasos"][0]["primera_linea"], "[Artículo segundo transitorio]")
        # La segunda llamada del turno 2 de cliente-1 recibe el turno 1; cliente-2 no.
        self.assertIn("certificación de recicladores", str(modelo.recibidos[2]))
        self.assertNotIn("certificación de recicladores", str(modelo.recibidos[4]))

    def test_ensayo_bloque_23_contrasta_secuencia_y_decisiones(self):
        respuestas = []
        for numero in ("12", "34"):
            respuestas.extend([
                pedir_herramienta("obtener_articulo", numero=numero),
                pedir_herramienta(
                    "entregar_informe", titulo=f"Artículo {numero}", contenido=f"Ver artículo {numero}."
                ),
                AIMessage(content="Resultado de la entrega simulada."),
            ])
        agente = construir_agente_con_memoria(
            construir_ejecutor(crear_modelo_falso(respuestas), HERRAMIENTAS)
        )
        # Solo pruebas automáticas con modelo falso; el ensayo real no reemplaza la aprobación.
        with patch(
            "src.orquestacion.herramientas.esperar_aprobacion", side_effect=[True, False]
        ):
            resultado = ejecutar_ensayo(agente, CASOS[23])
        self.assertEqual(resultado["coincidencias"], 2)
        self.assertEqual(
            [caso["aprobaciones"][0]["aprobado"] for caso in resultado["casos"]], [True, False]
        )
        self.assertEqual(len(list(self.informes.glob("*.md"))), 1)
        self.assertEqual(len(self.trazas.read_text().splitlines()), 2)

    def test_ensayo_bloque_23_no_oculta_aprobacion_inesperada(self):
        modelo = crear_modelo_falso([
            pedir_herramienta("obtener_articulo", numero="12"),
            pedir_herramienta("entregar_informe", titulo="Título", contenido="Ver artículo 12."),
            AIMessage(content="No aprobado."),
        ])
        with patch("src.orquestacion.herramientas.esperar_aprobacion", return_value=False):
            resultado = ejecutar_ensayo(construir_ejecutor(modelo, HERRAMIENTAS), CASOS[23][:1])
        self.assertEqual(resultado["coincidencias"], 0)
        self.assertFalse(resultado["casos"][0]["aprobacion_coincide"])
        self.assertTrue(resultado["casos"][0]["secuencia_coincide"])


class TestMain(PruebaAgente):
    def setUp(self):
        super().setUp()
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

    def test_main_bloque_23_sin_terminal_no_consume_cuota(self):
        with (
            patch("sys.argv", ["ensayo", "--bloque", "23", "--salida", str(self.directorio / "x")]),
            patch(f"{ENSAYO}.sys.stdin.isatty", return_value=False),
            patch(f"{ENSAYO}.crear_modelo") as crear,
            redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            main()
        crear.assert_not_called()
        self.cargar.assert_not_called()
        self.assertFalse((self.directorio / "x").exists())
