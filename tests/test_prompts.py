"""Contratos de salida, integración HTTP y evaluación; sin llamadas reales."""

import json
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from prompts.banco import BANCO_DE_PROMPTS, NombrePrompt
from prompts.ley_rep import EJEMPLO_FRAGMENTO_REP
from prompts.test_consistencia import evaluar_intento, main, resumir
from src.agente_gemini import main as main_cliente
from src.salida_estructurada import parsear_respuesta_json
from tests.base import CasoAPI

EXPLICACION = {
    "concepto": "API",
    "explicacion": "Permite que dos aplicaciones se comuniquen.",
    "analogia": "Un mesero lleva el pedido y trae la respuesta.",
    "ejemplo": "Python consulta Gemini mediante HTTP.",
}
DIAGNOSTICO = {
    "codigo_http": 401,
    "causa_probable": "Podría faltar el Bearer token de la API local.",
    "pasos_revision": ["Revisar el encabezado Authorization."],
}
RESUMEN = {"resumen": "La API usa dos credenciales distintas.", "puntos_clave": ["No publicarlas."]}
PREPARACION_REP = {
    "consulta_interpretada": "Revisar el caso de una empresa que importa productos envasados.",
    "busquedas_sugeridas": ["Ley REP importación productos envasados"],
    "antecedentes_faltantes": ["¿Qué productos importa y en qué período?"],
}
RESUMEN_REP = {
    "id_fragmento": EJEMPLO_FRAGMENTO_REP["id_fragmento"],
    "resumen": "El extracto menciona la disminución de la generación de residuos.",
    "puntos_clave": ["Se describe un objetivo general."],
    "limites": [
        "El artículo describe el objeto de la ley; no resuelve por sí solo un caso concreto."
    ],
}
RESPUESTA_REP = {
    "estado": "respondida",
    "respuesta": "El extracto menciona disminuir la generación de residuos.",
    "citas": [
        {
            "id_fragmento": EJEMPLO_FRAGMENTO_REP["id_fragmento"],
            "cita_textual": EJEMPLO_FRAGMENTO_REP["texto"],
        }
    ],
    "antecedentes_faltantes": [],
}
SALIDAS_VALIDAS = (EXPLICACION, DIAGNOSTICO, RESUMEN, PREPARACION_REP, RESUMEN_REP, RESPUESTA_REP)


class ParseoPromptsTests(unittest.TestCase):
    def test_todos_los_contratos_aceptan_datos_y_bloques_markdown(self):
        for nombre, datos in zip(BANCO_DE_PROMPTS, SALIDAS_VALIDAS, strict=True):
            for plantilla in ("{}", "  ```json\n{}\n```  ", "\n```\n{}\n```\n"):
                with self.subTest(nombre=nombre, plantilla=plantilla):
                    texto = plantilla.format(json.dumps(datos))
                    self.assertEqual(parsear_respuesta_json(texto, nombre), datos)

    def test_rechaza_json_cortado_prosa_listas_y_contratos_incorrectos(self):
        invalidos = [
            '{"concepto":',
            'Aquí está el resultado: {"concepto": "API"}',
            "[]",
            "null",
            json.dumps({"concepto": "API"}),
            json.dumps({**EXPLICACION, "extra": "dato"}),
            json.dumps({**EXPLICACION, "explicacion": 123}),
            json.dumps({**EXPLICACION, "ejemplo": "   "}),
        ]
        for texto in invalidos:
            with self.subTest(texto=texto), self.assertRaises(ValueError):
                parsear_respuesta_json(texto, "explicar_concepto")

    def test_tipos_rangos_y_listas_se_validan_sin_conversiones_implicitas(self):
        invalidos = [
            {**DIAGNOSTICO, "codigo_http": "401"},
            {**DIAGNOSTICO, "codigo_http": True},
            {**DIAGNOSTICO, "codigo_http": 999},
            {**DIAGNOSTICO, "pasos_revision": []},
            {**DIAGNOSTICO, "pasos_revision": ["paso"] * 6},
            {**DIAGNOSTICO, "pasos_revision": [123]},
        ]
        for datos in invalidos:
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                parsear_respuesta_json(json.dumps(datos), "diagnosticar_error_http")
        sin_codigo = {**DIAGNOSTICO, "codigo_http": None}
        self.assertEqual(
            parsear_respuesta_json(json.dumps(sin_codigo), "diagnosticar_error_http"), sin_codigo
        )

    def test_respuesta_rep_admite_abstencion_y_aclaracion_con_antecedentes(self):
        casos = (
            {
                "estado": "evidencia_insuficiente",
                "respuesta": "No se proporcionaron fragmentos que respalden una respuesta.",
                "citas": [],
                "antecedentes_faltantes": [],
            },
            {
                "estado": "requiere_aclaracion",
                "respuesta": "Se necesitan antecedentes del caso para continuar.",
                "citas": [],
                "antecedentes_faltantes": ["¿Qué actividad realiza la empresa?"],
            },
        )
        for datos in casos:
            with self.subTest(estado=datos["estado"]):
                self.assertEqual(
                    parsear_respuesta_json(json.dumps(datos), "responder_ley_rep"), datos
                )

    def test_respuesta_rep_rechaza_estados_incoherentes_y_citas_sin_contrato(self):
        invalidos = (
            {**RESPUESTA_REP, "citas": []},
            {**RESPUESTA_REP, "antecedentes_faltantes": ["Falta identificar el producto."]},
            {**RESPUESTA_REP, "estado": "requiere_aclaracion"},
            {**RESPUESTA_REP, "estado": "desconocido"},
            {**RESPUESTA_REP, "citas": [{"id_fragmento": "fuente"}]},
            {**RESPUESTA_REP, "citas": [{"id_fragmento": "fuente", "cita_textual": "   "}]},
            {
                **RESPUESTA_REP,
                "citas": [{**RESPUESTA_REP["citas"][0], "url": "https://ejemplo.invalid"}],
            },
        )
        for datos in invalidos:
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                parsear_respuesta_json(json.dumps(datos), "responder_ley_rep")

    def test_preparacion_y_resumen_rep_rechazan_salida_vacia(self):
        casos: tuple[tuple[NombrePrompt, dict[str, Any]], ...] = (
            ("preparar_consulta_rep", {**PREPARACION_REP, "busquedas_sugeridas": []}),
            ("resumir_fragmento_rep", {**RESUMEN_REP, "id_fragmento": "   "}),
            ("resumir_fragmento_rep", {**RESUMEN_REP, "limites": []}),
        )
        for nombre, datos in casos:
            with self.subTest(prompt=nombre), self.assertRaises(ValueError):
                parsear_respuesta_json(json.dumps(datos), nombre)


class PromptsAPITests(CasoAPI):
    def test_consulta_estructurada_envia_sistema_y_esquema_y_devuelve_objeto_con_costo(self):
        for nombre, datos in zip(BANCO_DE_PROMPTS, SALIDAS_VALIDAS, strict=True):
            with self.subTest(prompt=nombre):
                self.post.reset_mock()
                mensaje = BANCO_DE_PROMPTS[nombre].ejemplo_usuario
                self.upstream.json.return_value["choices"] = [
                    {"message": {"content": json.dumps(datos)}, "finish_reason": "stop"}
                ]
                respuesta = self.client.post(
                    "/consultar",
                    headers=self.headers,
                    json={**self.cuerpo, "prompt": nombre, "mensaje": mensaje},
                )
                detalles = self.assertRespuesta(respuesta, 200)
                self.assertEqual(detalles["respuesta"], datos)
                self.assertEqual(detalles["uso"], self.resultado["uso"])
                self.assertEqual(detalles["costo_estimado"], self.resultado["costo_estimado"])
                self.post.assert_called_once()
                cuerpo = self.post.call_args.kwargs["json"]
                self.assertEqual(
                    cuerpo["messages"],
                    [
                        {"role": "system", "content": BANCO_DE_PROMPTS[nombre].system_instruction},
                        {"role": "user", "content": mensaje},
                    ],
                )
                self.assertEqual(cuerpo["response_format"]["type"], "json_schema")
                self.assertEqual(
                    cuerpo["response_format"]["json_schema"]["schema"],
                    BANCO_DE_PROMPTS[nombre].response_schema,
                )

    def test_salida_invalida_o_truncada_devuelve_502_sin_reintentar(self):
        for texto, finalizacion in (("{}", "stop"), (json.dumps(EXPLICACION), "length")):
            with self.subTest(finalizacion=finalizacion):
                self.post.reset_mock()
                self.upstream.json.return_value["choices"] = [
                    {"message": {"content": texto}, "finish_reason": finalizacion}
                ]
                respuesta = self.client.post(
                    "/consultar",
                    headers=self.headers,
                    json={**self.cuerpo, "prompt": "explicar_concepto"},
                )
                self.assertRespuesta(respuesta, 502)
                self.post.assert_called_once()

    def test_prompt_invalido_se_rechaza_antes_de_llamar_al_proveedor(self):
        for valor in ("otro", "", 123, [], {}):
            with self.subTest(valor=valor):
                respuesta = self.client.post(
                    "/consultar", headers=self.headers, json={**self.cuerpo, "prompt": valor}
                )
                errores = self.assertValidaciones(respuesta)
                self.assertIn("Prompt no disponible", errores["prompt"][0])
        self.post.assert_not_called()

    def test_raw_con_prompt_conserva_el_json_original_incluso_si_el_contenido_no_cumple(self):
        respuesta = self.client.post(
            "/consultar/raw",
            headers=self.headers,
            json={**self.cuerpo, "prompt": "explicar_concepto"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), self.upstream.json.return_value)
        self.assertEqual(self.post.call_args.kwargs["json"]["messages"][0]["role"], "system")
        self.get.assert_not_called()

    def test_cli_con_prompt_muestra_objeto_validado(self):
        self.upstream.json.return_value["choices"] = [
            {"message": {"content": json.dumps(EXPLICACION)}, "finish_reason": "stop"}
        ]
        with (
            patch("src.agente_gemini.load_dotenv"),
            patch(
                "sys.argv",
                [
                    "cliente",
                    "--modelo",
                    "flash",
                    "--prompt",
                    "explicar_concepto",
                    "¿Qué es una API?",
                ],
            ),
            patch("sys.stdout", new_callable=StringIO) as salida,
        ):
            main_cliente()
        self.assertEqual(json.loads(salida.getvalue())["respuesta"], EXPLICACION)
        self.assertEqual(self.post.call_args.kwargs["json"]["model"], "gemini-3.6-flash")


class ConsistenciaPromptsTests(CasoAPI):
    def test_evaluador_conserva_consumo_de_salida_invalida_y_separa_error_http(self):
        prompt = BANCO_DE_PROMPTS["explicar_concepto"]
        self.upstream.json.return_value["choices"] = [
            {"message": {"content": "{}"}, "finish_reason": "stop"}
        ]
        invalido = evaluar_intento(prompt, "gemini-3.5-flash-lite", 1)
        self.assertEqual(invalido["estado"], "error_salida")
        self.assertEqual(invalido["uso"]["entrada"], 1000)
        self.assertIsNotNone(invalido["costo_estimado"])
        self.assertEqual(invalido["respuesta_proveedor"], self.upstream.json.return_value)
        self.upstream.status_code = 429
        error = evaluar_intento(prompt, "gemini-3.5-flash-lite", 2)
        self.assertEqual(error["estado"], "error_peticion")
        self.assertIsNone(error["uso"])
        self.assertIsNone(error["costo_estimado"])
        resumen = resumir([invalido, error])[prompt.nombre]
        self.assertEqual(resumen["exitos"], 0)
        self.assertEqual(resumen["fallos_estructura"], 1)
        self.assertEqual(resumen["errores_peticion"], 1)

    def test_interrupcion_conserva_intento_sin_inventar_consumo(self):
        self.post.side_effect = KeyboardInterrupt
        registro = evaluar_intento(BANCO_DE_PROMPTS["explicar_concepto"], "modelo", 1)
        self.assertEqual(registro["estado"], "interrumpido")
        self.assertIsNone(registro["uso"])
        self.assertIsNone(registro["costo_estimado"])

    def test_script_evalua_todo_el_banco_guarda_evidencia_y_no_oculta_fallos(self):
        cantidad_prompts = len(BANCO_DE_PROMPTS)
        cantidad_intentos = cantidad_prompts * 3
        with TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "registro.json"
            with (
                patch("prompts.test_consistencia.load_dotenv"),
                patch("prompts.test_consistencia.sleep"),
                patch("sys.argv", ["evaluador", "--salida", str(ruta), "--pausa", "0"]),
                patch("sys.stdout", new_callable=StringIO),
                self.assertRaises(SystemExit) as salida,
            ):
                main()
            self.assertEqual(salida.exception.code, 1)
            registro = json.loads(ruta.read_text())
            self.assertEqual(registro["estado"], "con_fallos")
            self.assertEqual(len(registro["banco"]), cantidad_prompts)
            self.assertEqual(len(registro["intentos"]), cantidad_intentos)
            self.assertEqual(self.post.call_count, cantidad_intentos)
            for valores in registro["resumen"].values():
                self.assertEqual(valores["intentos"], 3)
                self.assertEqual(valores["exitos"], 0)
            self.assertNotIn("clave-gemini-ficticia", ruta.read_text())
            with (
                patch("sys.argv", ["evaluador", "--salida", str(ruta)]),
                patch("sys.stderr", new_callable=StringIO),
                self.assertRaises(SystemExit) as existente,
            ):
                main()
            self.assertEqual(existente.exception.code, 2)
            self.assertEqual(self.post.call_count, cantidad_intentos)
