# Decisión de personalización: clasificador de rutas de Ley REP

**Actividad:** Skillnest, bloque 30, decisión fundamentada de estrategia de personalización.

**Fecha:** 24 de noviembre de 2026.

**Estado:** revisada y lista para presentar.

## 1. El problema

El asistente de Ley REP envía cada consulta a una de tres rutas: normativa,
resumen o aclaración. De 24 respuestas del clasificador actual, 3 (12,5 %) no
corresponden a la ruta esperada. Dos preguntan por el contenido de un artículo y
se tratan como si pidieran un resumen; la otra se entiende, pero se responde
pidiendo aclaraciones.

Esta medición es una práctica sobre una sola norma, la Ley 20.920. El proyecto
final necesita varias, porque la ley remite a un decreto por producto. La decisión
debe servir hoy y también al crecer; el plan está en el
[PRD 06](../planes/prd-06-mvp-gate-3.md).

## 2. Resultado del método de decisión

| Pregunta | Respuesta | Evidencia |
| --- | --- | --- |
| ¿La información cambia al menos una vez al mes? | No | 0 cambios en 90 días: una versión local de la ley (2016-06-01) y reglas de ruta sin cambios desde `df14a2c`. |
| ¿Falla el formato o el comportamiento en 15 % o más? | No | 3 de 24 respuestas (12,5 %): `n03`, `n06` y `n08`. Las 24 cumplen el formato de una palabra. |
| ¿Hay al menos 200 ejemplos etiquetados y consistentes? | No | 24 ejemplos, 0 contradicciones detectadas. |
| ¿Se pueden pagar 2 entrenamientos o menos? | Sí | 0 entrenamientos: el proyecto no costearía ninguno. |
| ¿Se necesitan 2 o más variantes? | No | 1: un asistente en español para la Ley REP chilena. |

- **RAG: 2 puntos**
- PEFT: 1 punto
- Fine-tuning completo: 0 puntos

RAG obtiene el mayor puntaje, sin empate. Sus 2 puntos vienen **solo** de la
pregunta de presupuesto.

Sensibilidad, invirtiendo una respuesta a la vez:

| Si la respuesta fuera distinta | Mayor puntaje | ¿Cambia? |
| --- | --- | --- |
| La información cambia seguido | RAG | No |
| El formato o comportamiento falla 15 % o más | PEFT | Sí |
| Hay un dataset grande | Empate entre las tres | Sí |
| Hay presupuesto | Empate entre las tres | Sí |
| Se necesitan varias variantes | PEFT | Sí |

**El resultado es frágil.** Cuatro de las cinco respuestas lo cambian, y la de
comportamiento está en el límite:

- Un incumplimiento más daría 4 de 24, 16,7 %, y ganaría PEFT.
- Las primeras 20 consultas, en el orden del archivo, dan 3 de 20: justo 15 %.
- Solo por formato serían 0 de 24. Exigiendo coincidencia exacta de la palabra,
  5 de 24, 20,8 %.
- Con 24 respuestas, el intervalo de confianza del 95 % va de 4,3 % a 31,0 %:
  no permite asegurar de qué lado del 15 % está el clasificador.

El criterio se fijó antes de medir y no se modificó después.

**Qué cambiaría al crecer.** La primera respuesta describe la copia local. Con
varias normas, los cambios sí ocurren: la
[Res. Ex. 5.193/2026](https://www.diariooficial.interior.gob.cl/publicaciones/2026/09/24/44557/01/2873948.pdf),
publicada el 24-9-2026, dejó constancia de la anulación del decreto de aceites y
revocó tres actos. Es 1 cambio conocido en 90 días, no un conteo completo; el
criterio pide 3. Si llegara a «sí», RAG seguiría primero, como muestra la tabla.

## 3. Técnica elegida y por qué

**Se elige RAG como única técnica de personalización del asistente, y no entrenar
el clasificador de rutas.** El clasificador se mantiene con su prompt actual.

El puntaje por sí solo no basta, porque está en el límite. La decisión se apoya
en cuatro hechos que valen aunque la respuesta de comportamiento hubiera sido
«sí» y PEFT hubiera ganado con 3 puntos:

1. **Costo:** hay presupuesto para 0 entrenamientos y la API con clave de
   desarrollador rechaza la configuración PEFT.
2. **Datos:** hay 24 ejemplos de los 200 que pide el criterio.
3. **Alternativa más barata sin probar:** `n03` y `n08` comparten un patrón, una
   pregunta que nombra un artículo se toma como resumen. Aclararlo en el prompt
   se prueba en segundos. Corresponde intentarlo antes de pagar un entrenamiento.
4. **Errores que entrenar no corrige:** `r08` («resume art 27») y `a05` («Resume el
   artículo primero») terminan en la ruta equivocada por la regla local que
   detecta el artículo. El modelo respondió bien en ambos.

RAG no arregla el clasificador: a este no le falta información. RAG se elige para
lo que sí es información, el contenido de la ley, y ya está implementado y medido
en los bloques 24 a 28. Al crecer, esa razón se refuerza: agregar, cambiar o retirar
una norma solo exige actualizar el índice; con un modelo entrenado habría que volver
a entrenar y la respuesta no tendría una fuente que citar. Se descartan el
fine-tuning completo, por datos y costo, y el soft-prompting, porque la API no lo
ofrece.

## 4. Qué se necesitaría para ejecutarla

**Para RAG, por etapas.** Hoy están indexados los 50 artículos de una norma, en 99
fragmentos. La ley sola no fija las metas: su artículo 12 las encarga a decretos por
producto. Por eso el índice debe crecer en número de normas:

| Etapa | Normas | Qué permite responder | Falta respecto de hoy |
| --- | --- | --- | --- |
| Hoy | 1 | El marco general | 0 normas |
| Gate 2 | 2 | + envases y embalajes | 1 norma y la actualización incremental |
| MVP Gate 3 | 5 | + neumáticos, pilas y aparatos eléctricos | 4 normas y 40 preguntas propias (3,6 horas) |
| Ampliación | 9 | + residuos peligrosos, reportes y plásticos | 8 normas |

Cada norma exige cuatro comprobaciones: texto oficial, enlace y fecha, hash, y tablas
contrastadas. Son 16 para las 4 normas que faltan del MVP. Más documentos no es
siempre mejor: cada uno agrega fragmentos que compiten por entrar en la respuesta, así
que una etapa solo empieza si la anterior conserva sus resultados. El corpus se
justifica en el [PRD 06](../planes/prd-06-mvp-gate-3.md#3-corpus-propuesto).

**Para ampliarlo a Latinoamérica:** hoy hay 0 leyes de otros países en el corpus.
Cada país agrega al menos una norma y un índice separado, para no mezclar
jurisdicciones. Es un problema de información, no de variantes del modelo; si cada
país necesitara otro comportamiento, habría que repetir el método.

**Para mejorar el clasificador sin entrenar:** 2 ajustes en la regla de artículos
(`r08` y `a05`), 1 aclaración del prompt (`n03` y `n08`) y al menos 20 consultas
nuevas para medir, porque las 24 actuales ya se vieron. Etiquetar 20 consultas a 5
minutos son 1,7 horas.

**Para reconsiderar PEFT:**

| Requisito | Hoy | Falta |
| --- | --- | --- |
| Ejemplos etiquetados | 24 | 176 para llegar a 200: 15,84 horas, unas 2 jornadas |
| Ejemplos de prueba independientes | 0 | Al menos 20 |
| Entrenamientos costeables | 0 | Al menos 1 |
| Plataforma con PEFT | No | 1 proyecto con facturación en Gemini Enterprise Agent Platform |

Se vuelve a aplicar el método si, después de aclarar el prompt, el clasificador
incumple 15 % o más en al menos 20 consultas nuevas, o si se completan los cuatro
requisitos de la tabla.

Las horas usan los supuestos del curso: 5 minutos por ejemplo y una segunda
revisión de 2 minutos para el 20 %.

## Procedencia y límites

- [Línea base completa](../evidencias/bloques-29-30/linea-base-02.json), medida con
  `gemini-3.5-flash-lite` el 24-11-2026 en dos tramos por un límite de frecuencia.
  El [primer tramo](../evidencias/bloques-29-30/linea-base-01.json) se conserva.
- Las consultas son sintéticas. Las etiquetas se propusieron con asistencia de IA
  y se revisaron antes de medir. El documento se preparó con asistencia de IA.
- El inventario de modelos es del 20-10-2026. No se intentó enviar un
  entrenamiento, así que no se afirma que sea imposible por otra vía.
- El caso, los hechos y las huellas están en el
  [índice de evidencias](../evidencias/bloques-29-30/README.md).
