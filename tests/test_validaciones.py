"""Pruebas de validaciones de la API con servicios simulados."""

from unittest.mock import Mock, patch

from src.agentes import CLIENTES
from src.catalogo import AGENTES
from src.esquemas import LIMITES_CONSULTA, Resultado
from tests.base import CasoAPI


class ValidacionesTests(CasoAPI):
    def test_body_invalido_no_consulta_a_gemini(self):
        invalidos = [
            {},
            {"pregunta": "Hola"},
            {"model": "gemini-3.5-flash-lite", "messages": [{"role": "user", "content": "Hola"}]},
            {**self.cuerpo, "agente": "desconocido"},
            {**self.cuerpo, "modelo": "desconocido"},
            {**self.cuerpo, "modelo": "gemini-3.5-flash-lite"},
            {**self.cuerpo, "role": "system"},
            {**self.cuerpo, "endpoint": "https://example.com"},
        ]
        for campo in ("agente", "modelo", "mensaje"):
            invalidos.append({key: valor for key, valor in self.cuerpo.items() if key != campo})
            for valor in ("", "   ", 123, 1.5, True, None, [], {}):
                invalidos.append({**self.cuerpo, campo: valor})
        for cuerpo in invalidos:
            with self.subTest(cuerpo=cuerpo):
                respuesta = self.client.post("/consultar", headers=self.headers, json=cuerpo)
                self.assertValidaciones(respuesta)
        self.post.assert_not_called()

    def test_campos_faltantes_y_pregunta_tienen_errores_claros(self):
        respuesta = self.client.post(
            "/consultar", headers=self.headers, json={"pregunta": "Hola, ¿cómo estás?"}
        )
        errores = self.assertValidaciones(respuesta)
        self.assertEqual(
            errores,
            {
                "agente": ["El campo es obligatorio."],
                "modelo": ["El campo es obligatorio."],
                "mensaje": ["El campo es obligatorio."],
                "pregunta": [
                    "El campo no está permitido. Envía el texto de la consulta en 'mensaje'."
                ],
            },
        )
        self.assertNotIn("input", respuesta.text)
        self.assertNotIn("Hola, ¿cómo estás?", respuesta.text)
        self.post.assert_not_called()

    def test_cada_campo_faltante_se_identifica_por_nombre(self):
        for campo in self.cuerpo:
            with self.subTest(campo=campo):
                cuerpo = {nombre: valor for nombre, valor in self.cuerpo.items() if nombre != campo}
                respuesta = self.client.post("/consultar", headers=self.headers, json=cuerpo)
                self.assertEqual(
                    self.assertValidaciones(respuesta), {campo: ["El campo es obligatorio."]}
                )
        self.post.assert_not_called()

    def test_tipo_de_campo_invalido_tiene_mensaje_en_espanol(self):
        for campo in self.cuerpo:
            for valor in (123, 1.5, True, None, [], {}):
                with self.subTest(campo=campo, valor=valor):
                    respuesta = self.client.post(
                        "/consultar", headers=self.headers, json={**self.cuerpo, campo: valor}
                    )
                    self.assertEqual(
                        self.assertValidaciones(respuesta),
                        {campo: ["Debe ser una cadena de texto."]},
                    )
        self.post.assert_not_called()

    def test_campos_vacios_y_en_blanco_se_rechazan(self):
        for campo in self.cuerpo:
            for valor in ("", "   ", "\n\t"):
                with self.subTest(campo=campo, valor=valor):
                    respuesta = self.client.post(
                        "/consultar", headers=self.headers, json={**self.cuerpo, campo: valor}
                    )
                    self.assertEqual(
                        self.assertValidaciones(respuesta),
                        {campo: ["No puede estar vacío ni contener solo espacios."]},
                    )
        self.post.assert_not_called()

    def test_codigos_de_agente_y_modelo_exigen_formato_valido(self):
        for campo in ("agente", "modelo"):
            for valor in ("Gemini", "flash lite", "gemini/flash", " gemini ", "gemini\n"):
                with self.subTest(campo=campo, valor=valor):
                    respuesta = self.client.post(
                        "/consultar", headers=self.headers, json={**self.cuerpo, campo: valor}
                    )
                    errores = self.assertValidaciones(respuesta)
                    self.assertEqual(set(errores), {campo})
                    self.assertIn("letras minúsculas", errores[campo][0])
        self.post.assert_not_called()

    def test_limites_de_longitud_se_explican_por_campo(self):
        for campo, limite in LIMITES_CONSULTA.items():
            with self.subTest(campo=campo, limite=limite):
                respuesta = self.client.post(
                    "/consultar",
                    headers=self.headers,
                    json={**self.cuerpo, campo: "a" * (limite + 1)},
                )
                self.assertEqual(
                    self.assertValidaciones(respuesta),
                    {campo: [f"No puede superar los {limite} caracteres."]},
                )
        self.post.assert_not_called()

    def test_longitudes_maximas_son_inclusivas(self):
        cuerpo = {campo: "a" * limite for campo, limite in LIMITES_CONSULTA.items()}
        # Cada á cuenta como un carácter, aunque ocupe más de un byte en UTF-8.
        cuerpo["mensaje"] = "á" * LIMITES_CONSULTA["mensaje"]
        cliente = Mock(return_value=Resultado(respuesta="Respuesta en el límite"))
        catalogo = {
            cuerpo["agente"]: {
                "clave": "GEMINI_API_KEY",
                "modelos": {cuerpo["modelo"]: "modelo-real"},
            }
        }
        with patch.dict(AGENTES, catalogo), patch.dict(CLIENTES, {cuerpo["agente"]: cliente}):
            respuesta = self.client.post("/consultar", headers=self.headers, json=cuerpo)
        detalles = self.assertRespuesta(respuesta, 200)
        self.assertEqual(
            detalles,
            {"respuesta": "Respuesta en el límite", "uso": None, "costo_estimado": None},
        )
        self.assertNotIn(cuerpo["mensaje"], respuesta.text)
        cliente.assert_called_once_with("modelo-real", cuerpo["mensaje"])
        self.post.assert_not_called()

    def test_mensaje_de_un_caracter_es_valido(self):
        respuesta = self.client.post(
            "/consultar", headers=self.headers, json={**self.cuerpo, "mensaje": "a"}
        )
        self.assertRespuesta(respuesta, 200)
        self.post.assert_called_once()

    def test_varias_validaciones_del_mismo_campo_se_agrupan(self):
        respuesta = self.client.post(
            "/consultar",
            headers=self.headers,
            json={**self.cuerpo, "modelo": "A" * (LIMITES_CONSULTA["modelo"] + 1)},
        )
        self.assertEqual(
            self.assertValidaciones(respuesta),
            {
                "modelo": [
                    "No puede superar los 64 caracteres.",
                    "Usa solo letras minúsculas, números, guiones o guiones bajos, sin espacios.",
                ]
            },
        )
        self.post.assert_not_called()

    def test_agente_y_modelo_desconocidos_indican_opciones_en_su_campo(self):
        casos = (
            ("agente", "desconocido", "Agente no disponible. Usa: gemini."),
            ("modelo", "desconocido", "Modelo no disponible para gemini. Usa: flash-lite."),
        )
        for campo, valor, mensaje in casos:
            with self.subTest(campo=campo):
                respuesta = self.client.post(
                    "/consultar", headers=self.headers, json={**self.cuerpo, campo: valor}
                )
                self.assertEqual(self.assertValidaciones(respuesta), {campo: [mensaje]})
        self.post.assert_not_called()

    def test_modelo_de_otro_agente_se_rechaza(self):
        with patch.dict(
            AGENTES, {"otro": {"clave": "OTRA_CLAVE", "modelos": {"otro-modelo": "real"}}}
        ):
            respuesta = self.client.post(
                "/consultar", headers=self.headers, json={**self.cuerpo, "modelo": "otro-modelo"}
            )
        self.assertEqual(
            self.assertValidaciones(respuesta),
            {"modelo": ["Modelo no disponible para gemini. Usa: flash-lite."]},
        )
        self.post.assert_not_called()

    def test_errores_de_distintos_campos_se_reportan_juntos(self):
        respuesta = self.client.post(
            "/consultar",
            headers=self.headers,
            json={"agente": "desconocido", "modelo": 123, "mensaje": "   ", "role": "user"},
        )
        errores = self.assertValidaciones(respuesta)
        self.assertEqual(set(errores), {"agente", "modelo", "mensaje", "role"})
        self.post.assert_not_called()

    def test_cuerpo_ausente_no_valido_o_que_no_es_objeto(self):
        for contenido in (None, b"", b"null", b"[]", b'"hola"', b"123", b"true", b"{} extra"):
            with self.subTest(contenido=contenido):
                respuesta = self.client.post(
                    "/consultar",
                    headers={**self.headers, "Content-Type": "application/json"},
                    content=contenido,
                )
                errores = self.assertValidaciones(respuesta)
                self.assertEqual(set(errores), {"cuerpo"})
        self.post.assert_not_called()

    def test_json_mal_formado_indica_como_corregirlo(self):
        respuesta = self.client.post(
            "/consultar",
            headers={**self.headers, "Content-Type": "application/json"},
            content='{"agente": "gemini",}',
        )
        self.assertEqual(
            self.assertValidaciones(respuesta),
            {
                "cuerpo": [
                    "El cuerpo debe ser un JSON válido. Revisa las comillas, las comas y las llaves."
                ]
            },
        )
        self.post.assert_not_called()
