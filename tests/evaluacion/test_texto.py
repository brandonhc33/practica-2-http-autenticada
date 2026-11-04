import unittest

from src.evaluacion.texto import (
    calcular_metricas,
    comparar_antes_despues,
    procesar_texto,
    resumir_metricas,
)


class TestPipeline(unittest.TestCase):
    def test_normaliza_sin_perder_espanol_numeros_ni_negacion(self):
        self.assertEqual(procesar_texto(" ¡NIÑO, no! 30\n días. "), ["niño", "no", "30", "días"])
        self.assertEqual(procesar_texto("reciclaje/reutilización"), ["reciclaje", "reutilización"])

    def test_vacio_y_tipo_invalido(self):
        self.assertEqual(procesar_texto("¡¡¡...!!!"), [])
        with self.assertRaises(TypeError):
            procesar_texto(None)  # type: ignore[arg-type]
        for ref, resp in (("", ""), ("hola", "!!!"), ("", "hola")):
            self.assertEqual(
                calcular_metricas(ref, resp), {"precision": 0, "cobertura": 0, "f1": 0}
            )

    def test_repeticiones_se_cuentan_sin_inflar_coincidencias(self):
        metricas = calcular_metricas("el gato el gato", "el gato gato gato")
        self.assertEqual(metricas, {"precision": 0.75, "cobertura": 0.75, "f1": 0.75})

    def test_denominadores_y_f1(self):
        metricas = calcular_metricas(
            "el gato duerme en el sofá", "el gato duerme en el sillón todo el día"
        )
        self.assertAlmostEqual(metricas["precision"], 5 / 9)
        self.assertAlmostEqual(metricas["cobertura"], 5 / 6)
        self.assertAlmostEqual(metricas["f1"], 2 / 3)
        self.assertEqual(calcular_metricas("perro", "gato")["f1"], 0)

    def test_antes_despues_y_limite_semantico(self):
        self.assertEqual(
            comparar_antes_despues("El cielo es azul.", "el cielo es azul"),
            {"crudo": 0.5, "procesado": 1},
        )
        # La inversión del sujeto no cambia la bolsa de palabras: límite deliberado.
        self.assertEqual(
            calcular_metricas("el perro muerde al gato", "el gato muerde al perro")["f1"], 1
        )

    def test_resumen(self):
        self.assertEqual(resumir_metricas([])["f1_promedio"], 0)
        resultados = [calcular_metricas("gato", "gato"), calcular_metricas("gato", "perro")]
        self.assertEqual(resumir_metricas(resultados)["f1_promedio"], 0.5)
