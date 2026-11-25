"""El índice cambia solo lo que cambió y nunca responde a medias ni con lo no aprobado."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.gobernanza.prompts import guardar_json
from src.rag.indice_normas import (
    LOTE,
    abrir_indice_normas,
    actualizar_indice,
    leer_manifiesto,
    planificar,
)
from src.rag.normas import NORMAS, RAIZ, buscar_norma, preparar_norma
from tests.rag.soporte import EmbeddingsDePrueba


class EmbeddingsQueFallan(EmbeddingsDePrueba):
    def __init__(self, lotes_correctos: int):
        super().__init__()
        self.lotes_correctos = lotes_correctos

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.documentos >= self.lotes_correctos:
            raise ConnectionError("corte simulado")
        return super().embed_documents(texts)


class TestIndiceNormas(unittest.TestCase):
    def setUp(self):
        self.raiz = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for norma in NORMAS.values():
            (self.raiz / norma.archivo).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(RAIZ / norma.archivo, self.raiz / norma.archivo)
        self.activas = self.raiz / "activas.json"
        self.directorio = self.raiz / "indice"
        self.opciones: dict[str, Any] = {
            "modelo_embeddings": "determinista-pruebas", "dimensiones": 16,
            "ruta_activas": self.activas, "raiz": self.raiz,
        }
        self.embeddings = EmbeddingsDePrueba()
        self.activar("ley-20920")

    def activar(self, *normas: str):
        guardar_json(self.activas, {
            "normas": {n: {"huella": preparar_norma(n, self.raiz)[1]["huella"]} for n in normas},
        })

    def actualizar(self, embeddings: EmbeddingsDePrueba | None = None) -> dict[str, Any]:
        return actualizar_indice(embeddings or self.embeddings, self.directorio, **self.opciones)

    def abrir(self):
        return abrir_indice_normas(self.directorio, **self.opciones)

    def vectores(self) -> dict[str, list[float]]:
        datos = self.abrir()[0].get(include=["embeddings"])
        return {i: list(v) for i, v in zip(datos["ids"], datos["embeddings"], strict=True)}

    def cambiar_articulo(self, id_norma: str, posicion: int, campo: str, valor: str):
        ruta = self.raiz / buscar_norma(id_norma).archivo
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["fragmentos"][posicion][campo] = valor
        guardar_json(ruta, datos)

    def test_indexa_persiste_y_reutiliza(self):
        primero = self.actualizar()
        llamadas = self.embeddings.documentos
        segundo = self.actualizar()
        self.assertEqual(primero["embeddings_calculados"], 99)
        self.assertEqual((segundo["embeddings_calculados"], segundo["reutilizado"]), (0, True))
        self.assertEqual(self.embeddings.documentos, llamadas)
        self.assertEqual(len(segundo["historial"]), 1)

    def test_agregar_una_norma_conserva_los_vectores_anteriores(self):
        self.actualizar()
        antes = self.vectores()
        self.activar("ley-20920", "ds-12-2020")
        resultado = self.actualizar()
        nuevos = preparar_norma("ds-12-2020", self.raiz)[1]["fragmentos"]
        self.assertEqual(resultado["embeddings_calculados"], nuevos)
        self.assertEqual(
            resultado["cambios_por_norma"],
            {"ds-12-2020": {"agregar": nuevos}, "ley-20920": {"sin_cambios": 99}},
        )
        despues = self.vectores()
        self.assertEqual({i: despues[i] for i in antes}, antes)

    def test_retirar_una_norma_no_convierte_texto(self):
        self.activar("ley-20920", "ds-12-2020")
        self.actualizar()
        self.activar("ley-20920")
        resultado = self.actualizar()
        self.assertEqual(resultado["embeddings_calculados"], 0)
        self.assertEqual(set(self.vectores()), {
            str(c.id) for c in preparar_norma("ley-20920", self.raiz)[0]
        })

    def test_un_articulo_modificado_solo_reemplaza_sus_fragmentos(self):
        self.actualizar()
        self.cambiar_articulo("ley-20920", 0, "texto", "Artículo 1º.- Texto cambiado de prueba.")
        self.activar("ley-20920")
        resultado = self.actualizar()
        self.assertEqual(resultado["embeddings_calculados"], 1)
        self.assertEqual(resultado["cambios_por_norma"]["ley-20920"]["reemplazar"], 1)

    def test_cambiar_solo_la_fuente_no_convierte_texto(self):
        self.actualizar()
        antes = self.vectores()
        self.cambiar_articulo("ley-20920", 0, "url", "https://example.com/otra")
        self.activar("ley-20920")
        resultado = self.actualizar()
        self.assertEqual(resultado["embeddings_calculados"], 0)
        despues = self.vectores()
        self.assertEqual(set(despues), set(antes))
        # Chroma reescribe el vector con diferencias de redondeo del orden de 1e-9.
        for id_, vector in antes.items():
            self.assertTrue(all(
                abs(a - b) < 1e-6 for a, b in zip(vector, despues[id_], strict=True)
            ))

    def test_texto_distinto_al_aprobado_no_se_indexa_ni_se_abre(self):
        self.actualizar()
        self.cambiar_articulo("ley-20920", 0, "texto", "Artículo 1º.- Sin aprobar.")
        with self.assertRaisesRegex(ValueError, "no es el aprobado"):
            self.actualizar()
        with self.assertRaisesRegex(ValueError, "no es el aprobado"):
            self.abrir()

    def test_aprobar_sin_actualizar_impide_consultar(self):
        self.actualizar()
        self.activar("ley-20920", "ds-12-2020")
        with self.assertRaisesRegex(ValueError, "actualiza el índice"):
            self.abrir()

    def test_un_corte_cierra_el_indice_y_se_continua_sin_repetir(self):
        with self.assertRaises(ConnectionError):
            self.actualizar(EmbeddingsQueFallan(lotes_correctos=2))
        self.assertEqual(leer_manifiesto(self.directorio)["estado"], "en_proceso")
        with self.assertRaisesRegex(ValueError, "a medias"):
            self.abrir()
        resultado = self.actualizar()
        self.assertEqual(resultado["embeddings_calculados"], 99 - 2 * LOTE)
        self.assertEqual(
            [(h["embeddings_calculados"], h["interrumpida"]) for h in resultado["historial"]],
            [(2 * LOTE, True), (99 - 2 * LOTE, False)],
        )
        self.assertEqual(len(self.vectores()), 99)

    def test_otro_modelo_de_embeddings_no_se_mezcla(self):
        self.actualizar()
        self.opciones["modelo_embeddings"] = "otro"
        with self.assertRaisesRegex(ValueError, "otra configuración"):
            self.actualizar()
        with self.assertRaisesRegex(ValueError, "otro modelo"):
            self.abrir()

    def test_contenido_alterado_fuera_del_proceso_no_se_abre(self):
        self.actualizar()
        indice, _ = self.abrir()
        indice.delete(ids=["ley20920-articulo-1-c000"])
        with self.assertRaisesRegex(ValueError, "no coincide"):
            self.abrir()

    def test_dimensiones_incorrectas_no_completan(self):
        self.opciones["dimensiones"] = 8
        with self.assertRaisesRegex(ValueError, "dimensiones"):
            self.actualizar()
        self.assertEqual(leer_manifiesto(self.directorio)["estado"], "en_proceso")

    def test_planificar_no_crea_nada(self):
        plan = planificar(self.directorio, self.activas, self.raiz)
        self.assertEqual(plan["embeddings_por_calcular"], 99)
        self.assertFalse(self.directorio.exists())
        self.actualizar()
        plan = planificar(self.directorio, self.activas, self.raiz)
        self.assertEqual((plan["embeddings_por_calcular"], plan["tokens_aproximados"]), (0, 0))

    def test_indice_ausente_o_sin_normas(self):
        with self.assertRaisesRegex(ValueError, "Indexa primero"):
            self.abrir()
        guardar_json(self.activas, {"normas": {}})
        with self.assertRaisesRegex(ValueError, "No hay normas activas"):
            self.actualizar()

    def test_normas_activas_invalidas(self):
        for datos, mensaje in (
            ({"otra": {"huella": "x"}}, "no disponible"), ({"ley-20920": {}}, "no declara"),
        ):
            with self.subTest(mensaje=mensaje):
                guardar_json(self.activas, {"normas": datos})
                with self.assertRaisesRegex(ValueError, mensaje):
                    self.actualizar()
