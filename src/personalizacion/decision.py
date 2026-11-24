"""Método de decisión del bloque 30: puntajes, empates, sensibilidad y documento base."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

TECNICAS = ("RAG", "Fine-tuning completo", "PEFT")


@dataclass(frozen=True)
class Pregunta:
    clave: str
    texto: str
    puntos: dict[str, int]
    criterio: str


# Pesos y criterios orientativos de las lecciones del bloque 30, no valores de la API.
PREGUNTAS = (
    Pregunta(
        "informacion_cambia_seguido",
        "¿La información que necesita el modelo cambia seguido?",
        {"RAG": 3},
        "Las fuentes cambian al menos una vez al mes: 3 o más cambios en 90 días.",
    ),
    Pregunta(
        "problema_de_formato_o_tono",
        "¿El modelo no mantiene un formato o tono consistente?",
        {"PEFT": 2, "Fine-tuning completo": 1},
        "En al menos 20 respuestas reales, 15 % o más incumplen lo que se necesita.",
    ),
    Pregunta(
        "dataset_grande_y_de_calidad",
        "¿Hay un dataset grande y de calidad ya etiquetado?",
        {"Fine-tuning completo": 2, "PEFT": 1},
        "Al menos 200 ejemplos y ninguna etiqueta contradictoria al revisarlos.",
    ),
    Pregunta(
        "presupuesto_limitado_o_iterar_rapido",
        "¿El presupuesto de cómputo es limitado o hay que iterar rápido?",
        {"RAG": 2, "PEFT": 1},
        "Como máximo 2 intentos de entrenamiento pagables o resultados en menos de un día.",
    ),
    Pregunta(
        "necesita_multiples_variantes",
        "¿Se necesitan varias variantes del mismo modelo base?",
        {"PEFT": 2},
        "Dos o más versiones del comportamiento (cliente, idioma o producto).",
    ),
)
CLAVES = tuple(p.clave for p in PREGUNTAS)


def exigir_respuestas(respuestas: Mapping[str, object]) -> None:
    """Un texto como "si" es verdadero en un if: aceptar solo True o False evita ese error."""
    faltantes = [c for c in CLAVES if c not in respuestas]
    sobrantes = [c for c in respuestas if c not in CLAVES]
    if faltantes or sobrantes:
        raise ValueError(f"Claves faltantes: {faltantes}; claves no previstas: {sobrantes}.")
    pendientes = [c for c in CLAVES if respuestas[c] is None]
    if pendientes:
        raise ValueError(f"Completa con True o False antes de continuar: {pendientes}.")
    invalidas = [c for c in CLAVES if not isinstance(respuestas[c], bool)]
    if invalidas:
        raise TypeError(f"Usa True o False, no textos ni números: {invalidas}.")


def recomendar_estrategia(respuestas: Mapping[str, object]) -> tuple[dict[str, int], list[str]]:
    """Devuelve todas las técnicas empatadas; max(key=...) escondería el empate."""
    exigir_respuestas(respuestas)
    puntos: dict[str, int] = dict.fromkeys(TECNICAS, 0)
    for pregunta in PREGUNTAS:
        if respuestas[pregunta.clave]:
            for tecnica, valor in pregunta.puntos.items():
                puntos[tecnica] += valor
    maximo = max(puntos.values())
    return puntos, [tecnica for tecnica, p in puntos.items() if p == maximo]


def analizar_sensibilidad(respuestas: Mapping[str, object]) -> list[dict[str, Any]]:
    """Invierte una respuesta a la vez para ver cuáles cambian la recomendación."""
    _, base = recomendar_estrategia(respuestas)
    filas = []
    for clave in CLAVES:
        variante = dict(respuestas)
        variante[clave] = not variante[clave]
        puntos, ganadoras = recomendar_estrategia(variante)
        filas.append(
            {
                "clave": clave,
                "valor_probado": variante[clave],
                "puntos": puntos,
                "ganadoras": ganadoras,
                "cambia": set(ganadoras) != set(base),
            }
        )
    return filas


def escenarios_pendientes(respuestas: Mapping[str, bool | None]) -> list[dict[str, Any]]:
    """Antes de medir, muestra qué recomendaría el método con cada valor posible."""
    pendientes = [c for c in CLAVES if respuestas.get(c) is None]
    if len(pendientes) != 1:
        raise ValueError("Los escenarios se calculan con exactamente una respuesta pendiente.")
    escenarios = []
    for valor in (False, True):
        completa = {**respuestas, pendientes[0]: valor}
        puntos, ganadoras = recomendar_estrategia(completa)
        escenarios.append(
            {"clave": pendientes[0], "valor": valor, "puntos": puntos, "ganadoras": ganadoras}
        )
    return escenarios


def estimar_costo_de_etiquetar(
    num_ejemplos: float, minutos_por_ejemplo: float, costo_por_hora: float
) -> tuple[float, float]:
    horas = (num_ejemplos * minutos_por_ejemplo) / 60
    return horas, horas * costo_por_hora


def estimar_horas_faltantes(
    actuales: int, objetivo: int, supuestos: Mapping[str, float]
) -> dict[str, float | int]:
    """Horas para llegar al objetivo, con segunda revisión parcial; no estima dinero."""
    faltan = max(objetivo - actuales, 0)
    base, _ = estimar_costo_de_etiquetar(faltan, supuestos["minutos_por_ejemplo"], 0)
    revision, _ = estimar_costo_de_etiquetar(
        faltan * supuestos["porcentaje_segunda_revision"],
        supuestos["minutos_segunda_revision"],
        0,
    )
    return {
        "faltan": faltan,
        "horas_etiquetado": round(base, 2),
        "horas_revision": round(revision, 2),
        "horas_total": round(base + revision, 2),
        "jornadas_de_8_horas": round((base + revision) / 8, 1),
    }


@dataclass(frozen=True)
class Respuesta:
    valor: bool | None
    evidencia: str


def derivar_respuestas(
    hechos: Mapping[str, Mapping[str, Any]],
    ejemplos: int,
    contradicciones: int,
    linea_base: Mapping[str, Any] | None,
) -> dict[str, Respuesta]:
    """Convierte hechos medidos en True o False con los criterios del curso."""
    cambios = hechos["cambios_fuentes_ultimos_90_dias"]
    intentos = hechos["intentos_entrenamiento_disponibles"]
    variantes = hechos["variantes_necesarias"]
    if linea_base is None or linea_base.get("supera_umbral") is None:
        formato = Respuesta(
            None, "Pendiente: falta una línea base completa de al menos 20 respuestas."
        )
    else:
        incumplen = len(linea_base["incumplimientos_modelo"])
        formato = Respuesta(
            bool(linea_base["supera_umbral"]),
            f"{incumplen} de {linea_base['muestra_modelo']} respuestas del clasificador actual "
            f"incumplen ({linea_base['proporcion_incumplimiento']:.1%}); el umbral es 15 %.",
        )
    return {
        "informacion_cambia_seguido": Respuesta(
            cambios["valor"] >= 3, f"{cambios['valor']} cambios en 90 días. {cambios['evidencia']}"
        ),
        "problema_de_formato_o_tono": formato,
        "dataset_grande_y_de_calidad": Respuesta(
            ejemplos >= 200 and contradicciones == 0,
            f"{ejemplos} ejemplos etiquetados y {contradicciones} etiquetas contradictorias "
            "detectadas; el criterio pide al menos 200.",
        ),
        "presupuesto_limitado_o_iterar_rapido": Respuesta(
            intentos["valor"] <= 2,
            f"{intentos['valor']} intentos de entrenamiento disponibles. {intentos['evidencia']}",
        ),
        "necesita_multiples_variantes": Respuesta(
            variantes["valor"] >= 2,
            f"{variantes['valor']} variante necesaria. {variantes['evidencia']}",
        ),
    }


def generar_esqueleto_decision(
    problema: str,
    respuestas: Mapping[str, Respuesta],
    puntos: Mapping[str, int],
    ganadoras: list[str],
    sensibilidad: list[dict[str, Any]],
) -> str:
    """Cuatro secciones en orden; los [COMPLETAR] marcan lo que se redacta a mano."""
    empate = len(ganadoras) > 1
    lineas = ["# Decisión de personalización", "", "## 1. El problema", "", problema, ""]
    lineas += ["## 2. Resultado del método de decisión", ""]
    lineas += ["| Pregunta | Respuesta | Evidencia |", "| --- | --- | --- |"]
    for pregunta in PREGUNTAS:
        respuesta = respuestas[pregunta.clave]
        valor = "Sí" if respuesta.valor else "No"
        lineas.append(f"| {pregunta.texto} | {valor} | {respuesta.evidencia} |")
    lineas.append("")
    for tecnica, p in sorted(puntos.items(), key=lambda par: -par[1]):
        lineas.append(f"- {tecnica}: {p} puntos")
    lineas.append("")
    if empate:
        lineas.append(f"**Empate entre: {', '.join(ganadoras)}.** El puntaje no decide solo.")
    else:
        lineas.append(f"**Mayor puntaje: {ganadoras[0]}.**")
    lineas += ["", "Análisis de sensibilidad (una respuesta invertida a la vez):", ""]
    for fila in sensibilidad:
        cambio = "cambia" if fila["cambia"] else "igual"
        lineas.append(
            f"- `{fila['clave']}` → {fila['valor_probado']}: "
            f"{', '.join(fila['ganadoras'])} ({cambio})"
        )
    lineas += ["", "## 3. Técnica elegida y por qué", ""]
    if empate:
        lineas.append("[COMPLETAR: el puntaje no resolvió el empate; justificar con costos.]")
    else:
        lineas.append(f"[COMPLETAR: por qué {ganadoras[0]} responde o no responde a este caso.]")
    lineas += ["", "## 4. Qué se necesitaría para ejecutarla", ""]
    lineas.append("[COMPLETAR: ejemplos o corpus que faltan, con números y horas.]")
    return "\n".join(lineas) + "\n"
