# Evaluación de respuestas de Ley REP

Esta evaluación compara respuestas de Gemini con referencias basadas en la copia
local de la Ley 20.920 de 2016. Cubre el procesamiento de texto del bloque 15, las
métricas del bloque 16 y la revisión de resultados del bloque 17.

El banco contiene 20 preguntas sobre los artículos 1 al 20. Cada consulta recibe el
artículo correspondiente como contexto; la respuesta de referencia se utiliza solo
para evaluar y no se envía al modelo. La referencia es una respuesta esperada con
la que se compara lo que generó Gemini.

Para revisar el trabajo, este documento explica el funcionamiento y los resultados.
El [análisis de límites](limites_metrica.md) desarrolla los hallazgos; los archivos
JSON enlazados conservan el detalle de cada caso.

## Implementación

| Archivo | Función |
| --- | --- |
| [texto.py](../src/evaluacion/texto.py) | Limpieza, tokenización, comparación antes/después y métricas. |
| [casos-ley-rep.json](../datos/evaluacion/casos-ley-rep.json) | Preguntas, referencias y artículos utilizados. |
| [evaluar_texto.py](../scripts/evaluar_texto.py) | Consultas al cliente, registro de resultados y selección de casos para revisión. |
| [tests/evaluacion](../tests/evaluacion/) | Pruebas del procesamiento, métricas, reanudación y validación de la revisión. |

La limpieza pasa el texto a minúsculas, reemplaza la puntuación por espacios y
agrupa los espacios repetidos. Conserva tildes, ñ, números, guiones bajos y negaciones.
Reemplazar los signos por espacios evita unir palabras como `reciclaje/reutilización`.
Después se separa el texto por espacios para obtener una lista de palabras: ese paso
se llama tokenización. Estos tokens no son los que usa el proveedor para facturar.

Se compara únicamente el campo `respuesta`. El JSON completo, las citas y el consumo
se guardan junto al resultado para poder revisarlos después.

## Métricas

Antes y después de la limpieza se calcula qué proporción de palabras únicas de la
referencia aparece en la respuesta. Luego se calculan tres métricas que también
consideran las repeticiones de cada palabra:

| Métrica | Qué indica | Cálculo |
| --- | --- | --- |
| Precisión | Cuánto de lo escrito aparece en la referencia. | Coincidencias / palabras de la respuesta. |
| Cobertura | Cuánto de la referencia aparece en la respuesta. | Coincidencias / palabras de la referencia. |
| F1 | El equilibrio entre precisión y cobertura. | `2 × precisión × cobertura / (precisión + cobertura)`. |

Los valores van de 0 a 1: `0.75` equivale a 75 %. Por ejemplo, si la referencia es
«el gato negro duerme» y la respuesta es «el gato duerme tranquilo», coinciden tres
de cuatro palabras de cada lado. Precisión, cobertura y F1 valen 0.75.

Las repeticiones también cuentan: si una palabra aparece dos veces en la referencia
y tres en la respuesta, aporta dos coincidencias. El código hace ese conteo con
`Counter`, una herramienta de Python para contar apariciones. Si un texto queda
vacío o no hay coincidencias, las métricas valen cero. Los fallos de petición o de formato se registran como errores
y se excluyen de los promedios.

Estos valores miden coincidencia de palabras. Una respuesta más extensa o redactada
con sinónimos puede recibir un puntaje bajo aunque conteste correctamente.

## Resultados registrados

La [ejecución del 4 de noviembre de 2026](evaluaciones/texto-rep-01.json) contiene
20 respuestas procesadas con `gemini-3.5-flash-lite` y ningún caso pendiente.

En los primeros tres casos se observa el efecto de la limpieza del bloque 15:

| Caso | Coincidencia antes de limpiar | Después de limpiar |
| --- | ---: | ---: |
| `rep-01` | 79.2 % | 91.7 % |
| `rep-02` | 78.9 % | 84.2 % |
| `rep-03` | 90.0 % | 100.0 % |

Estos porcentajes usan palabras únicas. No son F1: muestran cómo cambia la
comparación al quitar diferencias de formato. Los promedios de las métricas del
bloque 16, calculados sobre las 20 respuestas, son:

| Promedio por respuesta | Valor |
| --- | ---: |
| Precisión | 0.456 |
| Cobertura | 0.939 |
| F1 | 0.593 |

La [revisión de diez casos](evaluaciones/revision-rep-01.json) reúne los cinco F1
más bajos y los cinco más altos, con desempate por identificador. Incluye la pregunta,
la referencia, el artículo, la respuesta y una justificación de cada calificación.
La revisión está registrada como asistida por Codex y pendiente de validación por Brandon.

En los diez casos revisados se calificaron las respuestas como correctas y completas
para sus preguntas, sin contradicciones con los fragmentos. Un ejemplo de la diferencia
entre puntaje y contenido es `rep-18`: responde correctamente que la interpretación
corresponde al Ministerio, pero obtiene F1 de 0.174 porque la referencia solo contiene
«Al Ministerio» y la respuesta desarrolla la oración completa.

El [documento de límites](limites_metrica.md) explica estos hallazgos y cuándo conviene
revisar el contenido en lugar de confiar solo en el puntaje.

## Ejecutar una evaluación

Desde la raíz del proyecto, con `GEMINI_API_KEY` configurada en `.env`:

```bash
uv run python -m scripts.evaluar_texto generar \
  --casos datos/evaluacion/casos-ley-rep.json \
  --salida docs/evaluaciones/texto-rep-02.json
```

El ejemplo usa una salida nueva para conservar la primera evaluación. No requiere
iniciar FastAPI. Realiza un intento por caso, con una pausa predeterminada de dos
segundos, y consume cuota del proveedor.

Cada intento queda guardado antes de continuar. Para retomar una ejecución incompleta,
se repite el comando con `--reanudar`: solo se consultan los casos sin éxito y se
conservan los errores anteriores. No se deben ejecutar dos procesos sobre la misma
salida al mismo tiempo.

Los resultados incluyen los casos, el modelo, las instrucciones y la versión del
prompt. Si cambia esa configuración, se requiere un archivo de salida nuevo.

## Revisar las respuestas

Para seleccionar los diez casos de una nueva evaluación:

```bash
uv run python -m scripts.evaluar_texto preparar-revision \
  --resultados docs/evaluaciones/texto-rep-02.json \
  --revision docs/evaluaciones/revision-rep-02.json
```

La selección requiere al menos 20 casos exitosos. La revisión utiliza estos campos:

| Campo | Criterio | Valores |
| --- | --- | --- |
| `correccion_factual` | Los datos concuerdan con el artículo. | `si`, `no`, `parcial` |
| `completitud` | La respuesta cubre lo preguntado. | `si`, `no`, `parcial` |
| `contradiccion` | La respuesta afirma algo contrario al artículo. | `si`, `no` |
| `nota` | Explicación de la calificación y de su relación con el F1. | Texto libre |

Un `si` en `contradiccion` significa que se encontró un problema. Una respuesta
puede tener datos correctos y estar incompleta si deja una parte de la pregunta sin
contestar. La nota explica estas diferencias con ejemplos del caso.

El archivo también identifica al revisor y la fecha. Las respuestas y métricas se
conservan sin cambios durante la revisión. Para comprobar la revisión ya registrada:

```bash
uv run python -m scripts.evaluar_texto validar-revision \
  --resultados docs/evaluaciones/texto-rep-01.json \
  --revision docs/evaluaciones/revision-rep-01.json
```

Para validar la nueva evaluación del ejemplo, se cambian ambos nombres de archivo
a `texto-rep-02.json` y `revision-rep-02.json`.

El validador comprueba que los campos estén completos y que correspondan a los
resultados originales. La calidad de las justificaciones requiere lectura del contenido.

## Alcance

La evaluación trabaja con artículos proporcionados directamente como contexto.
No evalúa la recuperación de documentos de un RAG ni comprueba vigencia normativa.
Tampoco verifica automáticamente que las citas respalden todas las afirmaciones.

Las pruebas automáticas se ejecutan sin llamadas al proveedor:

```bash
uv run python -m pytest tests/evaluacion -q
```
