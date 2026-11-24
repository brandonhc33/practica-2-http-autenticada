"""Los eventos son JSON, llevan su trace_id y no aceptan contenido."""

import io
import json
import logging
import unittest
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from src.observabilidad.trazas import (
    CAMPOS,
    LARGO_MAXIMO_TEXTO,
    configurar_registro,
    huella,
    logger,
    nueva_traza,
    registrar_evento,
    trace_id_actual,
)


class TestTrazas(unittest.TestCase):
    def setUp(self):
        self.salida = io.StringIO()
        anteriores, nivel = logger.handlers, logger.level
        self.addCleanup(lambda: (setattr(logger, "handlers", anteriores), logger.setLevel(nivel)))
        configurar_registro(self.salida)

    def eventos(self):
        return [json.loads(linea) for linea in self.salida.getvalue().splitlines()]

    def test_cada_linea_es_json_con_trace_id(self):
        with nueva_traza() as (trace_id, auditoria):
            registrar_evento("consulta_recibida", pregunta_len=35, k=3)
        evento = self.eventos()[0]
        self.assertEqual(evento["trace_id"], trace_id)
        self.assertEqual((evento["evento"], evento["pregunta_len"]), ("consulta_recibida", 35))
        self.assertEqual(auditoria, [{"evento": "consulta_recibida", "trace_id": trace_id,
                                      "pregunta_len": 35, "k": 3}])

    def test_la_traza_se_cierra_aunque_falle_y_las_anidadas_se_restauran(self):
        with self.assertRaises(RuntimeError), nueva_traza():
            raise RuntimeError
        self.assertIsNone(trace_id_actual())
        with nueva_traza() as (externa, _):
            with nueva_traza() as (interna, _):
                self.assertEqual(trace_id_actual(), interna)
            self.assertEqual(trace_id_actual(), externa)

    def test_consultas_iguales_tienen_trazas_distintas_y_no_se_mezclan_entre_hilos(self):
        def consulta(_):
            with nueva_traza() as (trace_id, auditoria):
                for _ in range(20):
                    registrar_evento("contexto_filtrado", n_limpios=1, n_descartados=0)
                return trace_id, {e["trace_id"] for e in auditoria}, len(auditoria)

        with ThreadPoolExecutor(max_workers=4) as hilos:
            resultados = list(hilos.map(consulta, range(8)))
        self.assertEqual(len({r[0] for r in resultados}), 8)
        self.assertTrue(all(r[1] == {r[0]} and r[2] == 20 for r in resultados))

    def test_contenido_y_campos_no_previstos_se_rechazan_sin_repetir_el_valor(self):
        privado = "ana.perez@example.com"
        casos: tuple[dict[str, Any], ...] = (
            {"pregunta": privado},
            {"respuesta": privado},
            {"texto": privado},
            {"pregunta_len": privado},
            {"k": True},
            {"motivo": privado * 10},
        )
        for campos in casos:
            with self.subTest(list(campos)), self.assertRaises(ValueError) as error:
                registrar_evento("consulta_recibida", **campos)
            self.assertNotIn(privado, str(error.exception))
        with self.assertRaises(ValueError):
            registrar_evento("evento_inventado")
        self.assertEqual(self.salida.getvalue(), "")

    def test_ningun_campo_admitido_parece_contenido(self):
        prohibidos = {"pregunta", "respuesta", "texto", "contexto", "contenido", "mensaje", "error"}
        self.assertFalse(prohibidos & set(CAMPOS))
        self.assertLessEqual(LARGO_MAXIMO_TEXTO, 80)

    def test_excepcion_adjunta_no_llega_al_registro(self):
        try:
            raise ValueError("dato privado")
        except ValueError:
            logger.exception("consulta_con_error")
        self.assertNotIn("dato privado", self.salida.getvalue())

    def test_configurar_de_nuevo_no_duplica_lineas(self):
        configurar_registro(self.salida)
        registrar_evento("consulta_recibida", pregunta_len=1)
        self.assertEqual(len(self.eventos()), 1)
        self.assertIsNone(self.eventos()[0]["trace_id"])

    def test_los_eventos_se_propagan_para_que_las_pruebas_puedan_revisarlos(self):
        with self.assertLogs(level=logging.INFO) as capturados:
            registrar_evento("consulta_recibida", pregunta_len=1)
        self.assertEqual(capturados.records[0].getMessage(), "consulta_recibida")

    def test_huella_de_la_leccion(self):
        self.assertEqual(huella("Politica de devoluciones: 30 dias desde la compra."), "d1f000839fa5")
        self.assertEqual(huella("Politica de envios: 5 dias habiles a todo el pais."), "1b1331984c5f")


if __name__ == "__main__":
    unittest.main()
