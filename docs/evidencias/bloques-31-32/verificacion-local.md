# Verificación local — bloques 31 y 32

**Alcance:** registros, filtro, servicio RAG, versiones de prompt, supervisión y matriz,
con índice, embeddings y modelos de prueba. Revisión del 24-11-2026 sobre `92679d7`, en
la rama local `bloques-31-32`, con Python 3.12.13.

## Comprobaciones ejecutadas

| Comando | Resultado |
| --- | --- |
| `uv run python -m pytest tests -q` | **407 pruebas y 698 subpruebas aprobadas**; 11 avisos de deprecación ya conocidos. |
| `uv run python -m tests` | **407 pruebas aprobadas**, ejecutor alternativo. |
| `uv run ruff check .` | Sin errores. |
| `uv run basedpyright` | 0 errores, 0 advertencias, 0 notas. |
| `git diff --check` | Sin errores de espacios. |
| `uv run python -m scripts.logging_rag` | Sin clave: 6 comprobaciones correctas. |
| `uv run python -m scripts.logging_rag --consultar ...` sin registro o sin `--confirmar-consumo` | Termina con error antes de crear el modelo o el archivo. |
| `uv run python -m scripts.registro_prompts` | Sin clave: dos huellas distintas y su diff. |
| `uv run python -m scripts.grafo_supervision demo` | Sin clave: ambos caminos; el prompt del proyecto no cambia. |
| `uv run python -m scripts.matriz_riesgos` | Sin clave: 8 riesgos, 0 problemas. |
| `git check-ignore output/observabilidad/x output/gobernanza/aprobaciones.sqlite` | Rutas ignoradas. |

La línea base del repositorio tenía 346 pruebas y 630 subpruebas. Se agregan **61
pruebas y 68 subpruebas**.

**Dependencias:** se declaran `langgraph`, ya instalado por LangChain, y
`langgraph-checkpoint-sqlite`. Son tres paquetes nuevos: `langgraph-checkpoint-sqlite`
3.1.3, `aiosqlite` 0.22.1 y `sqlite-vec` 0.1.9.

**Una corrida anterior falló.** Con el equipo sin memoria disponible, dos pruebas de
`test_ensayo_terminal.py` fallaron: 400 aprobadas en 183 segundos. Esas pruebas esperan
hasta 3 segundos a otro proceso. Tras reiniciar el equipo, sin cambiarlas, pasaron; la
suite completa tarda 9 segundos.

## Qué prueban las comprobaciones nuevas

- Cada evento es JSON con su `trace_id`; la traza se restaura aunque haya un error y no
  se mezcla entre hilos.
- Un campo no previsto se rechaza sin repetir su valor; el texto de una excepción no
  llega al registro.
- El filtro reconoce los ejemplos de la lección y variantes con tildes o caracteres
  invisibles, no descarta ninguno de los 99 fragmentos de la ley y **no** detecta letras
  separadas ni otras palabras.
- El servicio entrega solo respuestas con citas existentes, se abstiene sin llamar al
  modelo si no quedan fragmentos, controla los errores de cada etapa y no inventa tokens.
- v1 coincide con el prompt del B28; un texto alterado o repetido se rechaza; la versión
  activa está registrada; probar una versión no la activa.
- El grafo se pausa antes de aplicar, sobrevive a otro proceso, solo acepta booleanos y
  no decide dos veces. No aplica si cambió el archivo o la versión base.
- Un archivo con datos sensibles o fuera de `output/` no se puede proponer.
- La matriz rechaza valores fuera de 1 a 5, textos, filas ALTAS sin supervisión y
  archivos inexistentes.

Los modelos y documentos de prueba comprueban la mecánica, no la calidad real.
