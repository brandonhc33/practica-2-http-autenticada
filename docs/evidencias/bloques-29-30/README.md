# Evidencias de personalización — bloques 29 y 30

## Procedencia y archivos

Generadas el 24-11-2026 en la rama local `bloques-29-30`, con `google-genai`
2.34.0. Las dos líneas base son **llamadas reales a Gemini**; el resto se obtuvo
sin Gemini, sin clave y sin red. Cada archivo es la salida completa del comando.

| Archivo | Origen | Qué muestra |
| --- | --- | --- |
| [`dataset-validacion.txt`](dataset-validacion.txt) | `scripts.dataset_tuning --comprobar-validador --comprobar-api` | 24 ejemplos, balance 8/9/7, 0 problemas, 10 copias rotas detectadas y rechazo local de PEFT. |
| [`regla-local.txt`](regla-local.txt) | `scripts.linea_base_rutas --solo-regla-local` | La detección de artículos acierta 22 de 24. |
| [`escenarios-previos.txt`](escenarios-previos.txt) | `scripts.decision_personalizacion`, antes de medir | Lo que recomendaría el método con cada resultado posible. |
| [`linea-base-01.json`](linea-base-01.json) | **Gemini real**, tramo interrumpido | 16 respuestas y un `GoogleRateLimitError`. Incompleta: no responde la pregunta. |
| [`linea-base-02.json`](linea-base-02.json) | **Gemini real**, `--continuar` | Las 24 respuestas: 16 conservadas y 8 nuevas. |
| [`decision-resultado.txt`](decision-resultado.txt) | `scripts.decision_personalizacion --linea-base` | Puntaje y sensibilidad con la medición completa. |
| [`verificacion-local.md`](verificacion-local.md) | Pruebas, ruff, basedpyright y unittest | Comprobaciones de la implementación. |
| [`verificacion-github.md`](verificacion-github.md) | Merge, push de `main` y clon limpio | Publicación e instalación. |

| Archivo | SHA-256 |
| --- | --- |
| `datos/personalizacion/rutas_ley_rep.json` | `905faaca62cb289cbd282999d31bb06ecfbd053b72d663c4562a01fdc3ab89e5` |
| `datos/personalizacion/hechos_decision.json` | `b4c5f79e20e3b95f6e0603e05594a6233c33e411bb65cd63e11ecf21e0e90908` |
| `linea-base-01.json` | `ffba0580810ed355726c5e3d1063ee132611ff179cd77f39accfe3db2889f198` |
| `linea-base-02.json` | `e13894faf45d1383cfe4f12fa8b8b17ea521686d418a5a73dac3a4c0e9c4f013` |

Las consultas son **sintéticas** y sus etiquetas se propusieron con asistencia de
IA siguiendo las reglas R1 a R3. La revisión previa a la medición mantuvo 23 y
cambió `a05` de aclaración a resumen del Artículo 1.

## B29: dataset y validación

- **Tarea:** clasificar consultas en las rutas del B19 e identificar el artículo
  único nombrado. Es un problema de comportamiento consistente, no de información.
- **Balance:** normativa 8, resumen 9, aclaración 7; razón máxima/mínima 1,3.
- **Validación:** 0 problemas en el dataset real. Las diez copias rotas a propósito
  se detectaron: texto vacío, clave faltante, comillas simples, duplicado,
  etiqueta contradictoria, ruta inválida, resumen sin artículo, artículo
  inexistente, clave no prevista y menos de 10 ejemplos.
- **Envío del trabajo:** no se realizó. La API para desarrolladores rechaza
  `adapter_size` antes de enviar, y el inventario del 20-10-2026 no muestra
  modelos con `createTunedModel`.

## B30: línea base real

Modelo `gemini-3.5-flash-lite`, prompt del B19 sin cambios. El criterio y los
escenarios se fijaron antes de medir y no se modificaron después.

| Medida | Resultado |
| --- | --- |
| Formato estricto | 24 de 24 |
| Criterio fijado | 3 incumplen: `n03`, `n06` y `n08` (12,5 %; umbral 15 %) |
| Coincidencia exacta | 5 no coinciden: las anteriores, `a03` y `a04` (20,8 %) |
| Ruta final del sistema | 5 equivocadas: 3 del modelo y 2 de la regla local, `r08` y `a05` (20,8 %) |
| Consumo informado | 4.877 tokens de entrada, 54 de salida; US$ 0,0015981 estimados |

**Dos tramos.** El primero, de 21:19:44 a 21:20:03 UTC, obtuvo 16 respuestas y se
detuvo en `a01`; no había pausa entre llamadas. No se conservó el detalle del error,
así que no se atribuye a una cuota concreta. El segundo, de 21:21:37 a 21:22:26
UTC, obtuvo las 8 restantes con 5 segundos de pausa. En total, 25 solicitudes
lanzadas desde el comando: 24 respondidas y 1 rechazada, cuyo consumo no se
conoce. Las 16 primeras respuestas son idénticas en ambos archivos.

**Fragilidad.** Intervalo de Wilson del 95 % para 3 de 24: 4,3 % a 31,0 %. Un
incumplimiento más daría 16,7 %. Las primeras 20 consultas del archivo dan 3 de 20,
justo el umbral.

## B30: resultado del método

| Pregunta | Respuesta | Evidencia |
| --- | --- | --- |
| ¿La información cambia seguido? | No | 0 cambios en 90 días en la copia local y en las reglas de ruta. |
| ¿Falla el formato o el tono? | No | 3 de 24, 12,5 %, en el límite. |
| ¿Dataset grande y de calidad? | No | 24 ejemplos; el criterio pide 200. |
| ¿Presupuesto limitado o iterar rápido? | Sí | 0 entrenamientos costeables. |
| ¿Varias variantes? | No | 1 asistente en español. |

**RAG 2, PEFT 1, fine-tuning 0.** Cuatro de las cinco respuestas cambian el
resultado al invertirse. La interpretación está en la
[decisión](../../arquitectura/decision-personalizacion.md) y en la
[guía de estudio](../../estudio/bloques-29-30.md#8-cómo-interpretar-nuestro-resultado).
