"""Dataset de tuning del bloque 29: construir, revisar el balance y validar antes de entrenar."""

import hashlib
import json
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from google.genai import tunings as sdk_tunings
from google.genai import types

from src.evaluacion.texto import limpiar_texto
from src.prompts.contexto_ley_rep import cargar_documento_ley_rep

RAIZ = Path(__file__).resolve().parents[2]
RUTA_DATASET = RAIZ / "datos" / "personalizacion" / "rutas_ley_rep.json"
RUTAS = ("normativa", "resumen", "aclaracion")
CLAVES_SALIDA = ("ruta", "articulo")
MINIMO_EJEMPLOS = 10
# Umbrales del proyecto, no límites de la API: una consulta larga podría truncarse sin aviso.
MAXIMO_CARACTERES_ENTRADA = 300
RAZON_BALANCE_MAXIMA = 2.0

# El curso omite EXPIRED: con su lista, un trabajo vencido se consultaría para siempre.
ESTADOS_FINALES = frozenset(
    {
        types.JobState.JOB_STATE_SUCCEEDED,
        types.JobState.JOB_STATE_FAILED,
        types.JobState.JOB_STATE_CANCELLED,
        types.JobState.JOB_STATE_PARTIALLY_SUCCEEDED,
        types.JobState.JOB_STATE_EXPIRED,
    }
)

EjemploRaw = tuple[str, dict[str, Any]]


def cargar_dataset(ruta: Path = RUTA_DATASET) -> dict[str, Any]:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError(f"No se pudo leer el dataset {ruta}.") from None
    if not isinstance(datos, dict) or not isinstance(datos.get("ejemplos"), list):
        raise ValueError("El dataset debe ser un objeto con una lista 'ejemplos'.")
    return datos


def huella_archivo(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def ejemplos_raw(dataset: dict[str, Any]) -> list[EjemploRaw]:
    """Pares (consulta, salida esperada), como `ejemplos_raw` en las lecciones del curso."""
    return [(ejemplo["consulta"], ejemplo["salida"]) for ejemplo in dataset["ejemplos"]]


def construir_ejemplos(pares: list[EjemploRaw]) -> list[types.TuningExample]:
    """La salida se serializa con comillas dobles y tildes: es lo que el modelo imitaría."""
    return [
        types.TuningExample(text_input=texto, output=json.dumps(salida, ensure_ascii=False))
        for texto, salida in pares
    ]


def chequear_balance(pares: list[EjemploRaw], clave: str) -> Counter[str]:
    return Counter(str(salida[clave]) for _, salida in pares)


def resumir_balance(conteo: Counter[str], categorias: tuple[str, ...] = RUTAS) -> dict[str, Any]:
    """Incluye las categorías sin ejemplos: un cero no aparece en un Counter."""
    completo = {categoria: conteo.get(categoria, 0) for categoria in categorias}
    maximo, minimo = max(completo.values()), min(completo.values())
    razon = maximo / minimo if minimo else None
    return {
        "conteos": completo,
        "maximo": maximo,
        "minimo": minimo,
        "razon_max_min": razon,
        "aceptable": razon is not None and razon <= RAZON_BALANCE_MAXIMA,
    }


def validar_dataset(
    examples: list[types.TuningExample], claves_esperadas: tuple[str, ...] = CLAVES_SALIDA
) -> list[str]:
    """Valida cada ejemplo y reporta todos los problemas, no solo el primero."""
    problemas: list[str] = []
    vistos: dict[str, tuple[int, Any]] = {}
    for i, ejemplo in enumerate(examples):
        texto = ejemplo.text_input or ""
        try:
            salida = json.loads(ejemplo.output or "")
            json_valido = True
        except json.JSONDecodeError:
            salida, json_valido = None, False
        if not texto.strip():
            problemas.append(f"ejemplo {i}: text_input vacio")
        else:
            # Normalizar detecta duplicados que solo cambian mayúsculas o puntuación.
            clave_texto = limpiar_texto(texto)
            if clave_texto in vistos:
                anterior, salida_anterior = vistos[clave_texto]
                if json_valido and salida_anterior is not None and salida != salida_anterior:
                    problemas.append(f"ejemplo {i}: contradice la etiqueta del ejemplo {anterior}")
                else:
                    problemas.append(f"ejemplo {i}: text_input duplicado del ejemplo {anterior}")
            else:
                vistos[clave_texto] = (i, salida)
        if not ejemplo.output or not ejemplo.output.strip():
            problemas.append(f"ejemplo {i}: output vacio")
            continue
        if not json_valido:
            problemas.append(f"ejemplo {i}: output no es JSON valido")
            continue
        if not isinstance(salida, dict):
            problemas.append(f"ejemplo {i}: output no es un objeto JSON")
            continue
        for clave in claves_esperadas:
            if clave not in salida:
                problemas.append(f'ejemplo {i}: output no tiene la clave "{clave}"')
        for clave in sorted(set(salida) - set(claves_esperadas)):
            problemas.append(f'ejemplo {i}: output tiene la clave no prevista "{clave}"')
    return problemas


def referencias_disponibles() -> frozenset[str]:
    return frozenset(f["referencia"] for f in cargar_documento_ley_rep()["fragmentos"])


def validar_reglas_rutas(
    examples: list[types.TuningExample], referencias: frozenset[str]
) -> list[str]:
    """Aplica las reglas R1 a R3 del proyecto; el formato ya lo revisa validar_dataset."""
    problemas: list[str] = []
    for i, ejemplo in enumerate(examples):
        if len(ejemplo.text_input or "") > MAXIMO_CARACTERES_ENTRADA:
            problemas.append(
                f"ejemplo {i}: text_input supera {MAXIMO_CARACTERES_ENTRADA} caracteres"
            )
        try:
            salida = json.loads(ejemplo.output or "")
        except json.JSONDecodeError:
            continue
        if not isinstance(salida, dict):
            continue
        ruta, articulo = salida.get("ruta"), salida.get("articulo")
        if ruta not in RUTAS:
            problemas.append(f'ejemplo {i}: ruta "{ruta}" no es una de {", ".join(RUTAS)}')
        if articulo is not None and articulo not in referencias:
            problemas.append(f'ejemplo {i}: articulo "{articulo}" no existe en la copia local')
        if ruta == "resumen" and articulo is None:
            problemas.append(f"ejemplo {i}: una ruta resumen necesita un articulo (R1)")
        if ruta == "aclaracion" and articulo is not None:
            problemas.append(f"ejemplo {i}: una ruta aclaracion no lleva articulo (R3)")
    return problemas


def revisar_dataset(examples: list[types.TuningExample], referencias: frozenset[str]) -> list[str]:
    problemas = validar_dataset(examples) + validar_reglas_rutas(examples, referencias)
    if len(examples) < MINIMO_EJEMPLOS:
        problemas.append(f"dataset: tiene {len(examples)} ejemplos y se piden al menos 10")
    return problemas


def _con_reemplazo(
    examples: list[types.TuningExample],
    indice: int,
    *,
    texto: str | None = None,
    salida: str | None = None,
) -> list[types.TuningExample]:
    copia = [ejemplo.model_copy() for ejemplo in examples]
    original = copia[indice]
    copia[indice] = types.TuningExample(
        text_input=original.text_input if texto is None else texto,
        output=original.output if salida is None else salida,
    )
    return copia


def generar_casos_rotos(
    examples: list[types.TuningExample],
) -> list[tuple[str, list[types.TuningExample]]]:
    """Copias con un defecto cada una, para comprobar que el validador de verdad lo detecta."""
    primero = examples[0]
    # Para contradecir hace falta otra etiqueta, no solo otro ejemplo.
    distinto = next(e for e in examples if e.output != primero.output)
    return [
        ("text_input vacío", _con_reemplazo(examples, 0, texto="   ")),
        (
            "output sin la clave articulo",
            _con_reemplazo(examples, 0, salida='{"ruta": "normativa"}'),
        ),
        (
            "comillas simples en lugar de JSON",
            _con_reemplazo(examples, 0, salida="{'ruta': 'normativa', 'articulo': None}"),
        ),
        ("consulta duplicada", examples + [primero.model_copy()]),
        (
            "misma consulta con otra etiqueta",
            examples
            + [
                types.TuningExample(
                    text_input=(primero.text_input or "").upper(), output=distinto.output
                )
            ],
        ),
        (
            "ruta fuera del contrato",
            _con_reemplazo(examples, 0, salida='{"ruta": "otra", "articulo": null}'),
        ),
        (
            "resumen sin artículo",
            _con_reemplazo(examples, 0, salida='{"ruta": "resumen", "articulo": null}'),
        ),
        (
            "artículo inexistente",
            _con_reemplazo(examples, 0, salida='{"ruta": "normativa", "articulo": "Artículo 60"}'),
        ),
        (
            "clave no prevista",
            _con_reemplazo(
                examples, 0, salida='{"ruta": "normativa", "articulo": null, "motivo": "x"}'
            ),
        ),
        ("dataset con menos de 10 ejemplos", examples[:9]),
    ]


def construir_configuracion_peft(
    adapter_size: types.AdapterSize = types.AdapterSize.ADAPTER_SIZE_FOUR, epoch_count: int = 5
) -> types.CreateTuningJobConfig:
    """Configuración demostrativa del curso; construirla no llama a la API."""
    return types.CreateTuningJobConfig(
        tuning_mode=types.TuningMode.TUNING_MODE_PEFT_ADAPTER,
        adapter_size=adapter_size,
        epoch_count=epoch_count,
        tuned_model_display_name="clasificador-rutas-ley-rep",
    )


def comprobar_modo_desarrollador(config: types.CreateTuningJobConfig) -> str | None:
    """Devuelve el motivo por el que la API para desarrolladores rechazaría la configuración.

    Usa la misma conversión interna que `client.tunings.tune` aplica antes de enviar:
    no crea un cliente, no necesita clave y no usa la red. Al ser interna del SDK, una
    actualización puede cambiarla; las pruebas lo detectarían.
    """
    try:
        sdk_tunings._CreateTuningJobConfig_to_mldev(config, {})  # pyright: ignore[reportPrivateUsage]
    except ValueError as error:
        return str(error)
    return None


class _Trabajos(Protocol):
    def get(self, *, name: str) -> types.TuningJob: ...


class ClienteTuning(Protocol):
    @property
    def tunings(self) -> _Trabajos: ...


def esperar_a_que_termine(
    client: ClienteTuning,
    nombre_trabajo: str,
    intervalo_segundos: float = 30,
    espera_maxima_segundos: float | None = None,
    *,
    dormir: Callable[[float], None] = time.sleep,
    reloj: Callable[[], float] = time.monotonic,
) -> types.TuningJob:
    """Consulta con `get` (no con `tune`, que crearía otro trabajo) hasta un estado final."""
    inicio = reloj()
    while True:
        trabajo = client.tunings.get(name=nombre_trabajo)
        print(f"estado actual: {trabajo.state}", flush=True)
        if trabajo.state in ESTADOS_FINALES:
            return trabajo
        if espera_maxima_segundos is not None and reloj() - inicio >= espera_maxima_segundos:
            # Detener este script no detiene el trabajo: para eso existe client.tunings.cancel.
            raise TimeoutError(
                f"{nombre_trabajo} sigue en {trabajo.state}. Si ya no lo necesitas, "
                "cancélalo con client.tunings.cancel(name=...)."
            )
        dormir(intervalo_segundos)
