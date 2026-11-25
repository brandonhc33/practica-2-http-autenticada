"""Acciones de alto riesgo que se pausan hasta recibir una decisión humana explícita.

Cada solicitud es un hilo propio de un grafo de LangGraph. El estado pausado se guarda
en SQLite: quien propone y quien decide pueden ser procesos distintos.
"""

import getpass
import hashlib
import json
import sqlite3
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from src.gobernanza.prompts import (
    RAIZ,
    RUTA_ACTIVO,
    RUTA_PROMPTS,
    RegistroDePrompts,
    guardar_json,
    leer_activo,
)
from src.observabilidad.datos_sensibles import detectar_datos_sensibles
from src.rag.normas import RUTA_NORMAS_ACTIVAS, leer_normas_activas, preparar_norma

DIRECTORIO_GOBERNANZA = RAIZ / "output" / "gobernanza"
RUTA_CHECKPOINTS = DIRECTORIO_GOBERNANZA / "aprobaciones.sqlite"
RUTA_DECISIONES = DIRECTORIO_GOBERNANZA / "decisiones.jsonl"
MOTIVOS = {
    "activar_prompt": "activar una versión de prompt para todas las respuestas",
    "publicar_evidencia": "copiar un archivo local a las evidencias públicas",
    "entregar_respuesta": "entregar a un cliente una respuesta sobre la normativa",
    "activar_norma": "usar una norma en todas las respuestas",
    "retirar_norma": "dejar de usar una norma en todas las respuestas",
}
BORRADORES = "output/servicio/borradores"
ENTREGADAS = "output/servicio/entregadas"


class EstadoAccion(TypedDict):
    accion: str
    objeto: dict[str, str]
    huella: str
    aprobado: bool
    resultado: str


def _ruta_dentro(raiz: Path, relativa: str, carpeta: str) -> Path:
    base = (raiz / carpeta).resolve()
    ruta = (raiz / relativa).resolve()
    if not ruta.is_relative_to(base) or ruta == base:
        raise ValueError(f"La ruta debe estar dentro de {carpeta}/.")
    return ruta


class Acciones:
    """Comprueba y aplica cada acción; las rutas se reciben para poder probarlas."""

    def __init__(
        self,
        ruta_prompts: Path = RUTA_PROMPTS,
        ruta_activo: Path = RUTA_ACTIVO,
        raiz: Path = RAIZ,
        ruta_normas: Path = RUTA_NORMAS_ACTIVAS,
    ):
        self.ruta_prompts = ruta_prompts
        self.ruta_activo = ruta_activo
        self.raiz = raiz
        self.ruta_normas = ruta_normas

    def huella(self, accion: str, objeto: dict[str, str]) -> str:
        """Identifica lo que se revisa. Se recalcula al aplicar: si cambió, no se aplica."""
        if accion == "activar_prompt":
            version = RegistroDePrompts.cargar(self.ruta_prompts).buscar(objeto["huella"])
            activa = leer_activo(self.ruta_activo)["huella"]
            if activa == version.huella:
                raise ValueError("Esa versión ya está activa.")
            # La persona revisa el diff contra esta base: si cambia, hay que revisar otra vez.
            if activa != objeto["base"]:
                raise ValueError("La versión activa ya no es la que se comparó.")
            return version.huella
        if accion == "publicar_evidencia":
            origen = _ruta_dentro(self.raiz, objeto["origen"], "output")
            destino = _ruta_dentro(self.raiz, objeto["destino"], "docs/evidencias")
            if destino.exists():
                raise ValueError("El destino ya existe: no se reemplaza evidencia anterior.")
            contenido = origen.read_bytes()
            sensibles = detectar_datos_sensibles(contenido.decode("utf-8"))
            if sensibles:
                raise ValueError(f"El archivo tiene posibles datos sensibles: {sensibles}.")
            return hashlib.sha256(contenido).hexdigest()
        if accion == "entregar_respuesta":
            borrador = _ruta_dentro(self.raiz, objeto["borrador"], BORRADORES)
            contenido = borrador.read_bytes()
            datos = json.loads(contenido)
            if datos["estado"] != "ok":
                raise ValueError("Solo se entrega una respuesta con citas comprobadas.")
            if datos["huella_prompt"] != leer_activo(self.ruta_activo)["huella"]:
                raise ValueError("El borrador usó una versión de prompt que no está activa.")
            if self._entregada(borrador).exists():
                raise ValueError("Esa respuesta ya fue entregada.")
            return hashlib.sha256(contenido).hexdigest()
        if accion == "activar_norma":
            resumen = preparar_norma(objeto["norma"], self.raiz)[1]
            activa = leer_normas_activas(self.ruta_normas).get(objeto["norma"], {}).get("huella")
            if activa == resumen["huella"]:
                raise ValueError("Esa norma ya está activa con el mismo texto.")
            return resumen["huella"]
        if accion == "retirar_norma":
            normas = leer_normas_activas(self.ruta_normas)
            if objeto["norma"] not in normas:
                raise ValueError("Esa norma no está activa.")
            if len(normas) == 1:
                raise ValueError("No se puede retirar la única norma activa.")
            return normas[objeto["norma"]]["huella"]
        raise ValueError(f"Acción no prevista: {accion}.")

    def _entregada(self, borrador: Path) -> Path:
        return self.raiz / ENTREGADAS / f"{borrador.stem}.md"

    def _entregar(self, objeto: dict[str, str], hilo: str) -> str:
        borrador = _ruta_dentro(self.raiz, objeto["borrador"], BORRADORES)
        datos = json.loads(borrador.read_text(encoding="utf-8"))
        destino = self._entregada(borrador)
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("x", encoding="utf-8") as archivo:
            archivo.write(
                f"# Respuesta revisada\n\n**Consulta:** {datos['pregunta']}\n\n"
                f"{datos['respuesta']}\n\n"
                f"Revisión: {hilo}. Traza: {datos['trace_id']}. No es asesoría legal ni una "
                "comprobación de vigencia.\n"
            )
        return f"entregada: {destino.relative_to(self.raiz)}"

    def _cambiar_normas(self, accion: str, objeto: dict[str, str], hilo: str) -> str:
        normas = leer_normas_activas(self.ruta_normas)
        norma = objeto["norma"]
        if accion == "activar_norma":
            resumen = preparar_norma(norma, self.raiz)[1]
            normas[norma] = {
                "huella": resumen["huella"],
                "version": resumen["version"],
                "autorizacion": hilo,
                "fecha": datetime.now(UTC).date().isoformat(),
            }
        else:
            del normas[norma]
        guardar_json(self.ruta_normas, {"normas": normas})
        hecho = "activada" if accion == "activar_norma" else "retirada"
        return f"{hecho}: {norma}. Falta actualizar el índice"

    def aplicar(self, accion: str, objeto: dict[str, str], hilo: str) -> str:
        if accion == "activar_prompt":
            guardar_json(self.ruta_activo, {
                "huella": objeto["huella"],
                "anterior": objeto["base"],
                "autorizacion": hilo,
                "fecha": datetime.now(UTC).date().isoformat(),
            })
            return f"activada: {objeto['huella']} reemplaza a {objeto['base']}"
        if accion == "entregar_respuesta":
            return self._entregar(objeto, hilo)
        if accion in ("activar_norma", "retirar_norma"):
            return self._cambiar_normas(accion, objeto, hilo)
        origen = _ruta_dentro(self.raiz, objeto["origen"], "output")
        destino = _ruta_dentro(self.raiz, objeto["destino"], "docs/evidencias")
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("xb") as archivo:
            archivo.write(origen.read_bytes())
        return f"publicado: {objeto['destino']}"


def construir_grafo(
    acciones: Acciones, guardado: BaseCheckpointSaver
) -> CompiledStateGraph[EstadoAccion, None, EstadoAccion, EstadoAccion]:
    # LangGraph exige que el primer parámetro de cada nodo se llame `state`.
    def supervisar(state: EstadoAccion) -> dict[str, Any]:
        # Al reanudar, este nodo se ejecuta de nuevo desde el principio: no debe tener
        # efectos antes del interrupt.
        decision = interrupt({
            "motivo": MOTIVOS[state["accion"]],
            "objeto": state["objeto"],
            "huella": state["huella"],
        })
        # Solo el booleano True aprueba: un texto como "no" es verdadero en Python.
        return {"aprobado": decision is True}

    def aplicar(state: EstadoAccion, config: RunnableConfig) -> dict[str, Any]:
        if not state["aprobado"]:
            return {"resultado": "rechazada: no se aplicó ningún cambio"}
        hilo = config.get("configurable", {})["thread_id"]
        try:
            actual = acciones.huella(state["accion"], state["objeto"])
        except (OSError, ValueError) as error:
            return {"resultado": f"no aplicada: {error}"}
        if actual != state["huella"]:
            return {"resultado": "no aplicada: el objeto cambió después de la revisión"}
        return {"resultado": acciones.aplicar(state["accion"], state["objeto"], hilo)}

    grafo = StateGraph(EstadoAccion)
    grafo.add_node("supervisar", supervisar)
    grafo.add_node("aplicar", aplicar)
    grafo.add_edge(START, "supervisar")
    grafo.add_edge("supervisar", "aplicar")
    grafo.add_edge("aplicar", END)
    return grafo.compile(checkpointer=guardado)


def abrir_guardado(ruta: Path = RUTA_CHECKPOINTS) -> SqliteSaver:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver(sqlite3.connect(ruta, check_same_thread=False))


def _config(hilo: str) -> Any:
    return {"configurable": {"thread_id": hilo}}


def proponer(
    grafo: CompiledStateGraph, acciones: Acciones, accion: str, objeto: dict[str, str]
) -> str:
    """Comprueba el objeto y deja la acción pausada en un hilo nuevo."""
    huella = acciones.huella(accion, objeto)
    hilo = f"{accion}-{uuid.uuid4().hex[:12]}"
    grafo.invoke(
        {"accion": accion, "objeto": objeto, "huella": huella, "aprobado": False, "resultado": ""},
        config=_config(hilo),
    )
    return hilo


def pendiente(grafo: CompiledStateGraph, hilo: str) -> dict[str, Any] | None:
    """Lo que espera decisión en ese hilo, leído del guardado; None si no hay nada."""
    estado = grafo.get_state(_config(hilo))
    if not estado.next or not estado.interrupts:
        return None
    return estado.interrupts[0].value


def resolver(
    grafo: CompiledStateGraph,
    hilo: str,
    aprobar: bool,
    huella_revisada: str,
    registrar: Callable[[dict[str, Any]], None] | None = None,
) -> str:
    """Reanuda un hilo pausado solo con un booleano y la huella que la persona revisó."""
    if not isinstance(aprobar, bool):
        raise TypeError("La decisión debe ser True o False.")
    espera = pendiente(grafo, hilo)
    if espera is None:
        raise ValueError("Ese hilo no tiene ninguna aprobación pendiente.")
    if espera["huella"] != huella_revisada:
        raise ValueError("La huella revisada no corresponde a lo que está pendiente.")
    resultado = grafo.invoke(Command(resume=aprobar), config=_config(hilo))["resultado"]
    if registrar is not None:
        registrar({
            "fecha": datetime.now(UTC).isoformat(timespec="seconds"),
            "hilo": hilo,
            "motivo": espera["motivo"],
            "huella": huella_revisada,
            "aprobado": aprobar,
            "resultado": resultado,
            # Cuenta local que ejecutó el comando; no autentica a una persona.
            "cuenta_local": getpass.getuser(),
        })
    return resultado


def registrar_decision(decision: dict[str, Any], ruta: Path = RUTA_DECISIONES) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(decision, ensure_ascii=False) + "\n")


def hilos_pendientes(guardado: SqliteSaver, grafo: CompiledStateGraph) -> list[str]:
    hilos = {c.config.get("configurable", {})["thread_id"] for c in guardado.list(None)}
    return sorted(h for h in hilos if pendiente(grafo, h) is not None)
