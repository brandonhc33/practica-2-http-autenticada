# Comparación local de chunking — bloques 24 y 25

Ejecución del 16-11-2026 sobre la copia versionada de Ley REP. **Sin API,
embeddings ni generación.** Se usó el comando real:

```bash
uv run python -m scripts.indexar_corpus --comparar
```

Puede conservarse el JSON completo con `--salida archivo-nuevo.json`.
El comando incluye los chunks del artículo 9 para inspeccionar los cortes.

| Estrategia | Tamaño | Overlap | Documentos | Chunks | Caracteres chunks | Mín. / máx. | Texto no blanco perdido | Espacios de borde omitidos | Textos duplicados |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fijo | 400 | 50 | 50 | 164 | 58.393 | 55 / 400 | 0 | 0 | 0 |
| Fijo | 800 | 100 | 50 | 95 | 57.216 | 136 / 800 | 0 | 0 | 0 |
| Recursivo | 400 | 50 | 50 | 187 | 53.444 | 55 / 399 | 0 | 228 | 0 |
| Recursivo | 800 | 100 | 50 | 99 | 53.731 | 37 / 797 | 0 | 66 | 0 |

Corpus original: **52.727 caracteres**. El overlap repite texto; el splitter
limpia espacios de borde. La comprobación por offsets no confunde esos efectos
con pérdida de contenido significativo. Cada texto de chunk coincide exactamente
con su tramo del documento original.

## Lectura del artículo 9

- Fijo 400: un fragmento termina en `sistemas de ges` y el siguiente continúa el
  mismo tema. También corta dentro del párrafo sobre la exigibilidad.
- Fijo 800: corta tras `párrafo 3º de este título`, antes de la frase que explica
  cuándo será exigible la obligación.
- Recursivo 400: divide la obligación b) después de `decretos supremos que`; el
  fragmento siguiente solo conserva la continuación. Requiere recuperar ambos.
- Recursivo 800: el primer chunk conserva la definición y la inscripción; el
  segundo agrupa b), c) y d), incluida la frase sobre exigibilidad. La referencia
  al artículo se conserva en metadata, aunque el encabezado no se repita.

**Decisión provisional:** recursivo 800 / 100. Mejora esos límites frente a los
ejemplos inspeccionados y produce 99 chunks, sin texto significativo perdido.
No demuestra mayor precisión/recall: eso se medirá con embeddings reales.

**Límite visible:** el último chunk del artículo 9 contiene solo
`e) Las demás que establezca esta ley.` (37 caracteres). No se ocultó para aparentar
fragmentos uniformes. Un agrupado mínimo o un splitter jurídico puede evaluarse
después si la recuperación demuestra que hace falta; no se añade sin medir.

## Huellas de la configuración elegida

- Corpus: `fa577eca361dcd917a1ed51779f7a3c1f2e86d3167c55b610b796f5da4517ee6`.
- Chunks: `16db0a67715d21b66c3f34a61406866a7c19ff99947592b6487b8a1f655c0abf`.
- Índice previsto: `43559c52b3c6cae8f14afb38aec54afc2488393bd5c9f725b0c4b4f86c88f794`.

Los diez casos de evaluación se etiquetaron sobre estos chunks antes de cualquier
retrieval. Si cambia el corpus o el chunking, hay que revisar etiquetas y crear un
índice nuevo, no conservar los IDs por conveniencia.
