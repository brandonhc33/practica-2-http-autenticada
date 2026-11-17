# Verificación local — bloques 24 a 28

**Alcance:** implementación, integridad, persistencia y contratos; no calidad
semántica ni mediciones reales de Gemini. Revisión iniciada el 16-11-2026 sobre
`607c61f`, en la rama local `bloques-24-28`.

## Comprobaciones ejecutadas

| Comando | Resultado |
| --- | --- |
| `uv sync --locked` | Correcto, dependencias instaladas desde el lock. |
| `uv run python -m pytest tests -v` | **303 pruebas y 588 subpruebas aprobadas**; 11 avisos de deprecación del historial anterior, no fallos del RAG. |
| `uv run python -m tests -v` | **303 pruebas aprobadas**, ejecutor alternativo. |
| `uv run ruff check .` | Sin errores. |
| `uv run basedpyright` | 0 errores, 0 advertencias, 0 notas. |
| `git diff --check` | Sin errores de whitespace. |
| `uv run python -m scripts.indexar_corpus --comparar` | Cuatro configuraciones e integridad comprobadas; ver [comparación](comparacion-chunking.md). |
| `uv run python -m scripts.indexar_corpus --help` | Entrada y opciones disponibles sin clave ni API. |
| `uv run python -m scripts.evaluacion_recuperacion --help` | Entrada y opciones disponibles sin clave ni API. |
| `uv run python -m scripts.registro_rag --help` | Entrada y opciones disponibles sin clave ni API. |
| `git check-ignore vectorstore/prueba output/rag/prueba` | Ambas rutas ignoradas. |

La línea base tenía 263 pruebas y 481 subpruebas. Se agregan **40 pruebas y 107
subpruebas**. La comparación del lock no encontró cambios de versión en ningún
paquete previamente bloqueado; se añadieron Chroma y sus dependencias y se hizo
explícita la del splitter existente.

Una ejecución que encadenaba pytest y unittest alcanzó el timeout del terminal
después de que pytest terminara correctamente. Se volvió a ejecutar unittest por
separado y terminó en `OK`. Otra cadena de comprobaciones terminó por tiempo tras
tipos y dos ayudas; la tercera ayuda se ejecutó por separado. No se presentan las
cadenas interrumpidas como validaciones completas.

## Qué prueban las comprobaciones nuevas

- Ley real: 50 documentos, 99 chunks, fuentes y offsets, sin mezcla de artículos,
  sin chunks vacíos/duplicados ni texto no blanco perdido.
- Configuraciones inválidas, pérdida de contenido y metadata incompleta.
- Chroma real en directorios temporales, con embeddings deterministas de prueba.
- Recarga desde otro proceso con las conexiones de red bloqueadas.
- Reutilización sin recalcular vectores; rechazo de ausencia, corrupción,
  incompatibilidad, dimensión incorrecta y creación interrumpida.
- Conector de embeddings real con cliente SDK simulado: tareas de documento y
  consulta, dimensión 3072 y timeout configurado; sin petición de red.
- Un embedding y una generación por consulta a nivel de invocaciones del flujo;
  tiempos separados y contenido del prompt.
- Citas inexistentes o ausentes, sin pretender probar respaldo semántico.
- Tokens ausentes distintos de cero, costo completo desconocido, consumo conservado
  cuando llega una respuesta vacía.
- Errores por etapa, salida parcial y ausencia de repetición del flujo.
- Precisión/recall con duplicados, vacíos y etiquetas obsoletas; comparación de
  prefijos k=3/5 y repetición.
- CLI de actividad 28: cuatro corridas, tres preguntas, k=3/6; colisión de archivo,
  conservación de líneas anteriores y parada al fallar.

Los resultados falsos de los tests viven solo en temporales y **no se publican
como evidencia real**. La suite pytest bloquea conexiones mediante
`tests/conftest.py`. La recarga en subproceso bloquea sus propias conexiones.
No se generaron embeddings reales ni respuestas reales para esta revisión.

## Instalación independiente desde snapshot local

Se exportó con `git archive` el árbol preparado
`a1066fcd103668de16c379269a1577bcefe438dd` a una carpeta temporal nueva, sin `.env`,
`.venv`, índice ni registros runtime. Es una copia de los archivos de esta
implementación, **no un clon desde GitHub**.

Se creó allí otro entorno virtual mediante `uv sync --locked`, con las variables
de credenciales retiradas del entorno de validación y el tracing externo
deshabilitado. En esa copia se ejecutaron:

```bash
uv sync --locked
uv run python -m pytest tests -v
uv run ruff check .
uv run basedpyright
uv run python -m scripts.indexar_corpus --comparar
```

Resultado: **303 pruebas y 588 subpruebas aprobadas**, 11 avisos heredados; ruff
correcto, tipos sin errores y los mismos cuatro resultados de chunking.
Al terminar seguían ausentes `.env`, `vectorstore/` y `output/rag/`. La prueba
confirma instalación reproducible local sin secretos ni datos generados, no
conexión real con Gemini. Después solo se añade esta constancia documental.

## Fuera del alcance de esta verificación inicial

La revisión inicial no ejecutó índice real, evaluación semántica, abstención ni
las cuatro mediciones del B28. Esos pasos se realizaron después y están en el
[registro de corridas reales](README.md), separados de las pruebas con fakes.
No se hizo merge/push ni clon desde GitHub de esta ampliación. Esta verificación
no es evidencia de CI ni de actividad enviada en la plataforma.

Ver el [checklist de entrega](../../entregas/bloques-24-28.md#evidencias-y-checklist-de-cierre).

## Continuación: evidencias reales y orden documental

Tras autorizar las corridas reales se reorganizó `docs/` por propósito, con
un [índice por carpetas y bloques](../../README.md). Las mediciones no cambiaron
`src/`, `scripts/`, `tests/`, el corpus, las etiquetas ni las dependencias respecto
de `31c6af4`. Se conservaron los artefactos de evaluación y capturas históricas;
las dos imágenes trasladadas conservan exactamente los bytes originales.

Se repitieron las comprobaciones en esta continuación:

| Comprobación | Resultado |
| --- | --- |
| `uv run python -m pytest tests -v` | 303 pruebas y 588 subpruebas aprobadas en 10,27 s; 11 avisos de deprecación heredados. |
| `uv run python -m tests -v` | 303 pruebas, `OK`, 7,336 s. |
| `uv run ruff check .` | Correcto. |
| `uv run basedpyright` | 0 errores, 0 advertencias, 0 notas. |
| `git diff --check` | Sin errores. |
| Enlaces y anclas Markdown | Parseados con `MarkdownIt`; rutas locales y anclas de encabezados verificadas, sin enlaces rotos. |
| Copias de evidencia real | Seis archivos cotejados byte a byte con `output/rag/` y con los tamaños y SHA-256 del manifiesto. |
| Esquema de actividad 28 | Cuatro líneas reales exitosas, tres preguntas, k=3/3/3/6, uso informado y tres tiempos no negativos por corrida. |

No se volvió a ejecutar una instalación desde GitHub: la rama de bloques
continúa local y falta autorización para publicar esta ampliación. Los detalles
del fallo real inicial y los límites de los costos están en el [reporte real](README.md);
no se mezclan con resultados de la suite.
