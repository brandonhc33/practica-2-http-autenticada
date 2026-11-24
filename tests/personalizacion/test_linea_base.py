"""La línea base separa errores del modelo y de la regla local, sin red ni cuota."""

import copy
import unittest

from langchain_core.messages import AIMessage, HumanMessage

from src.orquestacion.enrutamiento import plantilla_clasificacion
from src.personalizacion.dataset import cargar_dataset
from src.personalizacion.linea_base import (
    categorias_aceptables,
    categorias_que_llegan,
    evaluar_regla_articulos,
    medir_linea_base,
    origen_discrepancia,
    ruta_efectiva,
)
from tests.orquestacion.modelo_falso import crear_modelo_falso

USO = {"input_tokens": 100, "output_tokens": 2, "total_tokens": 102}


def respuesta(texto: str) -> AIMessage:
    return AIMessage(content=texto, usage_metadata=USO)


class TestReglas(unittest.TestCase):
    def test_ruta_efectiva_repite_la_bifurcacion_del_bloque_19(self):
        self.assertEqual(ruta_efectiva("normativa", False), "normativa")
        self.assertEqual(ruta_efectiva("resumen", True), "resumen")
        self.assertEqual(ruta_efectiva("resumen", False), "aclaracion")
        self.assertEqual(ruta_efectiva("otra cosa", True), "aclaracion")

    def test_categorias_que_llegan_a_la_ruta(self):
        self.assertEqual(categorias_que_llegan("resumen", True), ["resumen"])
        self.assertEqual(categorias_que_llegan("normativa", False), ["normativa"])
        self.assertEqual(categorias_que_llegan("aclaracion", False), ["resumen", "aclaracion"])
        self.assertEqual(categorias_que_llegan("resumen", False), [])

    def test_solo_tres_ejemplos_aceptan_otra_palabra_y_esa_palabra_llega_a_la_ruta(self):
        ejemplos = cargar_dataset()["ejemplos"]
        con_excepcion = [e["id"] for e in ejemplos if "categorias_modelo" in e]
        self.assertEqual(con_excepcion, ["a03", "a04", "a05"])
        for e in ejemplos:
            with self.subTest(e["id"]):
                salida = e["salida"]
                llegan = categorias_que_llegan(salida["ruta"], salida["articulo"] is not None)
                self.assertIn(salida["ruta"], categorias_aceptables(e))
                self.assertLessEqual(set(categorias_aceptables(e)), set(llegan))

    def test_origen_de_la_discrepancia(self):
        self.assertIsNone(origen_discrepancia(True, False))
        self.assertEqual(origen_discrepancia(False, True), "regla_local")
        self.assertEqual(origen_discrepancia(False, False), "modelo")

    def test_regla_local_sin_gemini_detecta_el_limite_de_art_sin_punto(self):
        evaluacion = evaluar_regla_articulos(cargar_dataset())
        self.assertEqual(evaluacion["total"], 24)
        self.assertEqual(evaluacion["rutas_inalcanzables"], ["r08"])
        self.assertEqual(evaluacion["articulos_correctos"], 23)


class TestMedicion(unittest.TestCase):
    def setUp(self):
        dataset = cargar_dataset()
        self.dataset = copy.deepcopy(dataset)
        # Se conserva el orden del archivo: n01, r01, r08, a01, a03.
        self.dataset["ejemplos"] = [
            e for e in dataset["ejemplos"] if e["id"] in {"n01", "r01", "r08", "a01", "a03"}
        ]

    def test_mide_formato_coherencia_y_ruta_con_el_prompt_real(self):
        modelo = crear_modelo_falso(
            [
                respuesta("Normativa."),  # n01
                respuesta("resumen"),  # r01
                respuesta("resumen"),  # r08
                respuesta("Lo siento, no puedo."),  # a01
                respuesta("resumen"),  # a03
            ]
        )
        resultado = medir_linea_base(self.dataset, modelo, "gemini-3.5-flash-lite")
        registros = {r["id"]: r for r in resultado["registros"]}
        mensaje = modelo.recibidos[0][0]
        self.assertIsInstance(mensaje, HumanMessage)
        esperado = plantilla_clasificacion.format(mensaje=self.dataset["ejemplos"][0]["consulta"])
        self.assertEqual(mensaje.content, esperado)

        self.assertFalse(registros["n01"]["formato_estricto"])
        self.assertTrue(registros["n01"]["formato_utilizable"])
        self.assertTrue(registros["n01"]["ruta_correcta"])
        # r08: el modelo acierta, pero "art 27" sin punto no lo detecta la regla local.
        self.assertTrue(registros["r08"]["modelo_coherente"])
        self.assertEqual(registros["r08"]["origen_discrepancia"], "regla_local")
        # a03: "resumen" con varios artículos termina en aclaración por diseño.
        self.assertTrue(registros["a03"]["modelo_coherente"])
        self.assertFalse(registros["a03"]["coincidencia_exacta"])
        self.assertFalse(registros["a01"]["formato_utilizable"])
        self.assertEqual(registros["a01"]["ruta_efectiva"], "aclaracion")
        self.assertTrue(registros["a01"]["ruta_correcta"])
        self.assertEqual(registros["a01"]["origen_discrepancia"], None)
        self.assertEqual(registros["n01"]["costo_usd"], "0.000035")

        resumen = resultado["resumen"]
        self.assertEqual(resumen["incumplimientos_modelo"], ["a01"])
        self.assertEqual(resumen["discrepancias_regla_local"], ["r08"])
        self.assertFalse(resumen["completa"], "Cinco respuestas no alcanzan la muestra de 20.")
        self.assertIsNone(resumen["supera_umbral"])

    def test_obedecer_la_consulta_trampa_es_un_incumplimiento_aunque_el_flujo_lo_absorba(self):
        dataset = cargar_dataset()
        dataset["ejemplos"] = [e for e in dataset["ejemplos"] if e["id"] in {"a01", "a06"}]
        modelo = crear_modelo_falso([respuesta("resumen"), respuesta("resumen")])
        resultado = medir_linea_base(dataset, modelo, "gemini-3.5-flash-lite")
        for registro in resultado["registros"]:
            with self.subTest(registro["id"]):
                self.assertTrue(registro["ruta_correcta"])
                self.assertFalse(registro["modelo_coherente"])
        self.assertEqual(resultado["resumen"]["incumplimientos_modelo"], ["a01", "a06"])

    def test_error_detiene_sin_reintentar_ni_inventar_resultados(self):
        llamadas = []

        class ModeloQueFalla:
            def invoke(self, entrada):
                llamadas.append(entrada)
                if len(llamadas) == 2:
                    raise TimeoutError("sin respuesta")
                return respuesta("normativa")

        resultado = medir_linea_base(self.dataset, ModeloQueFalla(), "gemini-3.5-flash-lite")  # type: ignore[arg-type]
        self.assertEqual(len(llamadas), 2)
        self.assertEqual(len(resultado["registros"]), 1)
        self.assertEqual(resultado["error"], {"id": "r01", "tipo_error": "TimeoutError"})
        self.assertIsNone(resultado["resumen"]["supera_umbral"])

    def test_muestra_completa_aplica_el_umbral(self):
        dataset = cargar_dataset()
        respuestas_ok = []
        for ejemplo in dataset["ejemplos"]:
            ruta = ejemplo["salida"]["ruta"]
            respuestas_ok.append(respuesta(ruta))
        for i in (0, 1, 2):
            respuestas_ok[i] = respuesta("resumen")  # tres normativas mal clasificadas
        resultado = medir_linea_base(
            dataset, crear_modelo_falso(respuestas_ok), "gemini-3.5-flash-lite"
        )
        resumen = resultado["resumen"]
        self.assertTrue(resumen["completa"])
        self.assertEqual(len(resumen["incumplimientos_modelo"]), 3)
        self.assertEqual(resumen["proporcion_incumplimiento"], 3 / 24)
        self.assertFalse(resumen["supera_umbral"], "3 de 24 es 12,5 %: no llega al 15 %.")
