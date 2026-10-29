"""Políticas, esperas y agotamiento con un reloj virtual, sin demoras reales."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import Mock, call, patch

from src.errores_cliente import (
    ErrorAutenticacion,
    ErrorPeticion,
    ErrorRespuesta,
    ErrorTemporalProveedor,
    ErrorTimeoutLectura,
    ReintentosAgotados,
)
from src.reintentos import SIN_REINTENTOS, PoliticaReintento, con_reintento, parsear_retry_after


class ReintentosTests(unittest.TestCase):
    def setUp(self):
        self.tiempo = 0.0
        self.enterContext(patch("src.reintentos.monotonic", side_effect=lambda: self.tiempo))
        self.esperar = self.enterContext(patch("src.reintentos.sleep", side_effect=self.avanzar))
        self.azar = self.enterContext(patch("src.reintentos.uniform", return_value=0.25))
        self.logger = self.enterContext(patch("src.reintentos.logger"))

    def avanzar(self, segundos):
        self.tiempo += segundos

    def test_recuperacion_respeta_backoff_jitter_y_presupuesto_restante(self):
        operacion = Mock(
            side_effect=[ErrorTemporalProveedor("429"), ErrorTemporalProveedor("503"), 42]
        )
        self.assertEqual(con_reintento(operacion), 42)
        self.assertEqual(operacion.call_args_list, [call(90.0), call(88.75), call(86.5)])
        self.assertEqual(self.esperar.call_args_list, [call(1.25), call(2.25)])
        self.assertEqual(self.logger.info.call_count, 3)
        self.assertEqual(self.logger.warning.call_count, 2)

    def test_exito_inicial_no_espera(self):
        operacion = Mock(return_value={"respuesta": "ok"})
        self.assertEqual(con_reintento(operacion), {"respuesta": "ok"})
        operacion.assert_called_once()
        self.esperar.assert_not_called()

    def test_agotamiento_conserva_ultima_causa_sin_esperar_despues_del_ultimo(self):
        error = ErrorTemporalProveedor("HTTP 503", codigo_http=503)
        operacion = Mock(side_effect=error)
        with self.assertRaises(ReintentosAgotados) as resultado:
            con_reintento(operacion)
        self.assertEqual(operacion.call_count, 3)
        self.assertEqual(self.esperar.call_count, 2)
        self.assertEqual(resultado.exception.intentos, 3)
        self.assertIs(resultado.exception.ultimo_error, error)
        self.assertEqual(resultado.exception.codigo_http, 503)
        self.assertFalse(resultado.exception.presupuesto_agotado)

    def test_errores_permanentes_y_cancelacion_se_propagan_sin_reintentar(self):
        for error in (
            ErrorAutenticacion("clave"),
            ErrorPeticion("petición"),
            ErrorRespuesta("JSON"),
            ValueError("error inesperado"),
            KeyboardInterrupt(),
        ):
            with self.subTest(error=type(error).__name__):
                operacion = Mock(side_effect=error)
                with self.assertRaises(type(error)) as resultado:
                    con_reintento(operacion)
                self.assertIs(resultado.exception, error)
                operacion.assert_called_once()
        self.esperar.assert_not_called()

    def test_timeout_lectura_solo_se_reintenta_si_la_politica_lo_habilita(self):
        error = ErrorTimeoutLectura("Consumo desconocido")
        operacion = Mock(side_effect=[error, "ok"])
        with self.assertRaises(ErrorTimeoutLectura):
            con_reintento(operacion)
        operacion.assert_called_once()
        self.esperar.assert_not_called()
        self.assertEqual(
            con_reintento(
                Mock(side_effect=[error, "ok"]), PoliticaReintento(reintentar_lectura=True)
            ),
            "ok",
        )

    def test_sin_reintentos_conserva_el_error_original(self):
        error = ErrorTemporalProveedor("429", codigo_http=429)
        operacion = Mock(side_effect=error)
        with self.assertRaises(ErrorTemporalProveedor) as resultado:
            con_reintento(operacion, SIN_REINTENTOS)
        self.assertIs(resultado.exception, error)
        operacion.assert_called_once()
        self.esperar.assert_not_called()

    def test_retry_after_se_respeta_como_minimo_y_conserva_jitter(self):
        for retry_after, pausa in ((0, 1.25), (1, 1.25), (12, 12.25)):
            with self.subTest(retry_after=retry_after):
                self.esperar.reset_mock()
                operacion = Mock(
                    side_effect=[ErrorTemporalProveedor("429", retry_after=retry_after), "ok"]
                )
                self.assertEqual(con_reintento(operacion), "ok")
                self.esperar.assert_called_once_with(pausa)

    def test_retry_after_fuera_del_presupuesto_no_se_acorta_ni_se_espera(self):
        operacion = Mock(side_effect=ErrorTemporalProveedor("429", retry_after=100))
        with self.assertRaises(ReintentosAgotados) as resultado:
            con_reintento(operacion)
        self.assertTrue(resultado.exception.presupuesto_agotado)
        self.assertEqual(resultado.exception.intentos, 1)
        operacion.assert_called_once()
        self.esperar.assert_not_called()

    def test_pausa_con_jitter_debe_caber_en_el_presupuesto(self):
        for retry_after, presupuesto in ((None, 1.125), (None, 1.25), (12, 12.125), (12, 12.25)):
            with self.subTest(retry_after=retry_after, presupuesto=presupuesto):
                error = ErrorTemporalProveedor("503", retry_after=retry_after)
                operacion = Mock(side_effect=error)
                politica = PoliticaReintento(presupuesto_segundos=presupuesto)
                with self.assertRaises(ReintentosAgotados) as resultado:
                    con_reintento(operacion, politica)
                self.assertTrue(resultado.exception.presupuesto_agotado)
                self.assertEqual(resultado.exception.intentos, 1)
                self.assertIs(resultado.exception.ultimo_error, error)
                operacion.assert_called_once()
                self.esperar.assert_not_called()

    def test_presupuesto_incluye_duracion_de_peticion(self):
        def fallar(restante):
            self.assertEqual(restante, 5)
            self.avanzar(4)
            raise ErrorTemporalProveedor("503")

        with self.assertRaises(ReintentosAgotados) as resultado:
            con_reintento(fallar, PoliticaReintento(presupuesto_segundos=5))
        self.assertTrue(resultado.exception.presupuesto_agotado)
        self.esperar.assert_not_called()

    def test_no_inicia_otra_peticion_si_la_espera_sobrepasa_el_presupuesto(self):
        self.esperar.side_effect = lambda _: self.avanzar(100)
        operacion = Mock(side_effect=ErrorTemporalProveedor("503"))
        with self.assertRaises(ReintentosAgotados) as resultado:
            con_reintento(operacion)
        self.assertTrue(resultado.exception.presupuesto_agotado)
        self.assertEqual(resultado.exception.intentos, 1)
        operacion.assert_called_once()

    def test_espera_exponencial_limita_la_base_y_conserva_jitter(self):
        operacion = Mock(side_effect=[ErrorTemporalProveedor("503")] * 4 + ["ok"])
        politica = PoliticaReintento(intentos=5, espera_inicial=4, espera_maxima=5, jitter=2)
        self.azar.return_value = 1
        self.assertEqual(con_reintento(operacion, politica), "ok")
        self.assertEqual(self.esperar.call_args_list, [call(5), call(6), call(6), call(6)])

    def test_timeout_se_reduce_para_ajustarse_al_tiempo_restante(self):
        politica = PoliticaReintento()
        self.assertEqual(politica.timeout(90), (10, 60))
        self.assertEqual(politica.timeout(35), (5, 30))

    def test_politica_rechaza_limites_invalidos(self):
        casos = (
            {"intentos": 0},
            {"intentos": True},
            {"intentos": 1.5},
            {"presupuesto_segundos": 0},
            {"presupuesto_segundos": float("inf")},
            {"espera_inicial": -1},
            {"jitter": float("nan")},
            {"espera_maxima": -1},
            {"timeout_conexion": 0},
            {"timeout_lectura": -1},
            {"reintentar_lectura": 1},
        )
        for cambios in casos:
            with self.subTest(cambios=cambios), self.assertRaises(ValueError):
                replace(PoliticaReintento(), **cambios)


class RetryAfterTests(unittest.TestCase):
    def test_segundos_y_fecha_http_incluida_fecha_pasada(self):
        ahora = datetime(2026, 10, 23, tzinfo=UTC)
        self.assertEqual(parsear_retry_after(" 12 "), 12)
        self.assertEqual(parsear_retry_after("0"), 0)
        self.assertEqual(
            parsear_retry_after(format_datetime(ahora + timedelta(seconds=20)), ahora=ahora), 20
        )
        self.assertEqual(
            parsear_retry_after(format_datetime(ahora - timedelta(seconds=20)), ahora=ahora), 0
        )

    def test_encabezados_invalidos_no_rompen_el_cliente(self):
        for valor in (None, "", "mañana", "-3", "1.5", "NaN", "inf", {}):
            with self.subTest(valor=valor):
                self.assertIsNone(parsear_retry_after(valor))

    def test_segundos_enormes_conservan_la_espera_minima_del_proveedor(self):
        self.assertEqual(parsear_retry_after("9" * 500), float("inf"))
