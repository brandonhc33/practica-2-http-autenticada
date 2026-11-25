"""Una norma o una respuesta solo se usa después de una decisión sobre su contenido."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from src.gobernanza.prompts import guardar_json, leer_activo
from src.gobernanza.supervision import Acciones, construir_grafo, pendiente, proponer, resolver
from src.rag.normas import NORMAS, RAIZ, leer_normas_activas, preparar_norma


class TestNormasYEntregas(unittest.TestCase):
    def setUp(self):
        self.raiz = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for norma in NORMAS.values():
            (self.raiz / norma.archivo).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(RAIZ / norma.archivo, self.raiz / norma.archivo)
        self.activas = self.raiz / "activas.json"
        huella = preparar_norma("ley-20920", self.raiz)[1]["huella"]
        guardar_json(self.activas, {"normas": {"ley-20920": {"huella": huella}}})
        self.acciones = Acciones(raiz=self.raiz, ruta_normas=self.activas)
        self.grafo = construir_grafo(self.acciones, InMemorySaver())
        self.borrador = "output/servicio/borradores/trace-1.json"

    def guardar_borrador(self, **cambios: Any):
        guardar_json(self.raiz / self.borrador, {
            "trace_id": "trace-1", "estado": "ok", "pregunta": "¿Qué es un envase?",
            "respuesta": "Un producto [1].\n\nFuentes:\n[1] DS 12/2020, Artículo 2",
            "huella_prompt": leer_activo()["huella"], **cambios,
        })

    def decidir(self, accion: str, objeto: dict[str, str], aprobar: bool) -> str:
        hilo = proponer(self.grafo, self.acciones, accion, objeto)
        espera = pendiente(self.grafo, hilo)
        assert espera is not None
        return resolver(self.grafo, hilo, aprobar, espera["huella"])

    def entregadas(self) -> list[Path]:
        return list(self.raiz.glob("output/servicio/entregadas/*"))

    def test_activar_una_norma_necesita_aprobacion(self):
        objeto = {"norma": "ds-12-2020"}
        self.assertIn("rechazada", self.decidir("activar_norma", objeto, False))
        self.assertEqual(set(leer_normas_activas(self.activas)), {"ley-20920"})
        self.assertIn("activada", self.decidir("activar_norma", objeto, True))
        activa = leer_normas_activas(self.activas)["ds-12-2020"]
        self.assertTrue(activa["autorizacion"].startswith("activar_norma-"))
        with self.assertRaisesRegex(ValueError, "ya está activa"):
            proponer(self.grafo, self.acciones, "activar_norma", objeto)

    def test_si_el_texto_cambia_despues_de_revisar_no_se_activa(self):
        hilo = proponer(self.grafo, self.acciones, "activar_norma", {"norma": "ds-12-2020"})
        espera = pendiente(self.grafo, hilo)
        assert espera is not None
        ruta = self.raiz / NORMAS["ds-12-2020"].archivo
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["fragmentos"][0]["texto"] += " Agregado."
        guardar_json(ruta, datos)
        self.assertIn("cambió", resolver(self.grafo, hilo, True, espera["huella"]))
        self.assertNotIn("ds-12-2020", leer_normas_activas(self.activas))

    def test_un_texto_nuevo_de_una_norma_activa_se_puede_aprobar(self):
        self.decidir("activar_norma", {"norma": "ds-12-2020"}, True)
        ruta = self.raiz / NORMAS["ds-12-2020"].archivo
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["fragmentos"][0]["texto"] += " Agregado."
        guardar_json(ruta, datos)
        self.assertIn("activada", self.decidir("activar_norma", {"norma": "ds-12-2020"}, True))

    def test_retirar_necesita_aprobacion_y_deja_al_menos_una(self):
        with self.assertRaisesRegex(ValueError, "única norma"):
            proponer(self.grafo, self.acciones, "retirar_norma", {"norma": "ley-20920"})
        with self.assertRaisesRegex(ValueError, "no está activa"):
            proponer(self.grafo, self.acciones, "retirar_norma", {"norma": "ds-12-2020"})
        self.decidir("activar_norma", {"norma": "ds-12-2020"}, True)
        self.assertIn("retirada", self.decidir("retirar_norma", {"norma": "ds-12-2020"}, True))
        self.assertEqual(set(leer_normas_activas(self.activas)), {"ley-20920"})

    def test_la_respuesta_solo_se_entrega_al_aprobar_y_una_vez(self):
        self.guardar_borrador()
        objeto = {"borrador": self.borrador}
        self.assertIn("rechazada", self.decidir("entregar_respuesta", objeto, False))
        self.assertEqual(self.entregadas(), [])
        self.assertIn("entregada", self.decidir("entregar_respuesta", objeto, True))
        texto = self.entregadas()[0].read_text(encoding="utf-8")
        self.assertIn("DS 12/2020, Artículo 2", texto)
        self.assertIn("Revisión: entregar_respuesta-", texto)
        with self.assertRaisesRegex(ValueError, "ya fue entregada"):
            proponer(self.grafo, self.acciones, "entregar_respuesta", objeto)

    def test_un_borrador_modificado_despues_de_revisar_no_se_entrega(self):
        self.guardar_borrador()
        hilo = proponer(
            self.grafo, self.acciones, "entregar_respuesta", {"borrador": self.borrador}
        )
        espera = pendiente(self.grafo, hilo)
        assert espera is not None
        self.guardar_borrador(respuesta="Otra respuesta [1].")
        self.assertIn("cambió", resolver(self.grafo, hilo, True, espera["huella"]))
        self.assertEqual(self.entregadas(), [])

    def test_no_se_entrega_lo_hecho_con_un_prompt_en_prueba(self):
        self.guardar_borrador(huella_prompt="0" * 12)
        with self.assertRaisesRegex(ValueError, "no está activa"):
            proponer(
                self.grafo, self.acciones, "entregar_respuesta", {"borrador": self.borrador}
            )

    def test_no_se_entrega_una_abstencion_ni_una_ruta_externa(self):
        self.guardar_borrador(estado="abstencion")
        with self.assertRaisesRegex(ValueError, "citas comprobadas"):
            proponer(
                self.grafo, self.acciones, "entregar_respuesta", {"borrador": self.borrador}
            )
        with self.assertRaisesRegex(ValueError, "dentro de"):
            proponer(self.grafo, self.acciones, "entregar_respuesta", {
                "borrador": "output/servicio/borradores/../../../activas.json",
            })
