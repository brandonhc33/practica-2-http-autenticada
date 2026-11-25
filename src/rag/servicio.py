"""Consulta RAG auditable: traza, filtro, citas obligatorias y errores controlados.

`src/rag/registro.py` sigue siendo el instrumento de medición del bloque 28, que guarda
contenido en un archivo local elegido por quien lo ejecuta. Este módulo es el camino de
servicio: sus eventos no contienen la pregunta, la respuesta ni los fragmentos.
"""

import logging
from time import perf_counter
from typing import Any

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from src.gobernanza.prompts import VersionPrompt
from src.observabilidad.datos_sensibles import ocultar_datos_sensibles
from src.observabilidad.inyeccion import detectar_inyeccion, filtrar_documentos
from src.observabilidad.trazas import nueva_traza, registrar_evento
from src.orquestacion.modelo import exigir_texto
from src.rag.recuperacion import (
    buscar_por_vector,
    formatear_contexto,
    revisar_citas,
    validar_consulta,
)
from src.rag.registro import consumo_generacion

SIN_CONTEXTO = "No hay fragmentos confiables para responder esta consulta."
SIN_RESPALDO = "No hay información suficiente y citada para responder esta consulta."
ERROR_CONTROLADO = "No se pudo completar la consulta. Conserva el trace_id para revisarla."


def _fuentes_publicas(fuentes: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    """Datos para citar; el texto completo queda en el índice, no en la respuesta."""
    campos = ("id_chunk", "documento", "referencia", "fuente", "version", "url")
    return [
        {"cita": n, **{c: f[c] for c in campos if c in f}} for n, f in fuentes.items()
    ]


def nombre_fuente(fuente: dict[str, Any]) -> str:
    """Norma y artículo: con más de una norma, el artículo solo no identifica la fuente."""
    return ", ".join(fuente[c] for c in ("documento", "referencia") if c in fuente)


def _lista_de_fuentes(titulo: str, fuentes: list[dict[str, Any]]) -> str:
    lineas = [
        f"[{f['cita']}] {nombre_fuente(f)} — {f.get('url', f['fuente'])}" for f in fuentes
    ]
    return "\n".join([titulo, *lineas])


def responder(
    pregunta: str,
    indice: Chroma,
    embeddings: Embeddings,
    modelo: BaseChatModel,
    nombre_modelo: str,
    prompt: VersionPrompt,
    k: int = 3,
) -> dict[str, Any]:
    """Devuelve siempre un resultado con trace_id y auditoría; no propaga excepciones.

    Solo entrega texto del modelo si cita fragmentos que existen en el contexto.
    """
    inicio = perf_counter()
    with nueva_traza() as (trace_id, auditoria):
        resultado: dict[str, Any] = {
            "trace_id": trace_id,
            "estado": "error",
            "respuesta": ERROR_CONTROLADO,
            "fuentes": [],
            "requiere_revision": False,
            "huella_prompt": prompt.huella,
            "consumo": None,
            "auditoria": auditoria,
        }
        etapa = "validacion"
        try:
            # El proveedor tampoco necesita el correo o el RUT de quien pregunta.
            pregunta, ocultados = ocultar_datos_sensibles(pregunta)
            registrar_evento(
                "consulta_recibida",
                pregunta_len=len(pregunta),
                datos_ocultados=ocultados,
                patrones_en_pregunta=len(detectar_inyeccion(pregunta)),
                k=k,
                huella_prompt=prompt.huella,
            )
            validar_consulta(pregunta, k)
            etapa = "recuperacion"
            desde = perf_counter()
            vector = embeddings.embed_query(pregunta)
            buscado = perf_counter()
            recuperados = buscar_por_vector(indice, vector, k)
            registrar_evento(
                "documentos_recuperados",
                n_documentos=len(recuperados),
                ms_embedding=round((buscado - desde) * 1000, 1),
                ms_busqueda=round((perf_counter() - buscado) * 1000, 1),
            )
            etapa = "filtro"
            limpios, descartados = filtrar_documentos(recuperados)
            # Un fragmento sospechoso no responde en silencio: queda marcado para revisión.
            resultado["requiere_revision"] = bool(descartados)
            contexto, mapa = formatear_contexto(limpios)
            fuentes = _fuentes_publicas(mapa)
            if not limpios:
                resultado.update(estado="abstencion", respuesta=SIN_CONTEXTO)
                registrar_evento("respuesta_bloqueada", motivo="sin_contexto")
            else:
                etapa = "generacion"
                desde = perf_counter()
                mensaje = modelo.invoke(
                    prompt.plantilla().invoke({"pregunta": pregunta, "contexto": contexto})
                )
                # Antes de validar el texto: una respuesta vacía también puede consumir.
                consumo = consumo_generacion(mensaje, nombre_modelo)
                resultado["consumo"] = consumo
                tokens = consumo["tokens"] or {}
                registrar_evento(
                    "consumo_llm",
                    modelo=nombre_modelo,
                    ms=round((perf_counter() - desde) * 1000, 1),
                    input_tokens=tokens.get("input_tokens"),
                    output_tokens=tokens.get("output_tokens"),
                    total_tokens=tokens.get("total_tokens"),
                    costo_usd=consumo["costo_generacion_usd"],
                )
                texto = exigir_texto(mensaje.text)
                etapa = "citas"
                revision = revisar_citas(texto, mapa)
                if revision["referencias_validas"]:
                    usadas = [f for f in fuentes if f["cita"] in revision["numeros_citados"]]
                    resultado.update(
                        estado="ok",
                        fuentes=usadas,
                        respuesta=f"{texto}\n\n{_lista_de_fuentes('Fuentes:', usadas)}",
                    )
                else:
                    resultado.update(
                        estado="abstencion",
                        fuentes=fuentes,
                        respuesta=f"{SIN_RESPALDO}\n\n"
                        + _lista_de_fuentes("Fragmentos consultados:", fuentes),
                    )
                    registrar_evento(
                        "respuesta_bloqueada",
                        motivo="sin_citas" if revision["sin_citas"] else "cita_inexistente",
                        n_citas=len(revision["numeros_citados"]),
                    )
        except Exception as error:
            resultado.update(estado="error", respuesta=ERROR_CONTROLADO, fuentes=[])
            # El mensaje puede repetir la consulta o datos del transporte: solo el tipo.
            registrar_evento(
                "consulta_con_error", nivel=logging.ERROR, etapa=etapa, tipo_error=type(error).__name__[:80]
            )
        registrar_evento(
            "respuesta_entregada",
            estado=resultado["estado"],
            respuesta_len=len(resultado["respuesta"]),
            requiere_revision=resultado["requiere_revision"],
            ms=round((perf_counter() - inicio) * 1000, 1),
        )
        return resultado
