"""Los puntajes siguen la lección y cada control citado existe en el repositorio."""

import copy
import unittest

from src.gobernanza.riesgos import (
    cargar_matriz,
    categoria_riesgo,
    esta_en_el_limite,
    evaluar_matriz,
    puntaje_riesgo,
    tabla_markdown,
    validar_matriz,
)


class TestRiesgos(unittest.TestCase):
    def setUp(self):
        self.matriz = cargar_matriz()

    def test_ejemplos_de_la_leccion(self):
        for p, i, puntaje, categoria in (
            (4, 4, 16, "CRITICO"), (3, 5, 15, "CRITICO"), (3, 3, 9, "ALTO"),
            (2, 4, 8, "MEDIO"), (3, 2, 6, "MEDIO"), (1, 1, 1, "BAJO"),
        ):
            with self.subTest((p, i)):
                self.assertEqual(puntaje_riesgo(p, i), puntaje)
                self.assertEqual(categoria_riesgo(puntaje), categoria)
                self.assertEqual(esta_en_el_limite(p, i), (p, i) != (1, 1))
        self.assertFalse(esta_en_el_limite(5, 5))

    def test_valores_que_no_son_enteros_de_1_a_5(self):
        for valor in ("4", 0, 6, 2.5, True, None):
            with self.subTest(valor), self.assertRaises(ValueError):
                puntaje_riesgo(valor, 3)  # pyright: ignore[reportArgumentType]

    def test_matriz_del_proyecto(self):
        self.assertEqual(validar_matriz(self.matriz), [])
        filas = evaluar_matriz(self.matriz)
        self.assertGreaterEqual(len(filas), 5)
        self.assertGreater(len({f["categoria"] for f in filas}), 1)
        graves = [f for f in filas if f["categoria"] in {"ALTO", "CRITICO"}]
        self.assertTrue(graves and all(f["supervision"] for f in graves))
        self.assertEqual([f["puntaje"] for f in filas], sorted((f["puntaje"] for f in filas), reverse=True))

    def test_detecta_matrices_rotas(self):
        def romper(cambio):
            copia = copy.deepcopy(self.matriz)
            cambio(copia["riesgos"])
            return validar_matriz(copia)

        casos = {
            "sin supervisión": lambda r: r[0].update(supervision=None),
            "archivo inexistente": lambda r: r[0]["mitigaciones"][0].update(archivo="no/existe.py"),
            "supervisión inexistente": lambda r: r[0]["supervision"].update(archivo="no/existe.py"),
            "texto en vez de número": lambda r: r[0].update(impacto="4"),
            "id repetido": lambda r: r[1].update(id=r[0]["id"]),
            "clave mal escrita": lambda r: r[0].update(impact=r[0].pop("impacto")),
            "sin mitigaciones": lambda r: r[0].update(mitigaciones=[]),
            "muy pocos riesgos": lambda r: r.__delitem__(slice(4, None)),
            "ninguno grave": lambda r: [x.update(probabilidad=1, impacto=1) for x in r],
        }
        for nombre, cambio in casos.items():
            with self.subTest(nombre):
                self.assertTrue(romper(cambio))

    def test_tabla(self):
        filas = evaluar_matriz(self.matriz)
        self.assertEqual(len(tabla_markdown(filas).splitlines()), len(filas) + 2)


if __name__ == "__main__":
    unittest.main()
