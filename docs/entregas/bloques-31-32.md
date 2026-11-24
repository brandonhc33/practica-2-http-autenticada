# Entrega de bloques 31 y 32 — observabilidad, seguridad y gobernanza

**Estado: implementación, pruebas y medición de las dos versiones del prompt
completadas.** La matriz está revisada, la segunda versión del prompt, activa, y
`main`, publicado. Actividades listas para presentar.

Plan y fuentes: [PRD 07](../planes/prd-07-observabilidad-gobernanza.md).
Explicaciones y ejercicios: [guía de estudio](../estudio/bloques-31-32.md).
Matriz: [documento](../arquitectura/matriz-riesgos.md).
Evidencias: [resultados conservados](../evidencias/bloques-31-32/README.md).
La API, las chains, el agente y la medición del B28 no se modifican.

## Entregables y correspondencia

| Actividad | Pide el curso | En este proyecto |
| --- | --- | --- |
| 31, core | `logging_rag.py`: logs JSON con `trace_id`, consumo y filtro de inyección en el flujo RAG. | [`scripts/logging_rag.py`](../../scripts/logging_rag.py), con [`src/observabilidad/`](../../src/observabilidad/trazas.py) y [`src/rag/servicio.py`](../../src/rag/servicio.py). |
| 32, paso 1 | `registro_prompts.py`: dos versiones reales, huella, nota y diff. | [`scripts/registro_prompts.py`](../../scripts/registro_prompts.py), con [`prompts_rag.json`](../../datos/gobernanza/prompts_rag.json): v1 `18db60ea8163` y v2 `fa9063213deb`. |
| 32, paso 2 | `grafo_supervision.py`: `interrupt()`, aprobación y rechazo. | [`scripts/grafo_supervision.py`](../../scripts/grafo_supervision.py), con [`supervision.py`](../../src/gobernanza/supervision.py). |
| 32, paso 3 | `matriz_riesgos.py`: cinco riesgos propios o más. | [`scripts/matriz_riesgos.py`](../../scripts/matriz_riesgos.py): ocho riesgos. |

## Recorrido de ejecución

Desde la raíz del proyecto. No hace falta iniciar la API.

### 1. Sin cuota, clave ni red

```bash
uv sync --locked
uv run python -m scripts.logging_rag
uv run python -m scripts.registro_prompts
uv run python -m scripts.grafo_supervision demo
uv run python -m scripts.matriz_riesgos
uv run python -m pytest tests -v
uv run ruff check .
uv run basedpyright
git diff --check
```

Resultados observados:

- `logging_rag`: 6 comprobaciones correctas. Usa el servicio real con un índice,
  embeddings y modelo de prueba.
- `registro_prompts`: dos huellas distintas; la diferencia son tres líneas agregadas.
- `grafo_supervision demo`: pausa, rechazo y aprobación **simulados** sobre copias
  temporales. El prompt del proyecto no cambia.
- `matriz_riesgos`: 8 riesgos, 0 problemas; 3 CRITICO, 1 ALTO y 4 MEDIO.

### 2. Consulta real (opcional en la actividad)

**Consume cuota:** un embedding y una generación por pregunta. Requiere el índice
del B25 en `vectorstore/` y `GEMINI_API_KEY`. El registro debe ser un archivo nuevo.

```bash
uv run python -m scripts.logging_rag --confirmar-consumo \
  --registro output/observabilidad/eventos-v1.jsonl \
  --consultar "¿Qué es un productor de un producto prioritario?"
```

Con `--prompt fa9063213deb` se prueba la versión 2 **sin activarla**. El archivo
guarda los eventos; la pregunta y la respuesta solo se muestran en la terminal.

Resultado observado con cinco preguntas por versión: ambas cumplen los cinco casos.
US$ 0,0070126 estimados en las diez generaciones; ver el
[resultado](../evidencias/bloques-31-32/prueba-prompts-resultado.md).

Orden escondida en un documento, con una generación por versión y sin embeddings:

```bash
uv run python -m scripts.ensayo_inyeccion_indirecta --confirmar-consumo \
  --registro output/observabilidad/eventos-orden.jsonl
```

Resultado observado: ninguna versión obedeció; ver el
[resultado](../evidencias/bloques-31-32/orden-escondida-resultado.md).

### 3. Activar una versión del prompt

La decisión la toma una persona en su terminal. Este fue el recorrido con v2, que ya
está activa: repetirlo con la misma huella responde «Esa versión ya está activa».

```bash
uv run python -m scripts.grafo_supervision proponer-prompt fa9063213deb
uv run python -m scripts.grafo_supervision pendientes
uv run python -m scripts.grafo_supervision decidir HILO
```

`proponer-prompt` pausa la acción y escribe el `HILO` que se usa en `decidir`. Este
muestra el diff y pregunta `[s/n]`. Cualquier otra respuesta deja la solicitud
pendiente. Si se aprueba, cambia `datos/gobernanza/prompt_activo.json`; la decisión
queda en `output/gobernanza/decisiones.jsonl`, que no se publica.

### 4. Publicar un registro real como evidencia

```bash
uv run python -m scripts.grafo_supervision proponer-evidencia \
  output/observabilidad/eventos-v1.jsonl docs/evidencias/bloques-31-32/eventos-v1.jsonl
uv run python -m scripts.grafo_supervision decidir HILO
```

Antes de pausar se buscan correos, RUT, teléfonos y claves. No prueba que no haya
otros datos personales: por eso decide una persona.

## Evidencias y checklist de cierre

- [x] Material de los bloques 31 y 32 y sus actividades analizados y planificados.
- [x] Logs JSON con `trace_id`, consumo y filtro de inyección en el flujo RAG.
- [x] Un documento limpio y uno con inyección probados; aislamiento de dos consultas.
- [x] Registros sin pregunta, respuesta, fragmentos ni datos personales.
- [x] Dos versiones reales del prompt, con huella, nota y diff.
- [x] Grafo con pausa, aprobación y rechazo, y un hilo por solicitud.
- [x] Ocho riesgos propios, con supervisión en los cuatro ALTO y CRITICO.
- [x] Suite completa, ruff, basedpyright y ejecutor de unittest.
- [x] Salidas de los cuatro comandos conservadas con huellas.
- [x] Revisión de las estimaciones de la matriz.
- [x] Prueba real de las dos versiones del prompt, con el criterio escrito antes.
- [x] Orden escondida que el filtro no reconoce, probada con ambas versiones.
- [x] Decisión sobre la versión 2 en la terminal: aprobada y activa.
- [x] Ampliación integrada y publicada en `main`, sin publicar la rama de bloques.
- [x] Instalación desde un clon limpio de GitHub: [verificación](../evidencias/bloques-31-32/verificacion-github.md).
- [ ] Presentación de las actividades en Skillnest.

Las comprobaciones de esta versión se detallan en la
[verificación local](../evidencias/bloques-31-32/verificacion-local.md).

## Qué presentar

**Actividad 31, core:** [`scripts/logging_rag.py`](../../scripts/logging_rag.py) y su
[salida](../evidencias/bloques-31-32/logging-ensayo.txt).

**Actividad 32:** los tres archivos que pide,
[`registro_prompts.py`](../../scripts/registro_prompts.py),
[`grafo_supervision.py`](../../scripts/grafo_supervision.py) y
[`matriz_riesgos.py`](../../scripts/matriz_riesgos.py), con la
[matriz](../arquitectura/matriz-riesgos.md).

Los scripts importan módulos de `src/`: conviene presentar el enlace al repositorio.
