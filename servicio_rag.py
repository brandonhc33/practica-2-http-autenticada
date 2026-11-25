"""Gate 2: servicio RAG de la Ley REP, de indexar a responder, con supervisión humana.

Sin argumentos ensaya el servicio completo sobre las dos normas reales, con embeddings y
modelo locales: no usa red, clave ni cuota. Los demás comandos trabajan con Gemini y
requieren --confirmar-consumo cuando lo llaman.
"""

import argparse
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langgraph.checkpoint.memory import InMemorySaver

from scripts.logging_rag import CON_INYECCION, CORREO, consultar_de_prueba
from scripts.rag_comun import exigir_consumo
from src.catalogo import AGENTES
from src.gobernanza.prompts import RegistroDePrompts, VersionPrompt, guardar_json, prompt_activo
from src.gobernanza.supervision import (
    BORRADORES,
    Acciones,
    abrir_guardado,
    construir_grafo,
    pendiente,
    proponer,
    resolver,
)
from src.observabilidad.datos_sensibles import ocultar_datos_sensibles
from src.observabilidad.trazas import configurar_registro, trace_id_actual
from src.orquestacion.modelo import crear_modelo
from src.rag.indice import crear_embeddings
from src.rag.indice_normas import (
    abrir_indice_normas,
    actualizar_indice,
    planificar,
)
from src.rag.normas import NORMAS, RAIZ, leer_normas_activas
from src.rag.recuperacion import validar_consulta
from src.rag.servicio import nombre_fuente, responder
from src.rag.simulado import (
    DIMENSIONES_LEXICO,
    MODELO_LEXICO,
    NOMBRE_MODELO_SIMULADO,
    EmbeddingsDePalabras,
    ModeloQueCita,
)

K = 5
REGISTRO = RAIZ / "output" / "servicio" / "eventos.jsonl"
MODELO = AGENTES["gemini"]["modelos"]["flash-lite"]
LOCAL: dict[str, Any] = {
    "modelo_embeddings": MODELO_LEXICO, "dimensiones": DIMENSIONES_LEXICO,
}


def copiar_proyecto(carpeta: Path) -> tuple[Path, Acciones]:
    """Copia lo que el ensayo modifica; las normas aprobadas del proyecto no cambian."""
    for norma in NORMAS.values():
        destino = carpeta / norma.archivo
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(RAIZ / norma.archivo, destino)
    activas = carpeta / "normas_activas.json"
    base = {"ley-20920": leer_normas_activas()["ley-20920"]}
    guardar_json(activas, {"normas": base})
    return activas, Acciones(raiz=carpeta, ruta_normas=activas)


def guardar_borrador(
    pregunta: str, resultado: dict[str, Any], indice: Chroma, raiz: Path = RAIZ
) -> Path:
    """Deja respuesta y texto completo de cada fuente para quien decide la entrega."""
    ids = [f["id_chunk"] for f in resultado["fuentes"]]
    guardados = indice.get(ids=ids) if ids else {"ids": [], "documents": []}
    textos = dict(zip(guardados["ids"], guardados["documents"], strict=True))
    ruta = raiz / BORRADORES / f"{resultado['trace_id']}.json"
    guardar_json(ruta, {
        "trace_id": resultado["trace_id"],
        "estado": resultado["estado"],
        "pregunta": ocultar_datos_sensibles(pregunta)[0],
        "respuesta": resultado["respuesta"],
        "fuentes": [{**f, "texto": textos[f["id_chunk"]]} for f in resultado["fuentes"]],
        "requiere_revision": resultado["requiere_revision"],
        "huella_prompt": resultado["huella_prompt"],
        "consumo": resultado["consumo"],
    })
    return ruta


def mostrar(resultado: dict[str, Any]) -> None:
    print(f"trace_id: {resultado['trace_id']} | estado: {resultado['estado']}")
    print(resultado["respuesta"])


class _ContarEmbeddings(Embeddings):
    def __init__(self, base: Embeddings):
        self.base = base
        self.textos = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.textos += len(texts)
        return self.base.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.base.embed_query(text)


def _vectores(indice: Chroma, norma: str) -> dict[str, list[float]]:
    datos = indice.get(where={"norma": norma}, include=["embeddings"])
    return {
        i: [float(x) for x in v] for i, v in zip(datos["ids"], datos["embeddings"], strict=True)
    }


def ensayo() -> int:
    """Recorre el servicio completo y comprueba los cuatro criterios no compensables."""
    memoria = io.StringIO()
    configurar_registro(memoria)
    comprobaciones: dict[str, bool] = {}
    with tempfile.TemporaryDirectory() as carpeta:
        raiz = Path(carpeta)
        activas, acciones = copiar_proyecto(raiz)
        grafo = construir_grafo(acciones, InMemorySaver())
        opciones = {**LOCAL, "ruta_activas": activas, "raiz": raiz}
        directorio = raiz / "indice"
        embeddings = _ContarEmbeddings(EmbeddingsDePalabras())

        print("== 1. Indexar la Ley 20.920 y reutilizar el índice ==")
        primero = actualizar_indice(embeddings, directorio, **opciones)
        repetido = actualizar_indice(embeddings, directorio, **opciones)
        indice, _ = abrir_indice_normas(directorio, **opciones)
        antes = _vectores(indice, "ley-20920")
        print(f"fragmentos: {primero['fragmentos']}; segunda corrida convierte "
              f"{repetido['embeddings_calculados']} textos")
        comprobaciones["el índice persistido se reutiliza sin convertir texto otra vez"] = (
            repetido["reutilizado"] and repetido["embeddings_calculados"] == 0
        )

        print("\n== 2. Agregar el DS 12/2020 con aprobación (decisión simulada) ==")
        hilo = proponer(grafo, acciones, "activar_norma", {"norma": "ds-12-2020"})
        espera = pendiente(grafo, hilo)
        sin_aprobar = set(leer_normas_activas(activas)) == {"ley-20920"}
        print("pausado:", espera)
        print(resolver(grafo, hilo, True, espera["huella"] if espera else ""))
        ya_convertidos = embeddings.textos
        segundo = actualizar_indice(embeddings, directorio, **opciones)
        indice, _ = abrir_indice_normas(directorio, **opciones)
        print("cambios:", segundo["cambios_por_norma"])
        comprobaciones["una norma no se usa antes de aprobarla"] = sin_aprobar
        comprobaciones["agregar una norma solo convierte la nueva y conserva los demás vectores"] = (
            embeddings.textos - ya_convertidos
            == segundo["cambios_por_norma"]["ds-12-2020"]["agregar"]
            and _vectores(indice, "ley-20920") == antes
        )

        print("\n== 3. Recuperar, filtrar, responder y citar ==")
        pregunta = f"¿De qué color deben ser los contenedores de plástico? Mi correo es {CORREO}"
        resultado = responder(
            pregunta, indice, embeddings, ModeloQueCita(), NOMBRE_MODELO_SIMULADO,
            prompt_activo(), K,
        )
        mostrar(resultado)
        comprobaciones["el servicio completa la consulta sin excepciones"] = (
            resultado["estado"] == "ok"
        )
        comprobaciones["la respuesta nombra la norma y el artículo que cita"] = bool(
            resultado["fuentes"]
        ) and all(nombre_fuente(f) in resultado["respuesta"] for f in resultado["fuentes"])

        ataque = consultar_de_prueba("¿Quién debe inscribirse?", [CON_INYECCION], "Todos [1].")
        comprobaciones["si todo el contexto es sospechoso, no se llama al modelo"] = (
            ataque["estado"] == "abstencion" and ataque["consumo"] is None
        )
        roto = responder(
            "¿Qué es un envase?", indice, embeddings, ModeloQueCita(), NOMBRE_MODELO_SIMULADO,
            prompt_activo(), k=0,
        )
        comprobaciones["un error queda controlado y con traza"] = roto["estado"] == "error"
        comprobaciones["cada consulta tiene su traza y ninguna queda abierta"] = (
            len({resultado["trace_id"], ataque["trace_id"], roto["trace_id"]}) == 3
            and trace_id_actual() is None
        )

        print("\n== 4. Entregar la respuesta: pausa, rechazo y aprobación (simulados) ==")
        borrador = guardar_borrador(pregunta, resultado, indice, raiz)
        objeto = {"borrador": str(borrador.relative_to(raiz))}
        resultados = []
        for aprobar in (False, True):
            hilo = proponer(grafo, acciones, "entregar_respuesta", objeto)
            espera = pendiente(grafo, hilo)
            pausada = espera is not None and not list(raiz.glob("output/servicio/entregadas/*"))
            texto = resolver(grafo, hilo, aprobar, espera["huella"] if espera else "")
            resultados.append((pausada, texto))
            print(f"decisión simulada = {aprobar}: {texto}")
        entregadas = list(raiz.glob("output/servicio/entregadas/*"))
        comprobaciones["la entrega se pausa, se rechaza sin efectos y solo sale al aprobar"] = (
            all(p for p, _ in resultados) and resultados[0][1].startswith("rechazada")
            and len(entregadas) == 1
        )
        guardado = borrador.read_text(encoding="utf-8") + entregadas[0].read_text(encoding="utf-8")

    texto = memoria.getvalue()
    print("\n== Eventos ==")
    print(texto, end="")
    comprobaciones["ni los eventos ni los archivos guardan el correo de prueba"] = (
        CORREO not in texto and CORREO not in guardado
    )
    comprobaciones["los eventos no tienen la pregunta ni la respuesta"] = not any(
        t in texto for t in ("color deben ser", resultado["respuesta"].splitlines()[0])
    )
    print("\nComprobaciones (normas reales; embeddings y modelo simulados, sin Gemini):")
    for nombre, correcto in comprobaciones.items():
        print(f"- {'correcto' if correcto else 'FALLA'}: {nombre}")
    correcto = all(comprobaciones.values())
    print("Proceso terminado sin errores." if correcto else "Hay comprobaciones fallidas.")
    return 0 if correcto else 1


def estado() -> int:
    plan = planificar()
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


def indexar(confirmado: bool) -> int:
    plan = planificar()
    if plan["embeddings_por_calcular"]:
        exigir_consumo(confirmado)
    # Sin texto nuevo no se llama a la API: basta con comprobar o retirar.
    embeddings = crear_embeddings() if plan["embeddings_por_calcular"] else EmbeddingsDePalabras()
    try:
        resultado = actualizar_indice(embeddings)
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(
            f"Indexación interrumpida: {type(error).__name__}. Lo guardado se conserva y el índice "
            "queda cerrado. Si fue el límite por minuto, espera y repite el comando: continúa."
        ) from error
    for campo in ("cambios_por_norma", "embeddings_calculados", "fragmentos", "huella_indice"):
        print(f"{campo}: {resultado[campo]}")
    return 0


def elegir_prompt(huella: str | None) -> VersionPrompt:
    activa = prompt_activo()
    if huella is None or huella == activa.huella:
        return activa
    print(f"Versión en prueba: {huella}. La activa sigue siendo {activa.huella}.")
    return RegistroDePrompts.cargar().buscar(huella)


def preguntar(preguntas: list[str], k: int, confirmado: bool, huella: str | None) -> int:
    for pregunta in preguntas:
        validar_consulta(pregunta, k)
    prompt = elegir_prompt(huella)
    indice, _ = abrir_indice_normas()
    exigir_consumo(confirmado)
    embeddings, modelo = crear_embeddings(), crear_modelo("flash-lite")
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    correcto = True
    with REGISTRO.open("a", encoding="utf-8") as archivo:
        configurar_registro(archivo)
        for pregunta in preguntas:
            r = responder(pregunta, indice, embeddings, modelo, MODELO, prompt, k)
            mostrar(r)
            if r["requiere_revision"]:
                print("Se descartó un fragmento sospechoso: revisar antes de usar la respuesta.")
            if r["estado"] == "ok":
                guardar_borrador(pregunta, r, indice)
                print("BORRADOR. Para pedir su entrega: "
                      f"uv run python servicio_rag.py entregar {r['trace_id']}")
            correcto = correcto and r["estado"] != "error"
            print()
    print(f"Eventos en {REGISTRO.relative_to(RAIZ)}")
    return 0 if correcto else 1


def entregar(trace_id: str) -> int:
    acciones = Acciones()
    grafo = construir_grafo(acciones, abrir_guardado())
    objeto = {"borrador": f"{BORRADORES}/{trace_id}.json"}
    hilo = proponer(grafo, acciones, "entregar_respuesta", objeto)
    print(f"Pausado: no se entregó nada. Hilo: {hilo}")
    print(f"Para revisar y decidir: uv run python -m scripts.grafo_supervision decidir {hilo}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando")
    comandos.add_parser("ensayo", help="Servicio completo simulado (opción por omisión).")
    comandos.add_parser("estado", help="Normas activas y cambios pendientes, sin API.")
    p = comandos.add_parser("indexar", help="Dejar el índice igual a las normas aprobadas.")
    p.add_argument("--confirmar-consumo", action="store_true")
    p = comandos.add_parser("preguntar", help="Consultar con Gemini y guardar el borrador.")
    p.add_argument("preguntas", nargs="+")
    p.add_argument("--k", type=int, choices=range(1, 21), default=K)
    p.add_argument("--prompt", metavar="HUELLA", help="Probar una versión sin activarla.")
    p.add_argument("--confirmar-consumo", action="store_true")
    p = comandos.add_parser("entregar", help="Pausar la entrega de un borrador.")
    p.add_argument("trace_id")
    args = parser.parse_args(argv)
    try:
        if args.comando == "estado":
            return estado()
        if args.comando == "indexar":
            return indexar(args.confirmar_consumo)
        if args.comando == "preguntar":
            return preguntar(args.preguntas, args.k, args.confirmar_consumo, args.prompt)
        if args.comando == "entregar":
            return entregar(args.trace_id)
        return ensayo()
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    except Exception as error:
        # El mensaje del proveedor puede repetir contenido o datos del transporte.
        parser.exit(1, f"No se completó el comando: {type(error).__name__}.\n")


if __name__ == "__main__":
    sys.exit(main())
