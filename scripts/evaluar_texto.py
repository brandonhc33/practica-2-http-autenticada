"""Genera evidencia de bloques 15–17 y prepara una revisión humana sin rellenarla."""

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, sleep
from typing import Any

from dotenv import load_dotenv

from src.catalogo import AGENTES
from src.clientes.errores import ErrorCliente
from src.clientes.gemini import consultar_gemini_raw, extraer_texto, extraer_uso
from src.clientes.reintentos import SIN_REINTENTOS
from src.clientes.salida_estructurada import parsear_respuesta_json
from src.costos.calculadora import calcular_costo_usd_gemini
from src.evaluacion.casos import construir_casos
from src.evaluacion.texto import calcular_metricas, comparar_antes_despues, resumir_metricas
from src.prompts.banco import BANCO_DE_PROMPTS

PROMPT = BANCO_DE_PROMPTS["responder_ley_rep"]
RAIZ = Path(__file__).resolve().parents[1]


def ahora() -> str:
    return datetime.now(UTC).isoformat()


def huella(datos: Any) -> str:
    return hashlib.sha256(
        json.dumps(datos, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def guardar(ruta: Path, datos: Any) -> None:
    """Reemplazo atómico: una interrupción no deja el JSON escrito a medias."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporal.replace(ruta)


def cargar(ruta: Path) -> Any:
    return json.loads(ruta.read_text(encoding="utf-8"))


def validar_casos(casos: Any) -> None:
    if not isinstance(casos, list) or not casos:
        raise ValueError("Se requiere una lista de casos.")
    ids = set()
    for caso in casos:
        if not isinstance(caso, dict) or any(
            not isinstance(caso.get(k), str) or not caso[k].strip()
            for k in ("id", "consulta", "referencia")
        ):
            raise ValueError("Cada caso requiere id, consulta y referencia no vacíos.")
        if caso["id"] in ids:
            raise ValueError("Los identificadores deben ser únicos.")
        ids.add(caso["id"])
        fragmento = caso.get("fragmento")
        if not isinstance(fragmento, dict) or any(
            not isinstance(fragmento.get(k), str) or not fragmento[k].strip()
            for k in ("id_fragmento", "texto")
        ):
            raise ValueError("Cada caso requiere un fragmento documental identificado.")


def evaluar_caso(caso: dict, modelo: str) -> dict:
    registro: dict[str, Any] = {"id": caso["id"], "fecha": ahora(), "estado": "error"}
    entrada = json.dumps(
        {"pregunta": caso["consulta"], "antecedentes": {}, "fragmentos": [caso["fragmento"]]},
        ensure_ascii=False,
    )
    inicio = perf_counter()
    try:
        datos = consultar_gemini_raw(modelo, entrada, prompt=PROMPT.nombre, politica=SIN_REINTENTOS)
        registro["respuesta_proveedor"] = datos
        uso = extraer_uso(datos.get("usage"))
        costo = calcular_costo_usd_gemini(modelo, uso)
        registro["uso"] = uso.model_dump() if uso else None
        registro["costo_usd_estimado"] = costo.model_dump(mode="json") if costo else None
        salida = parsear_respuesta_json(extraer_texto(datos, exigir_completa=True), PROMPT.nombre)
        respuesta = salida["respuesta"]
        registro.update(
            estado="ok",
            respuesta=respuesta,
            salida_estructurada=salida,
            metricas=calcular_metricas(caso["referencia"], respuesta),
            antes_despues=comparar_antes_despues(caso["referencia"], respuesta),
        )
    except (ErrorCliente, ValueError) as error:
        registro["error"] = str(error)
    except KeyboardInterrupt:
        registro.update(estado="interrumpido", error="Consumo desconocido si no llegó respuesta.")
    finally:
        registro["latencia_segundos"] = round(perf_counter() - inicio, 6)
    return registro


def exitos_actuales(registro: dict) -> list[dict]:
    """Una respuesta por caso; los errores permanecen en el historial de intentos."""
    return list({r["id"]: r for r in registro["intentos"] if r["estado"] == "ok"}.values())


def generar(casos: list[dict], modelo: str, ruta: Path, reanudar: bool, pausa: float) -> bool:
    validar_casos(casos)
    configuracion = {
        "modelo": modelo,
        "prompt": PROMPT.nombre,
        "version_prompt": PROMPT.version,
        "instrucciones": PROMPT.system_instruction,
        "esquema": PROMPT.response_schema,
        "casos": casos,
        "version_pipeline": "1",
    }
    if reanudar:
        registro = cargar(ruta)
        if registro.get("huella_configuracion") != huella(configuracion):
            raise ValueError(
                "La configuración cambió. Usa otra salida para no mezclar evaluaciones."
            )
    else:
        if ruta.exists():
            raise ValueError("La salida existe; usa --reanudar o una ruta nueva.")
        registro = {
            **configuracion,
            "huella_configuracion": huella(configuracion),
            "creado": ahora(),
            "intentos": [],
            "origen": "gemini_real",
            "alcance": "Coincidencia léxica sobre respuesta; no mide veracidad ni valida citas.",
        }
    guardar(ruta, registro)
    completados = {r["id"] for r in exitos_actuales(registro)}
    pendientes = [caso for caso in casos if caso["id"] not in completados]
    for indice, caso in enumerate(pendientes):
        try:
            if indice:
                sleep(pausa)
            resultado = evaluar_caso(caso, modelo)
        except KeyboardInterrupt:
            break
        registro["intentos"].append(resultado)
        registro["actualizado"] = ahora()
        guardar(ruta, registro)
        print(f"{caso['id']}: {resultado['estado']}", flush=True)
        if resultado["estado"] == "interrumpido":
            break
    exitos = exitos_actuales(registro)
    registro["resumen"] = {
        "casos_exitosos": len(exitos),
        "casos_pendientes": len(casos) - len(exitos),
        **resumir_metricas([r["metricas"] for r in exitos]),
    }
    guardar(ruta, registro)
    print(json.dumps(registro["resumen"], ensure_ascii=False, indent=2))
    return len(exitos) == len(casos)


def preparar_revision(registro: dict) -> dict:
    exitos = sorted(exitos_actuales(registro), key=lambda r: (r["metricas"]["f1"], r["id"]))
    if len(exitos) < 20:
        raise ValueError("El bloque 17 requiere al menos 20 respuestas exitosas con métricas.")
    casos = {c["id"]: c for c in registro["casos"]}
    revision = []
    for grupo, seleccion in (("cinco_menores", exitos[:5]), ("cinco_mayores", exitos[-5:])):
        for resultado in seleccion:
            caso = casos[resultado["id"]]
            revision.append(
                {
                    "id": resultado["id"],
                    "grupo": grupo,
                    "consulta": caso["consulta"],
                    "referencia": caso["referencia"],
                    "fragmento": caso["fragmento"],
                    "respuesta": resultado["respuesta"],
                    "metricas": resultado["metricas"],
                    "salida_estructurada": resultado["salida_estructurada"],
                    "correccion_factual": None,
                    "completitud": None,
                    "contradiccion": None,
                    "nota": "",
                }
            )
    return {
        "huella_resultados": huella(registro),
        "revisor": "",
        "fecha_revision": "",
        "criterio": "5 menores y 5 mayores F1; desempate por id; 10 casos distintos.",
        "casos": revision,
    }


def validar_revision(registro: dict, revision: dict) -> None:
    esperado = preparar_revision(registro)
    if revision.get("huella_resultados") != esperado["huella_resultados"]:
        raise ValueError("La revisión pertenece a otros resultados o estos cambiaron.")
    if not revision.get("revisor", "").strip() or not revision.get("fecha_revision", "").strip():
        raise ValueError("Completa revisor y fecha_revision.")
    casos = revision.get("casos", [])
    if len(casos) != 10:
        raise ValueError("Se requieren los diez casos seleccionados.")
    for actual, original in zip(casos, esperado["casos"], strict=True):
        for clave in original.keys() - {
            "correccion_factual",
            "completitud",
            "contradiccion",
            "nota",
        }:
            if actual.get(clave) != original[clave]:
                raise ValueError("Se modificó la evidencia o la selección de casos.")
        if any(
            actual.get(k) not in ("si", "no", "parcial")
            for k in ("correccion_factual", "completitud")
        ):
            raise ValueError(f"{actual['id']}: corrección y completitud requieren si/no/parcial.")
        if actual.get("contradiccion") not in ("si", "no") or not actual.get("nota", "").strip():
            raise ValueError(
                f"{actual['id']}: completa contradiccion (si/no) y una nota justificada."
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)
    casos_parser = sub.add_parser(
        "casos", help="Exporta referencias propuestas para revisión previa."
    )
    casos_parser.add_argument("--salida", type=Path, required=True)
    generacion = sub.add_parser("generar", help="Consulta Gemini: consume cuota.")
    generacion.add_argument("--casos", type=Path, required=True)
    generacion.add_argument("--salida", type=Path, required=True)
    generacion.add_argument(
        "--modelo", choices=tuple(AGENTES["gemini"]["modelos"]), default="flash-lite"
    )
    generacion.add_argument("--pausa", type=float, default=2)
    generacion.add_argument("--reanudar", action="store_true")
    for nombre in ("preparar-revision", "validar-revision"):
        comando = sub.add_parser(nombre)
        comando.add_argument("--resultados", type=Path, required=True)
        comando.add_argument("--revision", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.comando == "casos":
            if args.salida.exists():
                raise ValueError("El archivo de casos ya existe; no se sobrescribe.")
            guardar(args.salida, construir_casos())
        elif args.comando == "generar":
            if not math.isfinite(args.pausa) or args.pausa < 0:
                raise ValueError("La pausa debe ser finita y no negativa.")
            load_dotenv(RAIZ / ".env")
            correcto = generar(
                cargar(args.casos),
                AGENTES["gemini"]["modelos"][args.modelo],
                args.salida,
                args.reanudar,
                args.pausa,
            )
            if not correcto:
                raise SystemExit(1)
        elif args.comando == "preparar-revision":
            if args.revision.exists():
                raise ValueError("La revisión ya existe; no se sobrescribe tu trabajo manual.")
            guardar(args.revision, preparar_revision(cargar(args.resultados)))
        else:
            validar_revision(cargar(args.resultados), cargar(args.revision))
            print(
                "Revisión completa en estructura y trazabilidad. La calidad del juicio y el documento de límites requieren lectura humana."
            )
    except (ValueError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
