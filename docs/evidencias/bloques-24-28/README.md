# Mediciones reales de RAG — bloques 24 a 28

## Procedencia y archivos

Ejecuciones autorizadas por el alumno el 16 de noviembre de 2026; los registros
usan UTC del **17-11-2026**. Código ejecutado:
`31c6af4ea08aeffabbe898a34e00e8fe85fb611c`, rama local `bloques-24-28`.
Se cargó el `.env` original con `uv run --env-file`, sin copiarlo ni imprimirlo.
No se usaron modelos falsos, respuestas de tests ni un índice simulado.

| Evidencia | Qué conserva |
| --- | --- |
| [Indexación](indexacion-01.json) | 50 documentos, 99 chunks, modelo, 3072 dimensiones, integridad y manifiesto completo. |
| [Recarga](recarga-01.json) | Otro proceso verificó el mismo índice sin crear embeddings. |
| [Evaluación TXT](resultados-evaluacion-02.txt) y [JSON](resultados-evaluacion-02.json) | Diez preguntas, k=3/5 y dos repeticiones; configuración y resultados por pregunta. |
| [`registros_latencia_costo.jsonl`](registros_latencia_costo.jsonl) | Las cuatro corridas reales de la actividad 28, con respuestas, fuentes, tiempos y uso de generación. |
| [Fuera del corpus](fuera-corpus-01.jsonl) | Quinta generación, separada: ensayo de abstención del B26. |
| [Manifiesto de copias](manifest.json) | Rutas runtime originales, tamaños y SHA-256; las seis salidas se copiaron byte a byte. |

Los comandos están en el [recorrido de entrega](../../entregas/bloques-24-28.md#recorrido-de-ejecución).
Las consultas son preguntas de estudio y las fuentes son la copia pública de la
ley. No se versionan claves, `.env`, SQLite ni vectores de Chroma.

## B24 y B25: índice y recarga

Se ejecutó `scripts.indexar_corpus --confirmar-consumo` con salida
`output/rag/indexacion-01.json`. Terminó con código 0 y `reutilizado: false`.
La recarga con `--verificar`, sin cargar la clave, terminó con código 0.

- Colección: `rag-ley-rep`, distancia coseno.
- Embeddings: `models/gemini-embedding-001`, dimensión 3072.
- Fragmentación: recursiva, 800 caracteres, overlap 100.
- Integridad: 99 IDs únicos, ningún texto duplicado ni carácter no blanco perdido;
  66 espacios de borde omitidos por el splitter.
- Misma huella en todas las salidas:
  `43559c52b3c6cae8f14afb38aec54afc2488393bd5c9f725b0c4b4f86c88f794`.

La comparación gratuita de cortes está [conservada aparte](comparacion-chunking.md).
No se ejecutó con cuota la réplica opcional de tienda del B25.

## B27: evaluación completada y resultados

**Resultado: evaluación real completada.** La ejecución `-02` terminó con código 0:
diez preguntas, k=3 y k=5, en dos repeticiones con resultados idénticos. Los
resultados completos están en [TXT](resultados-evaluacion-02.txt) y
[JSON](resultados-evaluacion-02.json). No se alteraron corpus, configuración,
preguntas ni etiquetas entre los intentos.

| k | Precisión promedio, 10 casos | Recall promedio, 9 casos definidos | Repetición |
| --- | ---: | ---: | --- |
| 3 | 0,30 | 1,00 | Mismos resultados en las dos corridas. |
| 5 | 0,18 | 1,00 | Mismos resultados en las dos corridas. |

Los nueve casos con respuesta tienen un único chunk etiquetado: cada uno se
recuperó dentro del top-3 y del top-5. Por caso, precisión fue 1/3 o 1/5 y recall
1. El décimo, fuera de corpus, tiene precisión 0 y recall `null`; no se incluye
en el promedio de recall. Se completaron 20 invocaciones de embedding de pregunta
en esta segunda ejecución, sin generaciones. El SDK puede reintentar internamente.

### Cómo se interpretan estos valores

La clase enseña a evaluar **qué evidencia llega al contexto**, no a medir todavía
si Gemini responde correctamente:

- **Precisión:** de los fragmentos recuperados, qué proporción coincide con los
  relevantes etiquetados. Con k=3, cada pregunta con respuesta obtuvo un acierto
  entre tres fragmentos: 1/3 ≈ 33,3 %.
- **Recall o exhaustividad:** de todos los relevantes etiquetados, qué proporción
  encontramos. Como cada una de esas preguntas tenía un único relevante y se
  recuperó, su recall fue 1/1 = 100 %. **No se contradice con la precisión: llegó
  la evidencia esperada, junto con dos fragmentos adicionales.**
- **Promedio 0,30:** nueve preguntas con precisión 1/3 y una fuera de corpus con
  precisión 0: `(9 × 1/3 + 0) / 10 = 0,30`. No significa «30 % de respuestas
  correctas». Con este etiquetado y tres resultados por pregunta, es el máximo
  posible de esa precisión promedio.
- **Promedio 0,18:** con k=5 se siguió encontrando el mismo relevante, pero entre
  cinco vecinos: `(9 × 1/5 + 0) / 10 = 0,18`. No se perdieron aciertos: aumentó
  el contexto sin añadir más relevantes etiquetados.
- **Recall promedio 1,00:** promedia solo las nueve preguntas con relevantes.
  La pregunta fuera del corpus tiene recall `null`/`n/a`, no cero: no existe
  evidencia pertinente que recuperar. Su abstención se evalúa por separado.
- **Repeticiones idénticas:** se observaron los mismos resultados sin cambiar el
  índice. Es evidencia de estabilidad en esas dos ejecuciones, no una garantía
  para cualquier pregunta futura.

**Decisión que permiten estos resultados:** entre k=3 y k=5, mantener k=3 conserva
la cobertura etiquetada con menos contexto adicional en esta muestra. No demuestra
el k óptimo general ni la veracidad de la respuesta generada. Para aprobar una
respuesta todavía hay que contrastar sus afirmaciones y citas con el texto.

Las etiquetas fueron propuestas por el asistente antes de retrieval y siguen
pendientes de revisión del alumno. Las métricas dependen de ese criterio: un
fragmento no etiquetado puede aportar contexto, pero no cuenta como acierto en
esta evaluación. No se afirma que el etiquetado sea jurídicamente exhaustivo.

La [guía de estudio desarrolla el cálculo paso a paso](../../estudio/bloques-24-28.md#cómo-se-interpretan-estos-valores),
incluye un caso real con sus IDs, decisiones de diagnóstico, el complemento F1
de la clase y un ejercicio de repaso.

### Antecedente: primer intento interrumpido

Este antecedente explica por qué los archivos finales llevan `-02`; **no deja
pendiente la ejecución del B27**.

El primer comando, con salida `resultados_evaluacion-01.txt` y su JSON, terminó
con código 1 y este diagnóstico:

```text
Evaluación interrumpida: GoogleGenerativeAIError; no se inventan métricas.
```

Ambos archivos runtime quedaron en cero bytes. No contienen una evaluación
parcial recuperable y no se presentan como resultados. El diagnóstico no conserva
código HTTP, pregunta de fallo ni número de solicitudes completadas: **no se
atribuye a un 429, timeout o cuota sin evidencia**, y su costo es desconocido.
Es una limitación del reporte agregado actual, no una corrida de costo cero.

Antes de repetir se hizo una única consulta diagnóstica real de embedding con la
primera pregunta del banco: devolvió un vector de 3072 dimensiones. No hubo
generación ni métricas de evaluación en ese diagnóstico.

## Actividad 28: tiempos, tokens y costo observado

Las cuatro líneas son reales, `estado: ok`, con tres preguntas distintas del B27.
Las tres primeras usan k=3; la cuarta repite la primera con k=6. Tiempos
redondeados a milisegundos en esta tabla; los decimales originales están en JSONL.

| Pregunta / k | Embedding ms | Búsqueda ms | Generación ms | Total ms | Tokens entrada / salida | USD generación estimada |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Objeto de la ley / 3 | 1271 | 1,50 | 1837 | 3117 | 1297 / 95 | 0,0006266 |
| Seis productos / 3 | 349 | 1,32 | 10469 | 10820 | 1402 / 120 | 0,0007206 |
| Metas y criterios / 3 | 1089 | 1,27 | 13630 | 14720 | 1237 / 177 | 0,0008136 |
| Objeto de la ley / 6 | 1154 | 1,48 | 11907 | 13063 | 2540 / 115 | 0,0010495 |

Conclusiones para entregar:

1. **El contexto cambió con la pregunta:** las primeras fuentes fueron,
   respectivamente, `ley20920-articulo-1-c000`, `ley20920-articulo-10-c000` y
   `ley20920-articulo-12-c000`; los mapas completos también son distintos.
2. **Subir k aumentó la entrada:** 1297 → 2540 tokens, **+1243 (+95,84 %)**.
   `caracteres_contexto` pasó de 2707 a 6206. La respuesta siguió citando el
   artículo 1; más contexto no aportó una mejora demostrada para esa pregunta.
3. **Generación dominó en las cuatro consultas**, no la búsqueda local. Sus tiempos
   variaron de 1,84 a 13,63 s: una comparación de solo dos corridas no permite
   atribuir toda la diferencia de latencia a k.
4. **Uso de generación informado:** 6476 tokens de entrada y 507 de salida,
   6983 en total. Subtotal estimado de las cuatro generaciones: **USD 0,0032103**.
   Incluyendo la abstención separada: **USD 0,0037690**, cinco generaciones.
   Son cálculos con tarifas de pago, no una factura ni el costo completo del RAG.
5. **Embeddings siguen desconocidos en tokens y costo real:** incluyen indexación,
   preguntas de evaluación, consultas, diagnóstico y el intento interrumpido.
   La aproximación por caracteres se rotula aparte; `costo_total_usd` sigue `null`.

El alcance del tiempo es una consulta con índice y clientes cargados. No incluye
instalación, arranque, carga inicial ni creación del índice. Cuatro muestras no
permiten informar p95, capacidad de producción ni un costo típico del dominio.

## B26: citas contrastadas y abstención

Revisión **asistida**, leyendo respuestas, mapas de fuentes y artículos originales;
no se atribuye una validación humana al alumno ni una revisión jurídica externa.

En la primera corrida, `02bf818323e44644b1731696a6409056`, se afirma:

> Busca proteger la salud de las personas y el medio ambiente [1].

La fuente `[1]` apunta a `ley20920-articulo-1-c000`, artículo 1, página 1,
versión `2016-06-01`. El [artículo original extraído](../../../datos/ley_rep/ley_20920.json)
incluye literalmente:

> con el fin de proteger la salud de las personas y el medio ambiente.

**Resultado del contraste:** afirmación respaldada, cita y referencia correctas.
También se revisó la enumeración de los seis productos contra el artículo 10 y
el instrumento y criterios de las metas contra el artículo 12. En las cuatro
respuestas legales no se encontraron números de cita inexistentes ni afirmaciones
contrarias a esos fragmentos. Es un control limitado a esta muestra.

La [pregunta fuera del corpus](fuera-corpus-01.jsonl), sobre impuesto a la renta
en 2027, respondió:

> No hay información suficiente en el contexto proporcionado para responder sobre la tasa del impuesto a la renta de las empresas chilenas.

**Criterio de abstención cumplido en esta corrida:** no inventó una tasa. Chroma
igualmente devolvió tres vecinos; eso no los convierte en evidencia tributaria.
El validador sintáctico marcó `sin_citas: true` y `referencias_validas: false`.
Es coherente con una abstención sin afirmaciones legales, no una cita inventada.
No se considera ese booleano una evaluación semántica de la abstención.

## Qué falta para cerrar administrativamente

Revisión del alumno de etiquetas y conclusiones, autorización de merge/push a
`main`, comprobación desde GitHub tras publicar y envío en la plataforma.
Estas mediciones no prueban vigencia normativa ni completan el proyecto final
multifuente. Ver el [checklist de entrega](../../entregas/bloques-24-28.md#evidencias-y-checklist-de-cierre).
