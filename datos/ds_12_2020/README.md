# Fuente del DS 12/2020

Decreto supremo 12 de 2020 del Ministerio del Medio Ambiente: metas de recolección y
valorización y otras obligaciones asociadas de **envases y embalajes**.

| Archivo | Contenido |
| --- | --- |
| [DS-12-2020_DO-16-MAR-2021.pdf](DS-12-2020_DO-16-MAR-2021.pdf) | Publicación firmada del Diario Oficial: 22 páginas, CVE 1910141. |
| [tablas.json](tablas.json) | Transcripción de las cuatro tablas que el PDF trae como imágenes. |
| [ds_12_2020.txt](ds_12_2020.txt) | Texto corrido, con vistos y considerandos. |
| [ds_12_2020.json](ds_12_2020.json) | 47 artículos y 6 transitorios, con página, versión, enlace y hash. |

- **Origen:** [Diario Oficial, 16-03-2021](https://www.diariooficial.interior.gob.cl/publicaciones/2021/03/16/42906/01/1910141.pdf),
  consultado el 24-11-2026. El [texto de LeyChile](https://www.bcn.cl/leychile/navegar?idNorma=1157019)
  no admitió lectura automática.
- **Hash SHA-256 del PDF:** `a9f712fdc83007f1655d6280530ac21a939b1404946f2e22a68284badae4fdf7`.

## Conversión

```bash
uv run --with pymupdf==2.1 python -m scripts.extraer_ds12
```

El cliente usa los archivos generados: PyMuPDF solo se necesita para convertir. Se
retiran encabezados, pies, títulos de sección y firmas.

**Comprobaciones:** se contrastaron las palabras con otra herramienta (`pdftotext`). Solo
faltan los títulos de sección; los subíndices de las fórmulas quedan unidos al símbolo.
En el artículo 30, la publicación dice «E SGSPAIi» en un párrafo y «END SGSPAIi» en otro:
se conserva así.

## Tablas

Los artículos 21, 23, 35 y 36 contienen **imágenes**: sin transcribirlas, el asistente no
podría citar ninguna meta. Cada fila se escribió como una frase completa, para que un
corte no la separe de su categoría y su material.

La transcripción se hizo con asistencia de IA, en dos lecturas que coincidieron. El OCR
disponible confirmó solo parte de las celdas. La norma se aprobó en la terminal, donde
`grafo_supervision decidir` muestra las cuatro tablas para contrastarlas con la publicación
(`activar_norma-02a1e3917417`).

## Alcance y vigencia

Es el texto publicado en 2021. Se revisó a mano en LeyChile el 24-11-2026 y mostraba una
**versión única**; una búsqueda del mismo día tampoco encontró un decreto modificatorio.
Hay que repetirlo antes de usar el asistente en otra fecha.

Sí se encontró que el Ministerio lo interpretó mediante el oficio circular In. Ad. 1 de
2025, y que la
[Res. Ex. 4.910, de 31-08-2026](https://www.diariooficial.interior.gob.cl/publicaciones/2026/09/07/44544/01/2866033.pdf),
inició un procedimiento para resolver si esa interpretación se invalida. Trata de qué residuos puede
usar un GRANSIC para cumplir sus metas. **Nada de eso está en el corpus.**
