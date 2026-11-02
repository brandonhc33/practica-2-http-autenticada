"""Pruebas de autenticacion de la API con servicios simulados."""

from tests.base import TOKEN, CasoAPI


class AutenticacionTests(CasoAPI):
    def test_todos_los_endpoints_exigen_bearer_valido(self):
        for authorization in (None, "Bearer incorrecto", "Bearer ", f"Basic {TOKEN}"):
            headers = {} if authorization is None else {"Authorization": authorization}
            for method, endpoint in (
                ("GET", "/health"),
                ("POST", "/consultar"),
                ("POST", "/consultar/raw"),
            ):
                with self.subTest(authorization=authorization, endpoint=endpoint):
                    respuesta = self.client.request(
                        method,
                        endpoint,
                        headers=headers,
                        json=self.cuerpo if method == "POST" else None,
                    )
                    detalles = self.assertRespuesta(respuesta, 401)
                    self.assertIn("Bearer token", detalles["causa"])
                    self.assertIn("Authorization", detalles["encabezado_requerido"])
                    self.assertEqual(respuesta.headers["WWW-Authenticate"], "Bearer")
                    self.assertNotIn(TOKEN, respuesta.text)
        self.post.assert_not_called()

    def test_token_en_query_no_autentica(self):
        respuesta = self.client.get("/health", params={"token": TOKEN})
        self.assertRespuesta(respuesta, 401)
        self.post.assert_not_called()

    def test_esquema_bearer_admite_minusculas(self):
        respuesta = self.client.get("/health", headers={"Authorization": f"bearer {TOKEN}"})
        self.assertRespuesta(respuesta, 200)

    def test_token_local_no_se_envia_a_gemini(self):
        respuesta = self.client.post("/consultar", headers=self.headers, json=self.cuerpo)
        self.assertRespuesta(respuesta, 200)
        headers = self.post.call_args.kwargs["headers"]
        self.assertEqual(headers["Authorization"], "Bearer clave-gemini-ficticia")
        self.assertNotIn(TOKEN, str(self.post.call_args))
        self.assertFalse(self.post.call_args.kwargs["allow_redirects"])
        self.assertNotIn(TOKEN, respuesta.text)
        self.assertNotIn("clave-gemini-ficticia", respuesta.text)
