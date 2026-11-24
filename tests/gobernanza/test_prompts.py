"""Las versiones de prompt son verificables y la activa siempre está registrada."""

import json
import tempfile
import unittest
from pathlib import Path

from langchain_core.prompts import (
    HumanMessagePromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)

from src.gobernanza.prompts import (
    NOMBRE_PROMPT,
    RegistroDePrompts,
    diff_prompts,
    guardar_json,
    huella_prompt,
    leer_activo,
    prompt_activo,
)
from src.rag.recuperacion import PROMPT_RAG


class TestPrompts(unittest.TestCase):
    def setUp(self):
        self.ruta = Path(self.enterContext(tempfile.TemporaryDirectory())) / "prompts.json"
        self.registro = RegistroDePrompts.cargar()

    def test_hay_dos_versiones_distintas_y_la_ultima_es_la_mas_reciente(self):
        versiones = self.registro.versiones
        self.assertGreaterEqual(len(versiones), 2)
        self.assertEqual(len({v.huella for v in versiones}), len(versiones))
        self.assertEqual(self.registro.ultima(NOMBRE_PROMPT), versiones[-1])
        self.assertIsNone(self.registro.ultima("otro"))

    def test_la_primera_version_es_el_prompt_real_medido_en_b28(self):
        mensajes = PROMPT_RAG.messages
        assert isinstance(mensajes[0], SystemMessagePromptTemplate)
        assert isinstance(mensajes[1], HumanMessagePromptTemplate)
        sistema, humano = (
            m.prompt.template for m in (mensajes[0], mensajes[1])
            if isinstance(m.prompt, PromptTemplate)
        )
        self.assertEqual((self.registro.versiones[0].sistema, self.registro.versiones[0].humano),
                         (sistema, humano))
        self.assertEqual(self.registro.versiones[0].modelo_probado, "gemini-3.5-flash-lite")

    def test_toda_version_probada_tiene_evidencia_y_separa_roles(self):
        raiz = Path(__file__).resolve().parents[2]
        for v in self.registro.versiones:
            with self.subTest(v.huella):
                self.assertEqual(v.modelo_probado is None, v.evidencia is None)
                if v.evidencia:
                    self.assertTrue((raiz / v.evidencia).is_file())
                mensajes = v.plantilla().invoke({"contexto": "C", "pregunta": "P"}).to_messages()
                self.assertEqual([m.type for m in mensajes], ["system", "human"])
                self.assertIn("<contexto_json>", str(mensajes[1].content))

    def test_diff_muestra_solo_la_instruccion_agregada(self):
        lineas = diff_prompts(*self.registro.versiones[:2])
        self.assertEqual(len([x for x in lineas if x.startswith("+") and not x.startswith("+++")]), 3)
        self.assertFalse([x for x in lineas if x.startswith("-") and not x.startswith("---")])

    def test_texto_alterado_o_version_repetida_se_rechaza(self):
        datos = {"versiones": [vars(v) for v in self.registro.versiones]}
        alterado = json.loads(json.dumps(datos))
        alterado["versiones"][0]["sistema"] += " "
        repetido = {"versiones": [datos["versiones"][0]] * 2}
        for caso in (alterado, repetido):
            self.ruta.write_text(json.dumps(caso), encoding="utf-8")
            with self.assertRaises(ValueError):
                RegistroDePrompts.cargar(self.ruta)

    def test_activo_no_registrado_falla_antes_de_responder(self):
        activo = self.ruta.with_name("activo.json")
        for contenido in ({"huella": "000000000000"}, {"huella": None}, {}):
            with self.subTest(contenido):
                guardar_json(activo, contenido)
                with self.assertRaises(ValueError):
                    prompt_activo(ruta_activo=activo)

    def test_guardar_y_cargar_conserva_todo(self):
        self.registro.guardar(self.ruta)
        self.assertEqual(RegistroDePrompts.cargar(self.ruta).versiones, self.registro.versiones)
        self.assertEqual([p.name for p in self.ruta.parent.iterdir()], ["prompts.json"])

    def test_la_version_activa_del_proyecto_esta_registrada(self):
        self.assertEqual(prompt_activo().huella, leer_activo()["huella"])
        self.assertEqual(prompt_activo().huella,
                         huella_prompt(prompt_activo().sistema, prompt_activo().humano))


if __name__ == "__main__":
    unittest.main()
