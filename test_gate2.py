"""Las cuatro pruebas del Gate 2 (BS1.1), adaptadas al servicio RAG de la Ley REP.

Uso: python -m pytest test_gate2.py -v
Por omisión usa las dos normas reales con embeddings y modelo locales: sin clave ni cuota.
Con GATE2_REAL=1 usa Gemini y el índice persistido (tres consultas).
"""

import atexit
import logging
import os
import shutil
import tempfile
from functools import cache
from pathlib import Path
from typing import Any

from servicio_rag import LOCAL, MODELO, K, copiar_proyecto, guardar_borrador
from src.gobernanza.prompts import prompt_activo
from src.rag.indice_normas import abrir_indice_normas, actualizar_indice
from src.rag.servicio import nombre_fuente, responder
from src.rag.simulado import NOMBRE_MODELO_SIMULADO, EmbeddingsDePalabras, ModeloQueCita

# Dato sensible de prueba que NUNCA debe aparecer en los logs
CORREO = "ana.perez@example.com"
PREGUNTA = "Cual es la meta de envases domiciliarios de vidrio el primer año? Mi correo es " + CORREO


# ===== SECCION ADAPTADA AL PROYECTO =====
@cache
def _carpeta() -> Path:
    carpeta = tempfile.mkdtemp(prefix="gate2-")
    atexit.register(shutil.rmtree, carpeta, ignore_errors=True)
    return Path(carpeta)


@cache
def _servicio() -> tuple[Any, ...]:
    """Índice, embeddings y modelo: simulados o reales, según GATE2_REAL."""
    if os.environ.get("GATE2_REAL") == "1":
        from scripts.rag_comun import exigir_consumo
        from src.orquestacion.modelo import crear_modelo
        from src.rag.indice import crear_embeddings

        exigir_consumo(True)
        return abrir_indice_normas()[0], crear_embeddings(), crear_modelo("flash-lite"), MODELO
    activas, acciones = copiar_proyecto(_carpeta())
    acciones.aplicar("activar_norma", {"norma": "ds-12-2020"}, "copia temporal de test_gate2")
    opciones = {**LOCAL, "ruta_activas": activas, "raiz": _carpeta()}
    embeddings = EmbeddingsDePalabras()
    actualizar_indice(embeddings, _carpeta() / "indice", **opciones)
    indice, _ = abrir_indice_normas(_carpeta() / "indice", **opciones)
    return indice, embeddings, ModeloQueCita(), NOMBRE_MODELO_SIMULADO


def ejecutar_servicio(pregunta):
    """Corre el flujo completo (indexar, recuperar y responder): (respuesta, fuentes)."""
    indice, embeddings, modelo, nombre = _servicio()
    r = responder(pregunta, indice, embeddings, modelo, nombre, prompt_activo(), K)
    # Un error controlado no es una respuesta: aquí debe fallar.
    assert r["estado"] != "error", [e for e in r["auditoria"] if "tipo_error" in e]
    return r["respuesta"], [nombre_fuente(f) for f in r["fuentes"]]


def crear_supervision() -> tuple[Any, dict[str, Any]]:
    """(app, entrada): la entrega de una respuesta a un cliente, la acción de mayor riesgo."""
    from langgraph.checkpoint.memory import InMemorySaver

    from src.gobernanza.supervision import Acciones, construir_grafo

    indice, embeddings, _, _ = _servicio()
    raiz = _carpeta()
    r = responder(
        PREGUNTA, indice, embeddings, ModeloQueCita(), NOMBRE_MODELO_SIMULADO, prompt_activo(), K
    )
    objeto = {"borrador": str(guardar_borrador(PREGUNTA, r, indice, raiz).relative_to(raiz))}
    acciones = Acciones(raiz=raiz)
    entrada = {
        "accion": "entregar_respuesta",
        "objeto": objeto,
        "huella": acciones.huella("entregar_respuesta", objeto),
        "aprobado": False,
        "resultado": "",
    }
    return construir_grafo(acciones, InMemorySaver()), entrada
# ===== FIN DE LA SECCION ADAPTADA =====


def test_1_pipeline_sin_excepciones():
    respuesta, _ = ejecutar_servicio(PREGUNTA)
    assert respuesta.strip(), "el servicio devolvio una respuesta vacia"


def test_2_respuesta_cita_fuente():
    respuesta, fuentes = ejecutar_servicio(PREGUNTA)
    assert fuentes, "el servicio no devolvio ninguna fuente"
    assert any(f in respuesta for f in fuentes), "la respuesta no menciona su fuente"


def test_3_logs_sin_contenido_crudo(caplog):
    with caplog.at_level(logging.DEBUG):
        ejecutar_servicio(PREGUNTA)
    texto_logs = " ".join(r.getMessage() + " " + str(r.__dict__) for r in caplog.records)
    assert CORREO not in texto_logs, "un dato sensible aparece en los logs"
    assert PREGUNTA not in texto_logs, "la consulta completa aparece en los logs"


def test_4_supervision_pausa_y_reanuda():
    from langgraph.types import Command

    app, entrada = crear_supervision()
    config = {"configurable": {"thread_id": "test-gate2"}}
    pausado = app.invoke(entrada, config=config)
    assert "__interrupt__" in pausado, "el grafo no se detuvo en el punto de supervision"
    final = app.invoke(Command(resume=True), config=config)
    assert "__interrupt__" not in final, "el grafo sigue pausado despues de reanudar"
    assert final["aprobado"] is True, "la decision no quedo registrada"
    # Agregado: la decisión tiene efecto, no solo queda anotada.
    assert final["resultado"].startswith("entregada"), final["resultado"]
