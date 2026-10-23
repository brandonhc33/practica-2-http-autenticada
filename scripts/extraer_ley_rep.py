"""Convierte la copia PDF de la Ley 20.920 de 2016 en texto y artículos trazables.

Uso: uv run --with pypdf python scripts/extraer_ley_rep.py /ruta/a/ley.pdf
El cliente usa los archivos generados; pypdf solo se necesita para esta conversión.
"""

import argparse
import hashlib
import json
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader

DESTINO = Path(__file__).resolve().parent.parent / "datos" / "ley_rep"
ARCHIVO_PDF = "Ley-20920_01-JUN-2016.pdf"
ARTICULO = re.compile(r"^Artículo (\d+|primero|segundo|tercero|cuarto)[º°]?\.-")
SECCION = re.compile(r"^(?:TÍTULO [IVX]+|Párrafo \d+[º°]?|DISPOSICIONES TRANSITORIAS)$")
TRANSITORIOS = ("primero", "segundo", "tercero", "cuarto")


def extraer_parrafos(texto: str) -> list[str]:
    """Une líneas de un párrafo y retira solo encabezados y pies repetidos del PDF."""
    parrafos: list[str] = []
    lineas: list[str] = []

    def cerrar_parrafo() -> None:
        if lineas:
            parrafos.append(" ".join(lineas))
            lineas.clear()

    for linea in texto.splitlines():
        contenido = linea.strip()
        if contenido == "Ley 20920" or contenido.startswith("Biblioteca del Congreso Nacional"):
            continue
        if not contenido or linea.startswith("     "):
            cerrar_parrafo()
        if contenido:
            lineas.append(contenido)
    cerrar_parrafo()
    return parrafos


def convertir(pdf: Path, destino: Path) -> dict[str, Any]:
    lector = PdfReader(pdf)
    paginas = [
        extraer_parrafos(pagina.extract_text(extraction_mode="layout")) for pagina in lector.pages
    ]
    primera = "\n".join(paginas[0])
    if "LEY NÚM. 20.920" not in primera or "Versión: Única De : 01-JUN-2016" not in primera:
        raise ValueError("El PDF debe corresponder a la Ley 20.920, versión 01-JUN-2016.")

    fecha = date.today().isoformat()
    sha256_pdf = hashlib.sha256(pdf.read_bytes()).hexdigest()
    texto = (
        "\n\n".join(
            f"[Página {numero}]\n\n" + "\n\n".join(parrafos)
            for numero, parrafos in enumerate(paginas, start=1)
        )
        + "\n"
    )
    fragmentos: list[dict[str, Any]] = []
    actual: dict[str, Any] | None = None
    partes: list[str] = []

    def cerrar_articulo() -> None:
        nonlocal actual
        if actual is not None:
            actual["texto"] = "\n\n".join(partes)
            fragmentos.append(actual)
            actual = None
            partes.clear()

    for numero_pagina, parrafos in enumerate(paginas, start=1):
        for parrafo in parrafos:
            if SECCION.fullmatch(parrafo) or parrafo.startswith("Habiéndose cumplido"):
                cerrar_articulo()
                continue
            coincidencia = ARTICULO.match(parrafo)
            if coincidencia:
                cerrar_articulo()
                numero = coincidencia[1]
                transitorio = numero in TRANSITORIOS
                identificador = f"transitorio-{numero}" if transitorio else f"articulo-{numero}"
                referencia = f"Artículo {numero}" + (" transitorio" if transitorio else "")
                actual = {
                    "id_fragmento": f"ley20920-{identificador}",
                    "documento": "Ley 20.920",
                    "referencia": referencia,
                    "url": "https://www.bcn.cl/leychile/navegar?idNorma=1090894",
                    "fecha_consulta": fecha,
                    "version_documento": "2016-06-01",
                    "archivo_pdf": ARCHIVO_PDF,
                    "sha256_pdf": sha256_pdf,
                    "paginas": [],
                }
            if actual is not None:
                partes.append(parrafo)
                if numero_pagina not in actual["paginas"]:
                    actual["paginas"].append(numero_pagina)
    cerrar_articulo()

    esperados = [f"ley20920-articulo-{numero}" for numero in range(1, 47)] + [
        f"ley20920-transitorio-{numero}" for numero in TRANSITORIOS
    ]
    if [fragmento["id_fragmento"] for fragmento in fragmentos] != esperados:
        raise ValueError("La extracción no conservó los 46 artículos y cuatro transitorios.")
    datos = {
        "documento": "Ley 20.920",
        "fecha_publicacion": "2016-06-01",
        "version_documento": "2016-06-01",
        "fecha_extraccion": fecha,
        "archivo_pdf": ARCHIVO_PDF,
        "sha256_pdf": sha256_pdf,
        "sha256_texto": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
        "paginas": len(paginas),
        "extractor": f"pypdf {pypdf.__version__}, modo layout",
        "tratamiento": (
            "Texto UTF-8 con párrafos reunidos y marcas editoriales [Página N]. "
            "Se retiran encabezados y pies repetidos. El TXT conserva preámbulo, "
            "secciones y cierre; el JSON contiene únicamente los artículos. "
            "El artículo 48 ter citado dentro del artículo 46 permanece dentro de este."
        ),
        "alcance": (
            "Copia aportada por el usuario, versión 2016-06-01. No verifica vigencia "
            "actual ni incorpora decretos, reglamentos u otras fuentes externas."
        ),
        "fragmentos": fragmentos,
    }
    destino.mkdir(parents=True, exist_ok=True)
    if pdf.resolve() != (destino / ARCHIVO_PDF).resolve():
        shutil.copyfile(pdf, destino / ARCHIVO_PDF)
    (destino / "ley_20920.txt").write_text(texto, encoding="utf-8")
    (destino / "ley_20920.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return datos


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--destino", type=Path, default=DESTINO)
    argumentos = parser.parse_args()
    datos = convertir(argumentos.pdf, argumentos.destino)
    print(f"Convertidas {datos['paginas']} páginas y {len(datos['fragmentos'])} artículos.")
    print(f"Archivos guardados en {argumentos.destino}.")


if __name__ == "__main__":
    main()
