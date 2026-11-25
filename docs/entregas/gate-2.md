# Entrega del Gate 2 — integración y orquestación

**Estado: servicio implementado, medido con Gemini y probado desde una instalación limpia.**
Norma y prompt aprobados, una respuesta entregada con revisión y corrida final correcta. La
publicación se registra en el [checklist](#checklist-de-cierre).

Plan y criterios: [PRD 08](../planes/prd-08-gate-2.md). Explicaciones:
[guía de estudio](../estudio/gate-2.md). Instalación y uso:
[README](../../README.md#servicio-rag-del-gate-2).

## Qué se entrega

| Pieza que pide el curso | En este proyecto |
| --- | --- |
| Índice persistido y actualización incremental | [`indice_normas.py`](../../src/rag/indice_normas.py) y [`normas.py`](../../src/rag/normas.py): 233 fragmentos de dos normas. |
| Recuperación con citas y métricas propias | [`servicio.py`](../../src/rag/servicio.py), [27 preguntas](../../datos/evaluacion/recuperacion_normas.json) y [resultado](../evidencias/gate-2/evaluacion-gemini.txt). |
| Costo y latencia, con corrida real | Tiempos por etapa, tokens y costo en cada evento; [consumo medido](../evidencias/gate-2/prueba-prompts-resultado.md#consumo) y [checklist operativo](#checklist-operativo). |
| Decisión de personalización | [Documento con matriz de puntaje](../arquitectura/decision-personalizacion.md). |
| Registros y consumo con `trace_id` | [`trazas.py`](../../src/observabilidad/trazas.py); ejemplo en el [ensayo](../evidencias/gate-2/ensayo.txt). |
| Filtro de inyección sobre documentos reales | [`inyeccion.py`](../../src/observabilidad/inyeccion.py), aplicado a `Document` de LangChain antes del prompt. |
| Versiones de prompt y supervisión | [`prompts_rag.json`](../../datos/gobernanza/prompts_rag.json), con tres versiones, y [`supervision.py`](../../src/gobernanza/supervision.py). |
| Matriz de riesgos | [Nueve riesgos](../arquitectura/matriz-riesgos.md); los cinco ALTO y CRITICO, con supervisión. |
| README | [Servicio RAG del Gate 2](../../README.md#servicio-rag-del-gate-2). |

## Las cuatro condiciones no compensables

| Condición | Cómo se comprueba | Resultado |
| --- | --- | --- |
| Corre sin excepciones | `test_1`; un fallo del proveedor termina en un mensaje controlado. | Cumple |
| Cada respuesta cita su fuente | `test_2`; sin cita válida se abstiene y lista lo consultado. | Cumple |
| Registros sin contenido sensible | `test_3`; lista cerrada de campos, y datos ocultos antes del proveedor. | Cumple |
| Supervisión real sobre la acción de mayor riesgo | `test_4`; pausa la **entrega de una respuesta a un cliente**. | Cumple |

La cuarta usa la acción del mayor riesgo de la matriz: entregar una respuesta que cita un
artículo real, pero cambia lo que dice.

## Recorrido de ejecución

Los comandos están en el [README](../../README.md#servicio-rag-del-gate-2). Sin clave:
`python servicio_rag.py`, `python -m pytest test_gate2.py -v`, `python -m scripts.evaluar_normas`,
`python -m scripts.matriz_riesgos` y `python -m scripts.autoevaluacion_gate2`.

### Verificación manual por criterio

| Criterio | Comando | Esperado |
| --- | --- | --- |
| 1 | `python servicio_rag.py; echo $?` | `0` |
| 2 | `python servicio_rag.py \| grep -i fuentes` | Al menos una línea |
| 3 | `grep -ri ana.perez output/servicio/` | Ninguna línea |
| 4 | `python -m scripts.grafo_supervision demo` | Pausa, rechazo y aprobación |

## Resultados

| Medición | Resultado | Criterio previo |
| --- | --- | --- |
| Una norma: evidencia entre los 5 primeros | **21 de 21** | 90 %: cumple |
| Dos normas: evidencia de ambas | **2 de 4** | 3 de 4: **no cumple** |
| Preguntas de la ley tras agregar el decreto | Exhaustividad 1,00, igual que en el B27 | No perder: cumple |
| Prompt 3 | Seis de seis casos, igual que la versión 2 | No empeorar: cumple |
| Agregar el decreto | 134 embeddings; los 99 vectores de la ley, idénticos | Solo lo nuevo: cumple |

**Por qué fallan las cruzadas:** los cinco lugares se reparten por cercanía y pueden quedar
todos en una norma. La solución prevista es reservar cupos por norma. No se aplicó, porque
corregirlo mirando las mismas cuatro preguntas no demostraría una mejora: se medirá en el
Gate 3 con preguntas nuevas.

## Registro del ensayo funcional

| Encontrado | Corregido |
| --- | --- |
| Las tablas de metas del PDF son imágenes: el texto extraído no traía ninguna. | Transcripción aparte, filas completas, pruebas y revisión antes de activar. |
| El primer extractor mezclaba líneas en el artículo 30. | Otro, por posición de línea, contrastado palabra por palabra con `pdftotext`. |
| El proveedor cortó la indexación a los 100 fragmentos. | El índice quedó cerrado y continuó con los 34 restantes; ahora se anota cada interrupción. |
| La pregunta con un correo llegaba al proveedor, aunque no se registrara. | Se oculta antes del embedding. |
| «Artículo 21» no distingue entre dos normas. | Las fuentes nombran la norma. |
| Se podía pedir la entrega de un borrador hecho con un prompt en prueba. | Solo con la versión activa. |
| Cambiar la fuente de un fragmento altera su vector en el orden de 1e-9. | Es redondeo de Chroma; la prueba lo admite. |

## Checklist operativo

- [x] Clave solo en `.env`, ignorado por Git; los mensajes de error no muestran contenido.
- [x] Índice con manifiesto, modelo y dimensiones comprobados al abrir.
- [x] Interrupción recuperable y sin respuestas a medias.
- [x] Modelo de respuesta y tarifas declarados; tiempo límite en el cliente.
- [x] Cada consulta con costo estimado; los embeddings quedan como costo desconocido.
- [x] Retiro de una norma sin reconstruir el índice.
- [ ] Alertas, panel y plazo de retención de registros: Gate 3.
- [ ] Autenticación de quien aprueba: Gate 3.

## Checklist de cierre

- [x] Tres lecciones del Gate 2 analizadas y planificadas.
- [x] DS 12/2020 desde la publicación oficial, con hash y tablas transcritas.
- [x] Norma revisada y aprobada en la terminal.
- [x] Índice real en dos pasos y recuperación real medida.
- [x] Versiones 2 y 3 del prompt comparadas con criterios previos.
- [x] Instalación limpia con `pip`, ensayo y cuatro pruebas.
- [x] Riesgo nuevo revisado y versión vigente del decreto revisada en LeyChile.
- [x] Decisión sobre la versión 3 del prompt: aprobada y activa.
- [x] [Corrida final](../evidencias/gate-2/corrida-final.md) y `test_gate2.py` con Gemini.
- [x] Entrega real pausada, revisada y aprobada en la terminal.
- [x] [Autoevaluación](../evidencias/gate-2/autoevaluacion.txt) revisada: 90,9 y los cuatro no compensables.
- [ ] Integración y publicación de `main`; clon limpio.
- [ ] Presentación en Skillnest.

El alcance, las fuentes y las evidencias se prepararon con asistencia de IA.
