import unittest
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from src.orquestacion.enrutamiento import (
    buscar_fragmento,
    construir_cadena_aclaracion,
    construir_cadena_con_enrutamiento,
    construir_cadena_resumen,
    construir_paso_clasificacion,
    plantilla_aclaracion,
    plantilla_clasificacion,
    plantilla_resumen,
)


def crear_rutas_falsas() -> dict[str, MagicMock]:
    """Cada ruta es un mock: LangChain lo llama como función, por eso se usa return_value."""
    return {
        "cadena_normativa": MagicMock(return_value="respuesta normativa"),
        "cadena_resumen": MagicMock(return_value="respuesta de resumen"),
        "cadena_aclaracion": MagicMock(return_value="respuesta de aclaración"),
    }


class TestClasificacion(unittest.TestCase):
    def test_clasificacion_normaliza_antes_de_comparar(self):
        for respuesta, categoria in ((" Queja. \n", "queja"), ("NORMATIVA.", "normativa")):
            with self.subTest(respuesta=respuesta):
                modelo_falso = MagicMock(return_value=AIMessage(content=respuesta))
                paso = construir_paso_clasificacion(modelo_falso)
                self.assertEqual(paso.invoke({"mensaje": "algo salió mal"}), categoria)


class TestBuscarFragmento(unittest.TestCase):
    def test_buscar_fragmento_reconoce_formas_validas(self):
        casos = (
            ("Resume el artículo 9", "Artículo 9"),
            ("resumen del ARTICULO 12", "Artículo 12"),
            ("resume el art. 3", "Artículo 3"),
            ("Resume el artículo 3º", "Artículo 3"),
            ("Resume el artículo 9 de la Ley 20.920", "Artículo 9"),
            ("resume el artículo primero transitorio", "Artículo primero transitorio"),
            ("Resume el Artículo Tercero Transitorio", "Artículo tercero transitorio"),
        )
        for mensaje, referencia in casos:
            with self.subTest(mensaje=mensaje):
                fragmento = buscar_fragmento(mensaje)
                assert fragmento is not None
                self.assertEqual(fragmento["referencia"], referencia)

    def test_buscar_fragmento_rechaza_casos_ambiguos(self):
        for mensaje in (
            "resume la ley",
            "resume el 9",
            "resume el artículo 99",
            "resume el artículo 48 ter",
            "resume el artículo 1 transitorio",
            "resume el artículo primero",
            "resume los artículos 9 y 10",
            "resume el artículo 9 y 10",
            "resume el artículo 9, 10",
            "¿qué dice el artículo 9 sobre el artículo 37?",
        ):
            with self.subTest(mensaje=mensaje):
                self.assertIsNone(buscar_fragmento(mensaje))


class TestEnrutamiento(unittest.TestCase):
    def ejecutar(self, categoria: str, mensaje: str) -> tuple[object, dict[str, MagicMock]]:
        """Fuerza la categoría para que la prueba no dependa de cómo clasifique el modelo."""
        rutas = crear_rutas_falsas()
        clasificacion_falsa = MagicMock(return_value=categoria)
        cadena = construir_cadena_con_enrutamiento(clasificacion_falsa, **rutas)
        return cadena.invoke({"mensaje": mensaje}), rutas

    def assertSoloSeEjecuto(self, rutas: dict[str, MagicMock], nombre: str) -> None:
        for ruta, mock in rutas.items():
            self.assertEqual(mock.called, ruta == nombre, ruta)

    def test_enrutamiento_va_a_cadena_normativa(self):
        resultado, rutas = self.ejecutar("normativa", "¿Quién fija las metas?")
        self.assertEqual(resultado, "respuesta normativa")
        self.assertSoloSeEjecuto(rutas, "cadena_normativa")

    def test_enrutamiento_va_a_cadena_resumen(self):
        resultado, rutas = self.ejecutar("resumen", "Resume el artículo 9")
        self.assertEqual(resultado, "respuesta de resumen")
        self.assertSoloSeEjecuto(rutas, "cadena_resumen")

    def test_enrutamiento_usa_default_ante_categoria_desconocida(self):
        resultado, rutas = self.ejecutar("categoria_inventada", "Resume el artículo 9")
        self.assertEqual(resultado, "respuesta de aclaración")
        self.assertSoloSeEjecuto(rutas, "cadena_aclaracion")

    def test_resumen_sin_articulo_va_a_aclaracion(self):
        for mensaje in ("Resume la ley", "Resume el artículo 99"):
            with self.subTest(mensaje=mensaje):
                resultado, rutas = self.ejecutar("resumen", mensaje)
                self.assertEqual(resultado, "respuesta de aclaración")
                self.assertSoloSeEjecuto(rutas, "cadena_aclaracion")

    def test_enrutamiento_conserva_mensaje(self):
        _, rutas = self.ejecutar("normativa", "¿Quién fija las metas?")
        entrada = rutas["cadena_normativa"].call_args.args[0]
        self.assertEqual(entrada["mensaje"], "¿Quién fija las metas?")
        self.assertEqual(entrada["categoria"], "normativa")


class TestRutas(unittest.TestCase):
    def test_cada_ruta_usa_un_prompt_distinto(self):
        plantillas = (plantilla_clasificacion, plantilla_resumen, plantilla_aclaracion)
        self.assertEqual(len({plantilla.template for plantilla in plantillas}), 3)

    def test_ruta_resumen_recibe_solo_su_fragmento(self):
        modelo_falso = MagicMock(return_value=AIMessage(content="resumen"))
        cadena = construir_cadena_con_enrutamiento(
            MagicMock(return_value="resumen"),
            cadena_resumen=construir_cadena_resumen(modelo_falso),
        )

        resultado = cadena.invoke({"mensaje": "Resume el artículo 9"})

        prompt = modelo_falso.call_args.args[0].to_string()
        self.assertEqual(resultado, "resumen")
        self.assertEqual(prompt.count("[Artículo "), 1)
        self.assertIn("<fragmento>[Artículo 9]\nArtículo 9º.-", prompt)
        self.assertIn("<consulta>Resume el artículo 9</consulta>", prompt)

    def test_ruta_aclaracion_no_recibe_fragmentos(self):
        modelo_falso = MagicMock(return_value=AIMessage(content="¿Qué producto importas?"))
        cadena = construir_cadena_con_enrutamiento(
            MagicMock(return_value="aclaracion"),
            cadena_aclaracion=construir_cadena_aclaracion(modelo_falso),
        )

        resultado = cadena.invoke({"mensaje": "Resume el artículo 9"})

        prompt = modelo_falso.call_args.args[0].to_string()
        self.assertEqual(resultado, "¿Qué producto importas?")
        self.assertNotIn("<fragmento", prompt)
        self.assertNotIn("Artículo 9º.-", prompt)
