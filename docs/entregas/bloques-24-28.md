# Entrega de bloques 24 a 28 — RAG y actividad core 28

**Estado: implementación y mediciones reales completadas; entrega preparada para revisión.**
El índice, recarga, evaluación y las cuatro corridas de la actividad 28 se
ejecutaron con Gemini, más una prueba de abstención. Las citas se contrastaron
de forma asistida. Falta la revisión del alumno, publicación autorizada y envío
en la plataforma; no se declara enviada ni integrada en `main`.

Resultados y conclusión: [evidencias reales](../evidencias/bloques-24-28/README.md).

## Entregables y correspondencia

| Bloque | Archivos y resultado esperado |
| --- | --- |
| 24 | `src/rag/corpus.py`, `src/rag/indice.py`, `scripts/indexar_corpus.py`: 50 documentos, chunking, embeddings reales y Chroma persistente. |
| 25 | Integridad, manifiesto, recarga sin embeddings y réplica separada de tienda. La réplica es práctica no entregable según la lección. |
| 26 | `src/rag/recuperacion.py`: búsqueda por vector, prompt dinámico y mapa completo de fuentes; generación desde `scripts/registro_rag.py`. |
| 27 | `datos/evaluacion/recuperacion_rag.json`, `src/rag/evaluacion.py`, `scripts/evaluacion_recuperacion.py`: diez casos, precisión/recall por caso y promedio; TXT y JSON. |
| 28 | `src/rag/registro.py`, `scripts/registro_rag.py`: tres etapas y JSONL real por consulta, con uso, fuentes, costos conocidos y desconocidos. |

Plan y fuentes: [PRD 04](../planes/prd-04-rag-ley-rep.md).
Explicaciones y ejercicios: [guía de estudio](../estudio/bloques-24-28.md).
La API, las chains y el agente anterior no se reemplazan.

## Recorrido de ejecución

Desde la raíz de la copia que contiene `bloques-24-28`. No necesitas iniciar la
API. Cada archivo de salida debe ser **nuevo**; una colisión falla antes de hacer
llamadas. Los índices y registros de trabajo están ignorados por Git.

### 1. Preparación sin cuota

```bash
uv sync --locked
uv run python -m scripts.indexar_corpus --comparar
uv run python -m pytest tests -v
uv run ruff check .
uv run basedpyright
git diff --check
```

Lee la [comparación de cortes](../evidencias/bloques-24-28/comparacion-chunking.md) y
revisa los diez criterios de relevancia del JSON de evaluación **antes** del
retrieval. El etiquetado inicial fue propuesto por el asistente leyendo el corpus.

### 2. Indexación real del B24 y recarga del B25

El primer comando siguiente **envía los chunks de la copia pública de la ley a
Gemini y consume cuota**. Requiere `GEMINI_API_KEY` en el entorno o `.env`:

```bash
uv run python -m scripts.indexar_corpus --confirmar-consumo \
  --salida output/rag/indexacion-01.json
```

Resultado ya observado en la [indexación real](../evidencias/bloques-24-28/indexacion-01.json):
99 chunks de 3072 dimensiones, `estado: completo`, `reutilizado: false`.
En un proceso distinto, sin volver a generar embeddings:

```bash
uv run python -m scripts.indexar_corpus --verificar \
  --salida output/rag/recarga-01.json
```

Volver a indexar con configuración idéntica reutiliza el índice, sin API. Uno
incompatible o incompleto se rechaza. Para reconstruir usa una ruta nueva con
`--directorio output/rag/indice-02`, dentro de una carpeta ignorada; no se borran
índices automáticamente. Consulta y evaluación deben recibir esa misma ruta si
no es la predeterminada. No elijas una carpeta nueva sin ignorar sus binarios.

En un worktree, `.env` no se copia desde la carpeta original. Puedes anteponer
`uv run --env-file /ruta/a/tu/.env` en lugar de `uv run` en los comandos reales,
sin copiar el archivo ni mostrar su contenido.

**Réplica opcional del B25**, con cuota; no es requisito adicional de entrega:

```bash
uv run python -m scripts.indexar_corpus --corpus ejemplo --confirmar-consumo \
  --salida output/rag/replica-01.json
uv run python -m scripts.indexar_corpus --corpus ejemplo --verificar
```

Usa otra colección y otra carpeta. No introducir sus políticas en el índice de la
ley. La suite ya verifica esta mecánica con embeddings de prueba, gratuitamente.

### 3. Evaluación real del B27

```bash
uv run python -m scripts.evaluacion_recuperacion --k 3 5 --repeticiones 2 \
  --salida output/rag/resultados_evaluacion-01.txt --confirmar-consumo
```

Produce TXT y JSON del mismo nombre. Son **20 invocaciones de embedding de
pregunta**, sin generación: diez preguntas por dos repeticiones; los dos k usan
prefijos del mismo ranking. El SDK puede tener reintentos internos.

**Evaluación real completada:** la ejecución `-02` terminó las diez preguntas y
ambas repeticiones sin cambiar etiquetas. Ver [resultados del B27](../evidencias/bloques-24-28/README.md#b27-evaluación-completada-y-resultados).
El primer intento, `-01`, quedó documentado como antecedente separado; no es un
pendiente de ejecución.

Revisar precisión y recall por pregunta, promedios e igualdad de repeticiones.
Un recall bajo se documenta; no se cambian etiquetas para que coincidan con los
vecinos. La precisión no está obligada a bajar en todos los casos al subir k.
El caso sin respuesta tiene recall `n/a`.

### 4. Actividad 28: cuatro corridas reales

```bash
uv run python -m scripts.registro_rag --actividad-28 \
  --salida output/rag/registros_latencia_costo-01.jsonl --confirmar-consumo
```

El comando usa las tres primeras preguntas del conjunto B27 con k=3 y vuelve a
hacer la primera con k=6. Son cuatro embeddings de pregunta y cuatro generaciones,
sin reindexar. Cada resultado se escribe y vacía al archivo inmediatamente.
Ante un error guarda lo disponible y se detiene, sin repetir todo el flujo.

Cada línea incluye:

- `timestamp`, `pregunta`, `k`, configuración y huella del índice.
- `tiempos_ms`: `embed_query`, `busqueda_vectorial`, `generacion`.
- `tiempo_total_ms` de pared y `tiempo_etapas_ms`, con alcance explícito.
- Respuesta, mapa de fuentes y revisión limitada de números de cita.
- `tokens` del `usage_metadata` de generación, o `null` si no se informa.
- Costo estimado de generación y tarifas aplicadas; costo de embeddings
  desconocido, aproximación rotulada aparte y total completo `null`.

**No son costos de factura.** Las tarifas son referencias de pago. El conector
instalado no devuelve tokens de embeddings; no se presenta su costo como cero ni
el costo de generación como todo el costo del RAG.

Comprobación local de forma, sin otra llamada:

```bash
uv run python - <<'PY'
import json
from pathlib import Path

ruta = Path("output/rag/registros_latencia_costo-01.jsonl")
filas = [json.loads(linea) for linea in ruta.read_text().splitlines()]
assert len(filas) == 4
assert all(r["tipo_ejecucion"] == "real" and r["estado"] == "ok" for r in filas)
assert len({r["pregunta"] for r in filas}) == 3
assert [r["k"] for r in filas] == [3, 3, 3, 6]
assert filas[0]["pregunta"] == filas[3]["pregunta"]
for r in filas:
    assert r["tokens"] is not None, "Sin uso real informado, falta este criterio."
    assert all(t is not None and t >= 0 for t in r["tiempos_ms"].values())
    lenta = max(r["tiempos_ms"], key=r["tiempos_ms"].get)
    print(r["k"], r["tokens"]["input_tokens"], r["tiempo_total_ms"], lenta)
print("Entrada k=3:", filas[0]["tokens"]["input_tokens"])
print("Entrada k=6:", filas[3]["tokens"]["input_tokens"])
print("¿Creció?:", filas[3]["tokens"]["input_tokens"] > filas[0]["tokens"]["input_tokens"])
PY
```

Esta comprobación valida estructura y muestra la comparación. No demuestra por
sí misma procedencia real: hay que conservar y contrastar la ejecución.

Redactar la conclusión con los números observados:

1. ¿Cambió el contexto entre las tres preguntas?
2. ¿Cuánto aumentaron los tokens de entrada entre k=3 y k=6?
3. ¿Qué etapa dominó cada corrida? Si no fue generación, explicar lo observado.
4. ¿Qué subtotal de USD conocemos y qué partes siguen desconocidas?
5. ¿Hubo fallos, citas incorrectas o respuestas no respaldadas?

No deducir p95, rendimiento de producción ni un costo típico a partir de cuatro
corridas. No declarar un resultado favorable antes de medirlo.

La [conclusión con los números reales](../evidencias/bloques-24-28/README.md#actividad-28-tiempos-tokens-y-costo-observado)
ya responde estas preguntas: entrada 1297 → 2540 tokens al subir k, generación
dominante en las cuatro corridas y USD 0,0032103 de generación estimada, sin
confundirlo con factura o costo completo.

### 5. Abstención y revisión de una cita del B26

La actividad 28 ya proporciona tres preguntas y contextos que pueden compararse.
Para el caso fuera de corpus, una generación adicional con cuota:

```bash
uv run python -m scripts.registro_rag \
  "¿Cuál es la tasa del impuesto a la renta de las empresas chilenas para el año 2027?" \
  --salida output/rag/fuera-corpus-01.jsonl --confirmar-consumo
```

Debe reconocer información insuficiente, no inventar el impuesto. Conservar el
resultado aunque falle el criterio.

Elegir una afirmación de las cuatro respuestas de la actividad, seguir `[N]` al
mapa `fuentes` y contrastarla con el chunk y artículo original. Guardar la
afirmación, ID, texto de respaldo y conclusión de la revisión. Que el número de
cita exista **no** garantiza ese respaldo.

## Evidencias y checklist de cierre

Lo generado en `output/rag/` es local y puede contener consultas completas. No
introducir datos privados. Solo copiar a `docs/evidencias/bloques-24-28/` las
corridas reales revisadas, sin claves, binarios de Chroma ni registros de tests.
No mezclar resultados ficticios para completar el JSONL.

- [x] Material de los cinco bloques y actividad 28 analizados y planificados.
- [x] Código de indexación, recuperación, evaluación e instrumentación.
- [x] Comparación local de cortes e integridad del corpus.
- [x] Diez casos propuestos antes del retrieval; pendiente revisión del alumno.
- [x] Tests con Chroma local, recarga en otro proceso y modelos falsos.
- [x] Autorización del alumno para las pruebas reales, sin copiar ni mostrar su `.env`.
- [ ] Revisión del alumno de las etiquetas iniciales y conclusiones.
- [x] Índice real y recarga real del B24/25.
- [x] Evaluación real de diez preguntas, k=3/5 y dos repeticiones.
- [x] Cuatro líneas reales de la actividad 28 y comparación de tokens k=3/6.
- [x] Abstención real y cita contrastada de forma asistida; conclusiones con tiempos y costos.
- [x] Evidencias reales revisadas y conservadas con manifiesto; estado y checklist actualizados.
- [ ] Merge/push autorizado de esta ampliación a `main`, sin publicar la rama de bloques.
- [ ] Instalación desde clon limpio y enlace/entrega en la plataforma.

Las comprobaciones automáticas de esta versión se detallan en
[verificación local](../evidencias/bloques-24-28/verificacion-local.md).
No se puede enviar la actividad desde la copia estática del curso; el alumno
debe presentar el enlace o los archivos en la plataforma que corresponda.

## Qué presentar en la actividad 28

1. [`scripts/registro_rag.py`](../../scripts/registro_rag.py), dentro del proyecto:
   importa módulos de `src/` y no se ejecuta como archivo aislado.
2. [`registros_latencia_costo.jsonl`](../evidencias/bloques-24-28/registros_latencia_costo.jsonl),
   con las cuatro corridas reales y los tokens informados por Gemini.
3. [Conclusiones y trazabilidad](../evidencias/bloques-24-28/README.md), junto con
   la [evaluación del B27](../evidencias/bloques-24-28/resultados-evaluacion-02.txt).

Se prepara el ZIP local `output/entrega-bloques-24-28.zip` desde el árbol
versionado del proyecto completo, con las evidencias revisadas. Está ignorado
por Git y no contiene `.env`, `.venv`, `output/`, `.git` ni `vectorstore/`.
La regla `export-ignore` de `.gitattributes` excluye `output/`, incluso el ZIP
histórico del B13–14 que ya estaba versionado; no se borra ese antecedente.
La actividad pide ejecución con una clave propia: el índice se reconstruye,
no se distribuye el almacenamiento binario de Chroma.

El paquete local no implica publicación ni envío. Para presentar un enlace de
`main`, primero falta autorizar e integrar esta ampliación.
