"""Selección de modelos en consultas directas, con servicios simulados."""

import json
from io import StringIO
from unittest.mock import patch

from src.agente_gemini import main, obtener_dato_de_prueba, obtener_dato_de_prueba_raw
from tests.base import CasoAPI

MODELOS = (
    ("flash-lite", "gemini-3.5-flash-lite"),
    ("flash", "gemini-3.6-flash"),
    ("flash-3-8", "gemini-3.8-flash"),
)


class SeleccionModeloGeminiTests(CasoAPI):
    def setUp(self):
        super().setUp()
        self.cargar_entorno = self.enterContext(patch("src.agente_gemini.load_dotenv"))

    def test_comando_envia_el_modelo_elegido_y_calcula_su_costo(self):
        for alias, modelo in MODELOS:
            with (
                self.subTest(modelo=alias),
                patch("sys.argv", ["cliente", "--modelo", alias, "¿Qué es una API?"]),
                patch("sys.stdout", new_callable=StringIO) as salida,
            ):
                self.post.reset_mock()
                main()
                datos = json.loads(salida.getvalue())
                self.post.assert_called_once()
                self.assertEqual(self.post.call_args.kwargs["json"]["model"], modelo)
                self.assertEqual(
                    self.post.call_args.kwargs["json"]["messages"],
                    [{"role": "user", "content": "¿Qué es una API?"}],
                )
                self.assertEqual(datos["costo_estimado"]["modelo"], modelo)

    def test_comando_raw_selecciona_modelo_y_conserva_la_respuesta(self):
        datos = {"choices": [], "metadato_adicional": {"valor": 1}}
        self.upstream.json.return_value = datos
        for alias, modelo in MODELOS:
            with (
                self.subTest(modelo=alias),
                patch("sys.argv", ["cliente", "Hola", "--raw", "--modelo", alias]),
                patch("sys.stdout", new_callable=StringIO) as salida,
            ):
                main()
                self.assertEqual(self.post.call_args.kwargs["json"]["model"], modelo)
                self.assertEqual(json.loads(salida.getvalue()), datos)
        self.get.assert_not_called()

    def test_funciones_permiten_seleccionar_modelo_desde_python(self):
        for funcion in (obtener_dato_de_prueba, obtener_dato_de_prueba_raw):
            for alias, modelo in MODELOS:
                with self.subTest(funcion=funcion.__name__, modelo=alias):
                    self.post.reset_mock()
                    funcion("Hola", modelo=alias)
                    self.post.assert_called_once()
                    self.assertEqual(self.post.call_args.kwargs["json"]["model"], modelo)

    def test_comando_rechaza_modelo_desconocido_antes_de_cargar_credenciales(self):
        for argumentos in ([], ["--raw"]):
            with (
                self.subTest(argumentos=argumentos),
                patch("sys.argv", ["cliente", *argumentos, "--modelo", "desconocido", "Hola"]),
                patch("sys.stderr", new_callable=StringIO) as errores,
            ):
                with self.assertRaises(SystemExit) as salida:
                    main()
                self.assertEqual(salida.exception.code, 2)
                self.assertIn("desconocido", errores.getvalue())
        self.cargar_entorno.assert_not_called()
        self.post.assert_not_called()
        self.get.assert_not_called()

    def test_funciones_rechazan_modelo_desconocido_sin_consultar(self):
        for funcion in (obtener_dato_de_prueba, obtener_dato_de_prueba_raw):
            with self.subTest(funcion=funcion.__name__):
                with self.assertRaisesRegex(ValueError, "Modelo no disponible para Gemini"):
                    funcion("Hola", modelo="desconocido")
        self.cargar_entorno.assert_not_called()
        self.post.assert_not_called()
        self.get.assert_not_called()
