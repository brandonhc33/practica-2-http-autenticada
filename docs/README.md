# Documentación del proyecto

Este índice conecta lo que se aprende, lo que se decidió y lo que realmente se
comprobó. Para ejecutar la aplicación, empieza por el [README del proyecto](../README.md).

## Organización

| Carpeta | Qué contiene | Cuándo consultarla |
| --- | --- | --- |
| [`guias/`](guias/guia-completa.md) | Instalación, comandos, API y resolución de problemas. | Quiero usar o ejecutar el proyecto. |
| [`arquitectura/`](arquitectura/vision-general.md) | Flujos, selección de modelo, límites de autonomía y diagramas editables. | Quiero entender cómo está diseñado y qué permite. |
| [`estudio/`](estudio/modulo-2-desde-bloque-18.md) | Glosario con ejemplos y diagramas, mapa desde B18 y guías por bloque. | Quiero aprender, no solo copiar un comando. |
| [`planes/`](planes/prd-08-gate-2.md) | PRD, decisiones, fases y revisiones iniciales. | Quiero entender el alcance y por qué se eligió una solución. |
| [`entregas/`](entregas/gate-2.md) | Correspondencia con las actividades, checklist y estado comprobado. | Quiero revisar o preparar una entrega. |
| [`evaluaciones/`](evaluaciones/respuestas-ley-rep.md) | Resultados de modelos/prompts/respuestas y límites de sus métricas. | Quiero analizar calidad y comparar resultados. |
| [`evidencias/`](evidencias/) | Registros, capturas y verificaciones conservadas. | Quiero comprobar una afirmación o el resultado de una ejecución. |

## Recorrido por bloques

Si el vocabulario es nuevo, consulta el
[glosario con definiciones, funciones, analogías y diagramas](estudio/glosario.md#cómo-usar-este-glosario).
Tiene una entrada corta de diez conceptos y el resto se puede leer por tema.

Para estudiar el módulo 2 desde el bloque 18, empieza por el
[mapa de progresión y orden de lectura](estudio/modulo-2-desde-bloque-18.md).
Conecta chains, rutas, agentes, RAG, personalización y gobernanza; las guías por bloque desarrollan el código,
los resultados y sus límites con ejercicios sin Gemini.

| Bloques | Aprender o usar | Diseño y planificación | Entrega o evidencia |
| --- | --- | --- | --- |
| 4 | [HTTP autenticado y API](guias/guia-completa.md#actividades-del-curso) | [Flujo base](arquitectura/vision-general.md) | [Peticiones y captura HTTP](evidencias/http/) |
| 8–9 | [Arquitectura](arquitectura/vision-general.md) | [Selección de modelo](arquitectura/seleccion-modelo.md) y [diagrama](arquitectura/diagramas/flujo-api.png) | [Mediciones de modelos](evaluaciones/gemini-2026-10-20.json) |
| 10 | [Prompts y JSON](estudio/bloque-10-prompts.md) | [Uso del banco](guias/guia-completa.md#banco-de-prompts-y-salida-estructurada-bloque-10) | [Evaluación de prompts](evaluaciones/prompts-actual.json) |
| 12–14 | [Reintentos](guias/guia-completa.md#cliente-con-reintentos-bloque-12) | [Revisión inicial](planes/revision-bloques-13-14.md); [PRD 01 aún propuesto](planes/prd-01-control-consumo-gemini.md) | [Entrega 13–14](entregas/bloques-13-14.md) y [capturas de terminal](evidencias/mis-capturas/README.md) |
| 15–17 | [Evaluación de respuestas](evaluaciones/respuestas-ley-rep.md) | [Límites de métricas](evaluaciones/limites-metricas.md) | [Resultados](evaluaciones/texto-rep-01.json) y [revisión](evaluaciones/revision-rep-01.json) |
| 18–20 | [Chains, rutas y errores](estudio/bloques-18-20.md) | [PRD 02](planes/prd-02-orquestacion-langchain.md) | [Entrega 18–20](entregas/bloques-18-20.md) |
| 21–23 | [Herramientas, memoria y supervisión](estudio/bloques-21-23.md) | [PRD 03](planes/prd-03-agente-ley-rep.md) y [límites de autonomía](arquitectura/limites-autonomia-agente.md) | [Entrega 21–23](entregas/bloques-21-23.md) |
| 24–28 | [RAG, evaluación, latencia y costo](estudio/bloques-24-28.md) | [PRD 04](planes/prd-04-rag-ley-rep.md) | [Entrega y actividad 28](entregas/bloques-24-28.md), con [mediciones reales](evidencias/bloques-24-28/README.md) |
| 29–30 | [Personalización: RAG, fine-tuning y PEFT](estudio/bloques-29-30.md) | [PRD 05](planes/prd-05-personalizacion-ley-rep.md) y [decisión](arquitectura/decision-personalizacion.md) | [Entrega y actividad 30](entregas/bloques-29-30.md), con [línea base real](evidencias/bloques-29-30/README.md) |
| 31–32 | [Registros, inyección, supervisión y riesgos](estudio/bloques-31-32.md) | [PRD 07](planes/prd-07-observabilidad-gobernanza.md) y [matriz de riesgos](arquitectura/matriz-riesgos.md) | [Entrega 31–32](entregas/bloques-31-32.md), con [evidencias y prueba real](evidencias/bloques-31-32/README.md) |
| Gate 2 | [Integrar, actualizar y supervisar](estudio/gate-2.md) | [PRD 08](planes/prd-08-gate-2.md) | [Entrega del Gate 2](entregas/gate-2.md), con [evidencias reales](evidencias/gate-2/README.md) |
| Proyecto final | [Proyecto final en la guía](guias/guia-completa.md#proyecto-final-de-skillnest-asistente-rag-para-ley-rep) | [PRD 06: MVP del Gate 3, sin implementar](planes/prd-06-mvp-gate-3.md) | Sin entrega todavía |

El estado de cada actividad se consulta en su entrega. Un PRD conserva el contexto
de planificación: no demuestra por sí solo que algo esté implementado o validado.
El proyecto final se desarrolla progresivamente en la [guía completa](guias/guia-completa.md#proyecto-final-de-skillnest-asistente-rag-para-ley-rep).

## Convenciones para seguir creciendo

- Nombres en minúsculas y con guiones. Dentro de `estudio/` y `entregas/`, usar
  `bloques-NN-NN.md`; no repetir `preguntas-` o `entrega-` en cada archivo.
- Numerar los PRD para conservar el orden de las decisiones, sin confundirlo con
  el número de bloque. Distinguir propuesta, implementación y validación real.
- Poner cada documento en una sola categoría y enlazarlo desde las demás. No
  duplicar explicaciones completas en el README ni en varias entregas.
- Mantener las evidencias de cada ampliación en `evidencias/bloques-NN-NN/`.
  `evidencias/http/` reúne las pruebas iniciales; `mis-capturas/` conserva el
  archivo histórico de capturas del alumno y sus manifiestos sin renombrarlos.
- Conservar los archivos originales de evaluación y evidencia: sus números,
  hashes, fechas y comandos históricos no se reescriben al reorganizar docs.
- Los enlaces y comandos de la documentación de uso apuntan a las rutas actuales.
  El corpus y los casos de entrada siguen en `datos/`; el runtime de RAG y los
  índices siguen fuera de Git, en `output/rag/`, `vectorstore/` e `indice_normas/`. Las mediciones
  locales de personalización quedan en `output/personalizacion/`.
- No guardar `.env`, claves, binarios de Chroma ni consultas privadas. Versionar
  únicamente evidencia revisada y señalar si usó servicios reales o simulados.
