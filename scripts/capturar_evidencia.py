"""Captura con Chromium un visor local de una salida de comando conservada en texto."""

import argparse
import hashlib
import html
import math
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def buscar_chromium() -> Path:
    for nombre in ("chromium", "chromium-browser", "google-chrome"):
        ruta = shutil.which(nombre)
        if ruta:
            return Path(ruta)
    candidatos = sorted(
        (Path.home() / ".cache/ms-playwright").glob("chromium-*/chrome-linux*/chrome")
    )
    if candidatos:
        return candidatos[-1]
    raise SystemExit("Indica --chromium con la ruta a un ejecutable de Chromium o Chrome.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entrada", type=Path)
    parser.add_argument("--titulo", required=True)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--ultimas-lineas", type=int)
    parser.add_argument("--chromium", type=Path)
    args = parser.parse_args()
    if args.salida.exists():
        parser.error("La captura ya existe. Usa otra ruta para conservarla.")
    if args.ultimas_lineas is not None and args.ultimas_lineas < 1:
        parser.error("ultimas-lineas debe ser mayor que 0.")
    contenido = args.entrada.read_bytes()
    texto = contenido.decode("utf-8")
    lineas = texto.splitlines()
    visible = lineas[-args.ultimas_lineas :] if args.ultimas_lineas else lineas
    nota = (
        f"Últimas {len(visible)} líneas. La salida íntegra está en el archivo fuente."
        if len(visible) < len(lineas)
        else "Salida íntegra del archivo fuente."
    )
    huella = hashlib.sha256(contenido).hexdigest()
    fecha = datetime.fromtimestamp(args.entrada.stat().st_mtime, UTC).isoformat(timespec="seconds")
    comando = lineas[0] if lineas and lineas[0].startswith("$") else args.entrada.name
    documento = """<!doctype html><html lang="es"><meta charset="utf-8">
<title>{titulo}</title><style>
*{{box-sizing:border-box}}body{{margin:0;padding:40px;background:#edf1f5;color:#142536;
font-family:Arial,sans-serif}}main{{max-width:1520px;margin:auto}}.eyebrow{{color:#52677d;
font-size:15px;letter-spacing:1.4px;font-weight:700}}h1{{font-size:32px;margin:12px 0 16px}}
.meta{{font-size:14px;line-height:1.65;color:#4b5e70;overflow-wrap:anywhere}}
.comando{{margin:24px 0 0;background:#dfe7ee;padding:16px 20px;border-radius:8px 8px 0 0;
font:15px/1.6 'DejaVu Sans Mono',monospace;overflow-wrap:anywhere}}
pre{{margin:0;padding:24px;background:#101c2a;color:#e4edf6;border-radius:0 0 8px 8px;
font:15px/1.55 'DejaVu Sans Mono',monospace;white-space:pre-wrap;overflow-wrap:anywhere}}
footer{{font-size:13px;line-height:1.7;color:#52677d;margin-top:18px;overflow-wrap:anywhere}}
</style><main><div class="eyebrow">SKILLNEST · EVIDENCIA DE EJECUCIÓN</div>
<h1>{titulo}</h1><div class="meta">Fuente: {fuente}<br>Registrada: {fecha}<br>{nota}</div>
<div class="comando">{comando}</div><pre>{texto}</pre>
<footer>Captura del visor local de la salida registrada. No se recrearon resultados.<br>
SHA-256 del archivo fuente: {huella}</footer></main></html>""".format(
        titulo=html.escape(args.titulo),
        fuente=html.escape(str(args.entrada)),
        fecha=html.escape(fecha),
        nota=html.escape(nota),
        comando=html.escape(comando),
        texto=html.escape("\n".join(visible)),
        huella=huella,
    )
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    visor = args.salida.with_suffix(".html")
    visor.write_text(documento, encoding="utf-8")
    lineas_visuales = sum(max(1, math.ceil(len(linea) / 151)) for linea in visible)
    alto = max(700, 500 + lineas_visuales * 24)
    chromium = args.chromium or buscar_chromium()
    subprocess.run(
        [
            str(chromium),
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--hide-scrollbars",
            "--virtual-time-budget=1000",
            f"--window-size=1600,{alto}",
            f"--screenshot={args.salida.resolve()}",
            visor.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    if not args.salida.is_file():
        raise SystemExit("Chromium no generó la captura.")
    print(f"Captura: {args.salida} | fuente SHA-256: {huella}")


if __name__ == "__main__":
    main()
