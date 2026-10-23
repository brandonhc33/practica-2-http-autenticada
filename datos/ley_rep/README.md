# Fuente local de Ley REP

La fuente es el PDF aportado por el usuario: `Ley-20920_01-JUN-2016-1.pdf`. Se conserva una copia con el nombre [Ley-20920_01-JUN-2016.pdf](Ley-20920_01-JUN-2016.pdf).

El documento tiene 18 páginas y señala «Versión: Única De : 01-JUN-2016». La fecha de generación del PDF es el 22 de octubre de 2026; esa fecha no cambia la versión normativa declarada por el documento. Su enlace de procedencia es [Ley Chile, BCN](https://www.bcn.cl/leychile/navegar?idNorma=1090894).

| Archivo | Contenido |
| --- | --- |
| [ley_20920.txt](ley_20920.txt) | Texto completo en UTF-8, con marcas editoriales `[Página N]`. Conserva portada textual, preámbulo, títulos, artículos, transitorios y cierre. |
| [ley_20920.json](ley_20920.json) | Metadatos y 50 fragmentos: artículos 1 a 46 y cuatro transitorios. Cada fragmento conserva ID, referencia, texto, páginas, versión y hash del PDF. |

Se reunieron las líneas de cada párrafo y se retiraron los encabezados y pies repetidos de página. Las marcas de página son editoriales y no forman parte de la ley. El artículo 48 ter reproducido dentro del artículo 46 permanece en ese fragmento: no se interpreta como otro artículo de la Ley 20.920. El texto se extrajo con pypdf 6.21.2, sin OCR ni generación de contenido con IA.

Para reproducir la conversión desde la raíz del repositorio:

```bash
uv run --with pypdf==6.21.2 python scripts/extraer_ley_rep.py datos/ley_rep/Ley-20920_01-JUN-2016.pdf
```

El script también acepta la ruta del PDF original y `--destino` para escribir en otra carpeta. Registra la fecha de extracción y los hashes SHA-256 del PDF y del TXT. El cliente carga el JSON generado; no requiere pypdf ni acceso a la carpeta Downloads al realizar consultas.

Esta fuente permite estudiar y consultar la copia de 2016 aportada. No incorpora decretos, reglamentos, modificaciones ni una comprobación de vigencia actual. Una respuesta sobre la situación de una empresa o un período posterior puede necesitar otras fuentes y antecedentes.
