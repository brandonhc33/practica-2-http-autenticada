"""Ninguna acción se aplica sin un True explícito sobre lo que se revisó."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from src.gobernanza.prompts import (
    RUTA_ACTIVO,
    RUTA_PROMPTS,
    RegistroDePrompts,
    guardar_json,
    leer_activo,
)
from src.gobernanza.supervision import (
    Acciones,
    abrir_guardado,
    construir_grafo,
    detectar_datos_sensibles,
    hilos_pendientes,
    pendiente,
    proponer,
    registrar_decision,
    resolver,
)


class TestSupervision(unittest.TestCase):
    def setUp(self):
        self.raiz = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.prompts, self.activo = self.raiz / "prompts.json", self.raiz / "activo.json"
        shutil.copy(RUTA_PROMPTS, self.prompts)
        self.versiones = RegistroDePrompts.cargar(self.prompts).versiones
        self.base, self.nueva = self.versiones[0].huella, self.versiones[1].huella
        guardar_json(self.activo, {"huella": self.base})
        self.acciones = Acciones(self.prompts, self.activo, self.raiz)
        self.grafo = construir_grafo(self.acciones, InMemorySaver())

    def proponer_prompt(self) -> str:
        return proponer(
            self.grafo, self.acciones, "activar_prompt", {"huella": self.nueva, "base": self.base}
        )

    def huella_activa(self) -> str:
        return leer_activo(self.activo)["huella"]

    def test_se_pausa_antes_de_aplicar(self):
        config: Any = {"configurable": {"thread_id": "directo"}}
        resultado = self.grafo.invoke(
            {"accion": "activar_prompt", "objeto": {"huella": self.nueva, "base": self.base},
             "huella": self.nueva, "aprobado": False, "resultado": ""}, config=config,
        )
        self.assertIn("__interrupt__", resultado)
        self.assertEqual(self.huella_activa(), self.base)

    def test_aprobar_activa_y_deja_autorizacion(self):
        hilo = self.proponer_prompt()
        self.assertEqual(cast(dict, pendiente(self.grafo, hilo))["huella"], self.nueva)
        self.assertIn("activada", resolver(self.grafo, hilo, True, self.nueva))
        datos = leer_activo(self.activo)
        self.assertEqual((datos["huella"], datos["anterior"], datos["autorizacion"]),
                         (self.nueva, self.base, hilo))

    def test_rechazar_mantiene_la_anterior(self):
        hilo = self.proponer_prompt()
        self.assertIn("rechazada", resolver(self.grafo, hilo, False, self.nueva))
        self.assertEqual(self.huella_activa(), self.base)

    def test_solo_un_booleano_resuelve_y_un_texto_no_aprueba(self):
        hilo = self.proponer_prompt()
        for valor in ("no", "si", 1, None):
            with self.subTest(valor), self.assertRaises(TypeError):
                resolver(self.grafo, hilo, cast(Any, valor), self.nueva)
        # Incluso si alguien reanuda el grafo directamente con un texto.
        config: Any = {"configurable": {"thread_id": hilo}}
        final = self.grafo.invoke(Command(resume="no"), config=config)
        self.assertFalse(final["aprobado"])
        self.assertEqual(self.huella_activa(), self.base)

    def test_un_hilo_resuelto_o_inexistente_no_se_puede_volver_a_decidir(self):
        hilo = self.proponer_prompt()
        resolver(self.grafo, hilo, False, self.nueva)
        for h in (hilo, "no-existe"):
            with self.subTest(h), self.assertRaises(ValueError):
                resolver(self.grafo, h, True, self.nueva)
        self.assertEqual(self.huella_activa(), self.base)

    def test_la_huella_revisada_debe_ser_la_pendiente(self):
        hilo = self.proponer_prompt()
        with self.assertRaises(ValueError):
            resolver(self.grafo, hilo, True, self.base)
        self.assertIsNotNone(pendiente(self.grafo, hilo))

    def test_si_cambia_la_base_comparada_no_se_aplica(self):
        registro = RegistroDePrompts.cargar(self.prompts)
        otra = registro.registrar("rag_ley_rep", "otro sistema", "{contexto}{pregunta}", "x",
                                  "2026-11-24", "otra")
        registro.guardar(self.prompts)
        hilo = self.proponer_prompt()
        guardar_json(self.activo, {"huella": otra.huella})
        self.assertIn("no aplicada", resolver(self.grafo, hilo, True, self.nueva))
        self.assertEqual(self.huella_activa(), otra.huella)

    def test_no_se_propone_lo_activo_lo_inexistente_ni_otra_accion(self):
        for accion, objeto in (
            ("activar_prompt", {"huella": self.base, "base": self.base}),
            ("activar_prompt", {"huella": "000000000000", "base": self.base}),
            ("borrar_todo", {}),
        ):
            with self.subTest(accion), self.assertRaises(ValueError):
                proponer(self.grafo, self.acciones, accion, objeto)

    def test_la_pausa_sobrevive_a_otro_proceso(self):
        ruta = self.raiz / "guardado" / "a.sqlite"
        primero = abrir_guardado(ruta)
        hilo = proponer(construir_grafo(self.acciones, primero), self.acciones, "activar_prompt",
                        {"huella": self.nueva, "base": self.base})
        primero.conn.close()
        segundo = abrir_guardado(ruta)
        self.addCleanup(segundo.conn.close)
        grafo = construir_grafo(self.acciones, segundo)
        self.assertEqual(hilos_pendientes(segundo, grafo), [hilo])
        self.assertIn("activada", resolver(grafo, hilo, True, self.nueva))
        self.assertEqual(hilos_pendientes(segundo, grafo), [])

    def test_la_decision_queda_registrada(self):
        ruta = self.raiz / "decisiones.jsonl"
        hilo = self.proponer_prompt()
        resolver(self.grafo, hilo, False, self.nueva, lambda d: registrar_decision(d, ruta))
        decision = json.loads(ruta.read_text(encoding="utf-8"))
        self.assertEqual((decision["hilo"], decision["aprobado"]), (hilo, False))

    def archivo(self, texto: str) -> dict[str, str]:
        origen = self.raiz / "output" / "x.jsonl"
        origen.parent.mkdir(exist_ok=True)
        origen.write_text(texto, encoding="utf-8")
        return {"origen": "output/x.jsonl", "destino": "docs/evidencias/b/x.jsonl"}

    def test_publicar_evidencia_copia_solo_si_se_aprueba(self):
        objeto = self.archivo('{"evento": "consulta_recibida"}\n')
        destino = self.raiz / objeto["destino"]
        for aprobar in (False, True):
            hilo = proponer(self.grafo, self.acciones, "publicar_evidencia", objeto)
            huella = cast(dict, pendiente(self.grafo, hilo))["huella"]
            self.assertFalse(destino.exists())
            resolver(self.grafo, hilo, aprobar, huella)
            self.assertEqual(destino.exists(), aprobar)
        with self.assertRaises(ValueError):
            proponer(self.grafo, self.acciones, "publicar_evidencia", objeto)

    def test_archivo_cambiado_despues_de_revisar_no_se_publica(self):
        objeto = self.archivo("revisado")
        hilo = proponer(self.grafo, self.acciones, "publicar_evidencia", objeto)
        huella = cast(dict, pendiente(self.grafo, hilo))["huella"]
        self.archivo("cambiado")
        self.assertIn("el objeto cambió", resolver(self.grafo, hilo, True, huella))
        self.assertFalse((self.raiz / objeto["destino"]).exists())

    def test_datos_sensibles_y_rutas_externas_no_se_proponen(self):
        for texto in ("ana.perez@example.com", "12.345.678-9", "+56 9 1234 5678", "AIza" + "x" * 30):
            with self.subTest(texto), self.assertRaises(ValueError) as error:
                proponer(self.grafo, self.acciones, "publicar_evidencia", self.archivo(texto))
            self.assertNotIn(texto, str(error.exception))
        normal = self.archivo("texto")
        for cambio in ({"origen": "../fuera"}, {"destino": "docs/x"}, {"destino": "/tmp/x"}):
            with self.subTest(cambio), self.assertRaises(ValueError):
                proponer(self.grafo, self.acciones, "publicar_evidencia", {**normal, **cambio})

    def test_un_evento_normal_no_parece_dato_sensible(self):
        self.assertEqual(detectar_datos_sensibles(
            '{"ts": "2026-11-24T22:25:02.724+00:00", "trace_id": "trace-b9a571881b914c438b9ef2e86ec2e627",'
            ' "pregunta_len": 59, "costo_usd": "0.000108"}'), {})

    def test_las_pruebas_no_cambian_el_prompt_del_proyecto(self):
        self.assertNotEqual(self.activo, RUTA_ACTIVO)


if __name__ == "__main__":
    unittest.main()
