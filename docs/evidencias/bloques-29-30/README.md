# Evidencias de personalización — bloques 29 y 30

## Procedencia y archivos

Todo lo de esta carpeta se generó **sin Gemini, sin clave y sin red** el
24-11-2026, en la rama local `bloques-29-30`, con `google-genai` 2.34.0. Cada
archivo es la salida completa del comando indicado.

| Archivo | Comando | Qué muestra |
| --- | --- | --- |
| [`dataset-validacion.txt`](dataset-validacion.txt) | `uv run python -m scripts.dataset_tuning --comprobar-validador --comprobar-api` | 24 ejemplos, balance 8/8/8, 0 problemas, 10 copias rotas detectadas y rechazo local de PEFT. |
| [`regla-local.txt`](regla-local.txt) | `uv run python -m scripts.linea_base_rutas --solo-regla-local` | La detección de artículos acierta 23 de 24; falla «resume art 27». |
| [`escenarios-previos.txt`](escenarios-previos.txt) | `uv run python -m scripts.decision_personalizacion` | Respuestas con evidencia y lo que recomendaría el método con cada resultado de la línea base. |
| [`verificacion-local.md`](verificacion-local.md) | Pruebas, ruff, basedpyright y unittest | Comprobaciones de la implementación. |

Huellas de los datos usados:

| Archivo | SHA-256 |
| --- | --- |
| `datos/personalizacion/rutas_ley_rep.json` | `a30841a8bf0bbd3b936f78ce3db8b5a942e0dcc371fcb7e58238aa5fa543b394` |
| `datos/personalizacion/hechos_decision.json` | `24926eb39a78da975a6434fc85b541341d4ca49f8c70c73d6a917cd3b134b310` |

Las consultas del dataset son **sintéticas** y sus etiquetas se propusieron con
asistencia de IA siguiendo las reglas R1 a R3. No provienen de usuarios reales.

## B29: dataset y validación

- **Tarea:** clasificar consultas en las rutas del B19 e identificar el artículo
  único nombrado. Es un problema de comportamiento consistente, no de información.
- **Balance:** normativa 8, resumen 8, aclaración 8; razón máxima/mínima 1,0.
- **Validación:** 0 problemas en el dataset real. Las diez copias rotas a propósito
  se detectaron: texto vacío, clave faltante, comillas simples, duplicado,
  etiqueta contradictoria, ruta inválida, resumen sin artículo, artículo
  inexistente, clave no prevista y menos de 10 ejemplos.
- **Envío del trabajo:** no se realizó. La API para desarrolladores rechaza
  `adapter_size` antes de enviar, y el inventario del 20-10-2026 no muestra
  modelos con `createTunedModel`.

## B30: hechos y escenarios antes de medir

| Pregunta | Respuesta | Evidencia |
| --- | --- | --- |
| ¿La información cambia seguido? | No | 0 cambios en 90 días: una versión de la ley y reglas sin cambios desde `df14a2c`. |
| ¿Falla el formato o el tono? | Pendiente | Requiere la línea base real. |
| ¿Dataset grande y de calidad? | No | 24 ejemplos; el criterio pide al menos 200. |
| ¿Presupuesto limitado o iterar rápido? | Sí | 0 intentos de entrenamiento disponibles con la API actual. |
| ¿Varias variantes? | No | Un solo flujo, idioma y corpus. |

Escenarios registrados antes de medir: si menos de 15 % de las respuestas
incumplen, el método da **RAG 2, PEFT 1, fine-tuning 0**; si 15 % o más, da
**PEFT 3, RAG 2, fine-tuning 1**.

## Pendiente

La línea base con Gemini, su revisión y el documento de decisión. Ver el
[checklist de la entrega](../../entregas/bloques-29-30.md#evidencias-y-checklist-de-cierre).
