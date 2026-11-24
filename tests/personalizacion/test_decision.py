"""El método del bloque 30 reproduce la lección, muestra empates y no inventa respuestas."""

import unittest

from src.personalizacion.decision import (
    CLAVES,
    Respuesta,
    analizar_sensibilidad,
    derivar_respuestas,
    escenarios_pendientes,
    estimar_costo_de_etiquetar,
    estimar_horas_faltantes,
    generar_esqueleto_decision,
    recomendar_estrategia,
)

CASO_CLASIFICADOR = {
    "informacion_cambia_seguido": False,
    "problema_de_formato_o_tono": True,
    "dataset_grande_y_de_calidad": True,
    "presupuesto_limitado_o_iterar_rapido": False,
    "necesita_multiples_variantes": False,
}
CASO_BOT = {
    "informacion_cambia_seguido": True,
    "problema_de_formato_o_tono": True,
    "dataset_grande_y_de_calidad": False,
    "presupuesto_limitado_o_iterar_rapido": True,
    "necesita_multiples_variantes": False,
}
HECHOS = {
    "cambios_fuentes_ultimos_90_dias": {"valor": 0, "evidencia": "Una versión."},
    "intentos_entrenamiento_disponibles": {"valor": 0, "evidencia": "Sin tuning."},
    "variantes_necesarias": {"valor": 1, "evidencia": "Un flujo."},
}


def linea_base(incumplen: int, muestra: int = 24, completa: bool = True) -> dict:
    proporcion = incumplen / muestra
    return {
        "incumplimientos_modelo": [f"x{i}" for i in range(incumplen)],
        "muestra_modelo": muestra,
        "proporcion_incumplimiento": proporcion,
        "supera_umbral": (proporcion >= 0.15) if completa else None,
    }


class TestMetodo(unittest.TestCase):
    def test_reproduce_los_dos_casos_de_la_leccion(self):
        self.assertEqual(
            recomendar_estrategia(CASO_CLASIFICADOR),
            ({"RAG": 0, "Fine-tuning completo": 3, "PEFT": 3}, ["Fine-tuning completo", "PEFT"]),
        )
        self.assertEqual(
            recomendar_estrategia(CASO_BOT),
            ({"RAG": 5, "Fine-tuning completo": 1, "PEFT": 3}, ["RAG"]),
        )

    def test_sensibilidad_del_empate_coincide_con_la_leccion(self):
        filas = analizar_sensibilidad(CASO_CLASIFICADOR)
        self.assertEqual(
            [(f["clave"], f["ganadoras"], f["cambia"]) for f in filas],
            [
                ("informacion_cambia_seguido", ["RAG", "Fine-tuning completo", "PEFT"], True),
                ("problema_de_formato_o_tono", ["Fine-tuning completo"], True),
                ("dataset_grande_y_de_calidad", ["PEFT"], True),
                ("presupuesto_limitado_o_iterar_rapido", ["PEFT"], True),
                ("necesita_multiples_variantes", ["PEFT"], True),
            ],
        )

    def test_rechaza_textos_pendientes_y_claves_incorrectas(self):
        with self.assertRaisesRegex(TypeError, "True o False"):
            recomendar_estrategia({**CASO_BOT, "informacion_cambia_seguido": "si"})
        with self.assertRaisesRegex(ValueError, "Completa"):
            recomendar_estrategia({**CASO_BOT, "necesita_multiples_variantes": None})
        with self.assertRaisesRegex(ValueError, "faltantes"):
            recomendar_estrategia({"informacion_cambia_seguido": True})
        with self.assertRaisesRegex(ValueError, "no previstas"):
            recomendar_estrategia({**CASO_BOT, "otra": True})

    def test_escenarios_muestran_ambos_resultados_antes_de_medir(self):
        pendiente = {**CASO_BOT, "problema_de_formato_o_tono": None}
        escenarios = escenarios_pendientes(pendiente)
        self.assertEqual([e["valor"] for e in escenarios], [False, True])
        with self.assertRaisesRegex(ValueError, "exactamente una"):
            escenarios_pendientes({**pendiente, "informacion_cambia_seguido": None})

    def test_costos_de_etiquetado_de_la_leccion(self):
        horas, costo = estimar_costo_de_etiquetar(8, 5, 25)
        self.assertEqual((round(horas, 2), round(costo, 2)), (0.67, 16.67))
        base, costo_base = estimar_costo_de_etiquetar(500, 4, 20)
        revision, costo_revision = estimar_costo_de_etiquetar(500 * 0.2, 2, 20)
        self.assertEqual(round(base + revision, 2), 36.67)
        self.assertEqual(round(costo_base + costo_revision, 2), 733.33)
        faltantes = estimar_horas_faltantes(
            24,
            200,
            {
                "minutos_por_ejemplo": 5,
                "porcentaje_segunda_revision": 0.2,
                "minutos_segunda_revision": 2,
            },
        )
        self.assertEqual(faltantes["faltan"], 176)
        self.assertEqual(faltantes["horas_total"], 15.84)


class TestRespuestasDesdeEvidencia(unittest.TestCase):
    def test_sin_linea_base_completa_no_inventa_la_respuesta(self):
        for medicion in (None, linea_base(1, muestra=12, completa=False)):
            with self.subTest(medicion=medicion is not None):
                respuestas = derivar_respuestas(HECHOS, 24, 0, medicion)
                self.assertIsNone(respuestas["problema_de_formato_o_tono"].valor)

    def test_umbral_de_formato_en_quince_por_ciento(self):
        self.assertFalse(
            derivar_respuestas(HECHOS, 24, 0, linea_base(2, 20))["problema_de_formato_o_tono"].valor
        )
        self.assertTrue(
            derivar_respuestas(HECHOS, 24, 0, linea_base(3, 20))["problema_de_formato_o_tono"].valor
        )

    def test_dataset_grande_requiere_200_y_sin_contradicciones(self):
        self.assertFalse(
            derivar_respuestas(HECHOS, 199, 0, None)["dataset_grande_y_de_calidad"].valor
        )
        self.assertTrue(
            derivar_respuestas(HECHOS, 200, 0, None)["dataset_grande_y_de_calidad"].valor
        )
        self.assertFalse(
            derivar_respuestas(HECHOS, 200, 1, None)["dataset_grande_y_de_calidad"].valor
        )

    def test_hechos_del_proyecto(self):
        respuestas = derivar_respuestas(HECHOS, 24, 0, linea_base(0))
        self.assertEqual(
            {c: respuestas[c].valor for c in CLAVES},
            {
                "informacion_cambia_seguido": False,
                "problema_de_formato_o_tono": False,
                "dataset_grande_y_de_calidad": False,
                "presupuesto_limitado_o_iterar_rapido": True,
                "necesita_multiples_variantes": False,
            },
        )


class TestEsqueleto(unittest.TestCase):
    def respuestas(self, valores: dict[str, bool]) -> dict[str, Respuesta]:
        return {c: Respuesta(v, f"evidencia de {c}") for c, v in valores.items()}

    def test_cuatro_secciones_en_orden_y_empate_explicito(self):
        puntos, ganadoras = recomendar_estrategia(CASO_CLASIFICADOR)
        texto = generar_esqueleto_decision(
            "Problema.",
            self.respuestas(CASO_CLASIFICADOR),
            puntos,
            ganadoras,
            analizar_sensibilidad(CASO_CLASIFICADOR),
        )
        posiciones = [texto.index(f"## {n}.") for n in range(1, 5)]
        self.assertEqual(posiciones, sorted(posiciones))
        self.assertIn("**Empate entre: Fine-tuning completo, PEFT.**", texto)
        self.assertEqual(texto.count("[COMPLETAR"), 2)
        self.assertIn("evidencia de dataset_grande_y_de_calidad", texto)

    def test_ganador_claro_no_se_presenta_como_empate(self):
        puntos, ganadoras = recomendar_estrategia(CASO_BOT)
        texto = generar_esqueleto_decision(
            "Problema.",
            self.respuestas(CASO_BOT),
            puntos,
            ganadoras,
            analizar_sensibilidad(CASO_BOT),
        )
        self.assertIn("**Mayor puntaje: RAG.**", texto)
        self.assertNotIn("Empate", texto)
