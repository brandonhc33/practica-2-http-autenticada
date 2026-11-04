# Límites de la evaluación de respuestas

## Qué mide

La evaluación cuenta las palabras que comparten una respuesta de Gemini y una
respuesta de referencia, después de limpiar ambos textos. Con ese conteo calcula
precisión, cobertura y F1. Se evalúa el campo `respuesta`; las citas se guardan aparte.

Un F1 alto indica que se usaron palabras parecidas a las de la referencia. Para saber
si la respuesta es correcta y completa, también hay que leerla y compararla con el
artículo. Esta evaluación usa la copia local de la Ley 20.920 de 2016.

## Modos de falla conocidos

En la [revisión registrada](evaluaciones/revision-rep-01.json) se observaron tres
situaciones en las que el puntaje no representa bien la calidad de la respuesta:

| Caso | F1 | Qué se observó |
| --- | ---: | --- |
| `rep-18` | 0.174 | La referencia dice «Al Ministerio». Gemini responde lo mismo dentro de una oración completa. La respuesta es correcta, pero las palabras adicionales hacen bajar mucho el puntaje. |
| `rep-06` | 0.500 | Gemini explica cómo manejar los residuos y qué autorizaciones se necesitan. Además menciona la declaración en el Registro, que aparece en el artículo. Esa información adicional es correcta, pero baja la precisión frente a una referencia más breve. |
| `rep-17` | 0.444 | La respuesta conserva el plazo máximo de cinco años y el procedimiento del reglamento. Es más extensa y usa «conforme al» donde la referencia dice «según el». El puntaje baja aunque la idea esté completa. |

Estos casos muestran que la longitud y la redacción de la referencia influyen mucho
en el resultado. No conviene comparar preguntas distintas solo por su F1: una
referencia de dos palabras, como la de `rep-18`, pone en desventaja una respuesta
que explica el contexto.

También hay límites del método que no aparecieron como errores en los diez casos
revisados. Una cifra incorrecta o una negación omitida pueden cambiar el sentido sin
bajar demasiado el puntaje. El conteo tampoco distingue el orden de las palabras.
En `rep-08` y `rep-20`, las respuestas sí conservaron las prohibiciones del texto;
no se observó una inversión de sentido en esos casos.

## Muestra revisada

La [evaluación del 4 de noviembre de 2026](evaluaciones/texto-rep-01.json) contiene
20 respuestas de `gemini-3.5-flash-lite`, una por pregunta. Se seleccionaron diez:

- Cinco F1 menores: `rep-18`, `rep-19`, `rep-17`, `rep-06` y `rep-12`.
- Cinco F1 mayores: `rep-05`, `rep-08`, `rep-20`, `rep-14` y `rep-04`.

Los empates se resolvieron por identificador. Cada respuesta se comparó con la
referencia y el artículo incluido, revisando corrección de los datos, completitud
y contradicciones. La completitud se juzgó según lo preguntado: no era necesario
resumir todo el artículo para responder una pregunta puntual.

La revisión fue realizada por Codex el 4 de noviembre de 2026 y está pendiente de
validación por Brandon, como consta en el archivo de revisión. Las diez respuestas
se calificaron como correctas y completas para sus preguntas, sin contradicciones
con los fragmentos. Esto describe la muestra revisada; no demuestra que las otras
diez respuestas o futuras consultas estén libres de errores.

## Recomendación de uso

Usar F1 como apoyo para ordenar qué respuestas revisar y comparar versiones de un
prompt sobre las mismas preguntas y referencias. Un F1 bajo es una razón para leer
el caso, no para descartarlo automáticamente. Un promedio más alto tampoco demuestra
por sí solo que una versión responda mejor.

Revisar el contenido especialmente cuando haya plazos, cifras o prohibiciones, y
comprobar que las citas respalden lo afirmado. En esta muestra, las diferencias de
extensión explican varios puntajes bajos, por lo que conviene mantener referencias
con un nivel de detalle consistente en futuras evaluaciones.

Los resultados corresponden a preguntas con el artículo ya proporcionado. No permiten
concluir cómo funcionaría una búsqueda documental ni si la copia utilizada representa
la normativa vigente.
