"""Convierte el DS 12/2020 del Diario Oficial en artículos trazables, con sus tablas.

Uso: uv run --with pymupdf python -m scripts.extraer_ds12
Las cuatro tablas del PDF son imágenes: su texto viene de datos/ds_12_2020/tablas.json.
"""

import argparse
import hashlib
import json
import re
from datetime import date
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pymupdf

CARPETA = Path(__file__).resolve().parent.parent / "datos" / "ds_12_2020"
ARCHIVO_PDF = "DS-12-2020_DO-16-MAR-2021.pdf"
URL = "https://www.diariooficial.interior.gob.cl/publicaciones/2021/03/16/42906/01/1910141.pdf"
TRANSITORIOS = ("primero", "segundo", "tercero", "cuarto", "quinto", "sexto")
ARTICULO = re.compile(rf"^Artículo (\d+|{'|'.join(TRANSITORIOS)})º?\. ")
# Posiciones en puntos: fuera de esta franja solo hay encabezado y pie de página.
CUERPO_DESDE, CUERPO_HASTA = 60, 850
# Margen de una línea que continúa: 85; primera línea de un párrafo: 108; título: centrado.
INICIO_PARRAFO, INICIO_TITULO = 100, 112


def leer_lineas(paginas: list[list[tuple[float, float, str]]]) -> list[tuple[int, float, str]]:
    """(página, margen, texto) de cada línea del cuerpo."""
    return [
        (numero, x, limpio)
        for numero, lineas in enumerate(paginas, start=1)
        for x, y, texto in lineas
        if CUERPO_DESDE < y < CUERPO_HASTA and (limpio := re.sub(r"\s+", " ", texto).strip())
    ]


def leer_pdf(pdf: Path) -> list[list[tuple[float, float, str]]]:
    with pymupdf.open(pdf) as documento:
        return [
            [
                (linea["bbox"][0], linea["bbox"][1], "".join(s["text"] for s in linea["spans"]))
                for bloque in pagina.get_text("dict")["blocks"]
                for linea in bloque.get("lines", [])
            ]
            for pagina in documento
        ]


def reunir_parrafos(lineas: list[tuple[int, float, str]]) -> list[tuple[set[int], bool, str]]:
    """(páginas, es título, texto). Un párrafo puede seguir en otra página."""
    parrafos: list[tuple[set[int], bool, str]] = []
    for numero, margen, texto in lineas:
        titulo = margen >= INICIO_TITULO
        if parrafos and not titulo and not parrafos[-1][1] and margen < INICIO_PARRAFO:
            paginas, _, previo = parrafos[-1]
            parrafos[-1] = (paginas | {numero}, False, f"{previo} {texto}")
        else:
            parrafos.append(({numero}, titulo, texto))
    return parrafos


def texto_de_tabla(tabla: dict[str, Any]) -> str:
    """Cada fila se entiende sola: un corte del texto no la separa de sus columnas."""
    paginas = "página " if len(tabla["paginas"]) == 1 else "páginas "
    paginas += " y ".join(str(p) for p in tabla["paginas"])
    filas = [tabla["fila"].format(*fila) for fila in tabla["filas"]]
    return "\n".join([f"[Tabla transcrita de la imagen, {paginas}] {tabla['titulo']}:", *filas])


def separar_articulos(
    parrafos: list[tuple[set[int], bool, str]], tablas: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    articulos: list[dict[str, Any]] = []
    actual: dict[str, Any] | None = None
    pendientes = {t["articulo"]: t for t in tablas}
    for paginas, titulo, texto in parrafos:
        if titulo or texto.startswith("Anótese, tómese razón"):
            actual = None
            continue
        encontrado = ARTICULO.match(texto)
        if encontrado:
            numero = encontrado[1]
            transitorio = numero in TRANSITORIOS
            actual = {
                "id": f"transitorio-{numero}" if transitorio else f"articulo-{numero}",
                "numero": numero,
                "referencia": f"Artículo {numero}" + (" transitorio" if transitorio else ""),
                "paginas": [],
                "partes": [],
            }
            articulos.append(actual)
        if actual is None:
            continue
        actual["partes"].append(texto)
        actual["paginas"] = sorted({*actual["paginas"], *paginas})
        tabla = pendientes.get(actual["numero"])
        if tabla and texto.endswith(tabla["despues_de"]):
            actual["partes"].append(texto_de_tabla(tabla))
            actual["paginas"] = sorted({*actual["paginas"], *tabla["paginas"]})
            del pendientes[actual["numero"]]
    if pendientes:
        raise ValueError(f"No se encontró dónde insertar las tablas: {sorted(pendientes)}.")
    return articulos


def convertir(carpeta: Path = CARPETA) -> dict[str, Any]:
    pdf = carpeta / ARCHIVO_PDF
    paginas = leer_pdf(pdf)
    portada = " ".join(texto for _, _, texto in paginas[0])
    if "CVE 1910141" not in portada or "Núm. 12.- Santiago, 8 de junio de 2020" not in portada:
        raise ValueError("El PDF debe ser el DS 12/2020 del Diario Oficial, CVE 1910141.")
    tablas = json.loads((carpeta / "tablas.json").read_text(encoding="utf-8"))["tablas"]
    parrafos = reunir_parrafos(leer_lineas(paginas))
    articulos = separar_articulos(parrafos, tablas)
    esperados = [f"articulo-{n}" for n in range(1, 48)] + [f"transitorio-{n}" for n in TRANSITORIOS]
    if [a["id"] for a in articulos] != esperados:
        raise ValueError("La extracción no conservó los 47 artículos y seis transitorios.")

    texto = "\n\n".join(p for _, _, p in parrafos) + "\n"
    fecha = date.today().isoformat()
    sha256_pdf = hashlib.sha256(pdf.read_bytes()).hexdigest()
    datos = {
        "documento": "DS 12/2020",
        "titulo": "Establece metas de recolección y valorización y otras obligaciones asociadas "
        "de envases y embalajes",
        "fecha_publicacion": "2021-03-16",
        "version_documento": "2021-03-16",
        "fecha_extraccion": fecha,
        "archivo_pdf": ARCHIVO_PDF,
        "sha256_pdf": sha256_pdf,
        "sha256_texto": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
        "sha256_tablas": hashlib.sha256((carpeta / "tablas.json").read_bytes()).hexdigest(),
        "paginas": len(paginas),
        "extractor": f"PyMuPDF {version('pymupdf')}, por posición de línea",
        "tratamiento": "Párrafos reunidos, también entre páginas; sin encabezados ni pies. El TXT "
        "conserva vistos y considerandos; el JSON, solo los artículos. Las tablas de los artículos "
        "21, 23, 35 y 36 son imágenes en el PDF y se transcribieron en tablas.json.",
        "alcance": "Texto publicado el 2021-03-16. No verifica modificaciones posteriores ni "
        "incorpora interpretaciones o resoluciones relacionadas.",
        "fragmentos": [
            {
                "id_fragmento": f"ds12-{a['id']}",
                "documento": "DS 12/2020",
                "referencia": a["referencia"],
                "url": URL,
                "fecha_consulta": fecha,
                "version_documento": "2021-03-16",
                "archivo_pdf": ARCHIVO_PDF,
                "sha256_pdf": sha256_pdf,
                "paginas": a["paginas"],
                "texto": "\n\n".join(a["partes"]),
            }
            for a in articulos
        ],
    }
    (carpeta / "ds_12_2020.txt").write_text(texto, encoding="utf-8")
    (carpeta / "ds_12_2020.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return datos


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    datos = convertir()
    print(f"Convertidas {datos['paginas']} páginas y {len(datos['fragmentos'])} artículos.")


if __name__ == "__main__":
    main()
