# Guía de estudio: bloques 18 a 20

## Objetivo y fuentes

Entender cómo pasamos de pedir una respuesta a Gemini a **organizar varios pasos,
elegir una ruta y responder de forma controlada si algo falla**. LangChain conecta
las piezas; no hace verdadero lo que diga el modelo.

Esta guía contrasta la Unidad 2.3, recogida en el
[PRD 02](../planes/prd-02-orquestacion-langchain.md#10-entregables-por-bloque),
con el código y las [evidencias de la entrega](../entregas/bloques-18-20.md).
No es una transcripción de videos ni agrega requisitos docentes. La primera
parte explica el recorrido; las fases del final conservan el análisis técnico
histórico para profundizar después.

Si cuesta ubicar estos conceptos dentro del módulo, empieza por el
[mapa de estudio desde el bloque 18](modulo-2-desde-bloque-18.md#1-el-recorrido-en-una-sola-idea).

## Índice

1. [Qué cambia y qué debes aprender](#1-qué-cambia-y-qué-debes-aprender)
2. [Las piezas mínimas de LangChain](#2-las-piezas-mínimas-de-langchain)
3. [Bloque 18: seguir los datos de una chain](#3-bloque-18-seguir-los-datos-de-una-chain)
4. [Bloque 19: clasificar no es decidir toda la ruta](#4-bloque-19-clasificar-no-es-decidir-toda-la-ruta)
5. [Bloque 20: fallar sin inventar una respuesta](#5-bloque-20-fallar-sin-inventar-una-respuesta)
6. [Interpretar los resultados reales](#6-interpretar-los-resultados-reales)
7. [Laboratorio sin Gemini](#7-laboratorio-sin-gemini)
8. Análisis avanzado conservado:
   [dependencias](#fase-0-dependencias),
   [chain](#fase-1-chain-de-tres-pasos),
   [rutas](#fase-2-clasificación-y-rutas),
   [errores](#fase-3-manejo-de-errores) y
   [clon limpio](#fase-4-entrega-y-clon-limpio).

## 1. Qué cambia y qué debes aprender

Antes teníamos un cliente que enviaba una consulta y recibía una respuesta.
Ahora el programa coordina varias llamadas, cada una con una responsabilidad.
La API y el cliente HTTP anterior siguen existiendo: esta etapa agrega otra
entrada, por terminal.

| Bloque | Qué pedía la actividad | Cómo lo resolvimos | Qué debes poder explicar |
| --- | --- | --- | --- |
| 18 | Chain de al menos tres pasos conectados. | Interpretar → responder con la ley → simplificar. Cada paso recibe información del anterior. | Qué entra y sale de cada paso y por qué una transformación puede perder información. |
| 19 | Enrutamiento condicional incorporado a la chain. | Clasificación y tres rutas: normativa, resumen y aclaración. | El modelo propone una categoría; el código comprueba condiciones y elige la ruta. |
| 20 | Comprobar el flujo completo y su manejo de errores. | Rutas con modelo secundario y texto de respaldo, más captura general de errores y pruebas sin red. | Disponibilidad, corrección del recorrido y exactitud legal son propiedades diferentes. |

**No es todavía un agente:** el modelo no elige una secuencia libre de
herramientas. Tampoco hay búsqueda semántica ni memoria entre consultas.

## 2. Las piezas mínimas de LangChain

| Pieza | En palabras simples | En nuestro proyecto |
| --- | --- | --- |
| `PromptTemplate` | Texto con casillas que se completan con datos. | La plantilla de interpretar usa `{mensaje}`. |
| Modelo | Recibe el prompt y devuelve un mensaje del asistente. | Lo configura [`crear_modelo`](../../src/orquestacion/modelo.py#L64). |
| `StrOutputParser` | Extrae texto de la respuesta del modelo. | Permite que el siguiente paso reciba texto, no un objeto `AIMessage`. |
| `Runnable` | Pieza que puede ejecutarse con una entrada. | Un modelo, una función adaptada o una chain completa. |
| `\|` | Conecta la salida de una pieza con la entrada de la siguiente. | `plantilla \| modelo \| StrOutputParser()`. |
| `.invoke(...)` | Ejecuta la pieza con esos datos. | `.invoke({"mensaje": consulta})`. |
| `RunnablePassthrough.assign` | Conserva los campos de entrada y agrega campos calculados. | Mantiene `mensaje` y agrega `interpretacion`. |
| `RunnableBranch` | Ejecuta la primera rama cuya condición se cumple; si ninguna, la rama por defecto. | Escoge una de las tres rutas. |

Una **chain** es esa composición ejecutable. Construirla no llama al modelo;
invocarla sí puede hacerlo. Un operador `|` no equivale a una llamada a Gemini:
parsear texto o agregar un campo son operaciones locales.

Tampoco usamos `consultar_gemini_raw` por debajo de este flujo: LangChain tiene su
propio conector. Reutilizamos el catálogo y el registro de costos, no toda la
política de reintentos del cliente HTTP anterior. El
[análisis de dependencias](#fase-0-dependencias) explica esa decisión y sus límites.

## 3. Bloque 18: seguir los datos de una chain

### ¿Qué recibe cada paso y para qué sirve?

La [`construcción de la chain`](../../src/orquestacion/cadena_tres_pasos.py#L62)
define este recorrido:

| Paso | Entrada | Salida | Lo que no debe hacer |
| --- | --- | --- | --- |
| Interpretar | Consulta original. | Reformulación y conceptos que revisar. | Contestar la pregunta o inventar datos del caso. |
| Responder | Consulta, interpretación y los artículos locales. | Respuesta documental con artículos y límites. | Tratar la interpretación como fuente legal. |
| Simplificar | Solo la respuesta anterior. | Texto en viñetas y lenguaje simple. | Agregar información o quitar condiciones y referencias. |

Ejemplo **didáctico del movimiento de datos**, no otra respuesta real de Gemini:

```text
{"mensaje": "¿Quién fija las metas de recolección?"}
→ assign agrega interpretacion sin borrar mensaje
{"mensaje": "...", "interpretacion": "..."}
→ assign agrega fragmentos de la copia local
{"mensaje": "...", "interpretacion": "...", "fragmentos": "..."}
→ paso_responder produce texto
"respuesta documental..."
→ una función lo envuelve en el campo que espera la última plantilla
{"respuesta": "respuesta documental..."}
→ paso_simplificar produce el texto final
```

El envoltorio `{"respuesta": respuesta}` no consulta al modelo: adapta la forma de
los datos. Si borrásemos `mensaje` al guardar la interpretación, el segundo paso
perdería la pregunta original. Si pasásemos un `AIMessage` sin parser, el contrato
de texto dejaría de cumplirse.

### ¿Interpretar significa buscar documentos?

No. La interpretación orienta la respuesta, pero
[`formatear_fragmentos`](../../src/orquestacion/cadena_tres_pasos.py#L55) carga
**los 50 artículos/transitorios** de la copia local. No selecciona fragmentos
por significado. Aún no hay embeddings, Chroma ni top-k.

Esta diferencia explica el consumo: el segundo paso recibe mucha más entrada
que interpretar o simplificar. Dividir una tarea en tres llamadas no ahorra
tokens automáticamente.

### ¿Por qué el tercer paso es un riesgo además de una ayuda?

Simplificar puede mejorar la lectura, pero también borrar una condición legal.
El tercer paso no vuelve a leer la ley: trabaja solo con lo que produjo el
segundo. Si ahí faltaba una excepción, no tiene una fuente para recuperarla.

En las corridas conservadas se perdió la referencia al artículo 37 y se
simplificaron condiciones indebidamente. Reforzar el prompt busca reducir ese riesgo,
pero **no equivale a validar la respuesta**. Es un ejemplo de propagación de
errores: más pasos no significan necesariamente más exactitud.

**Comprueba que lo entendiste:** la chain sola hace tres llamadas al modelo.
Si luego agregamos una clasificación previa, la ruta normativa completa hace
cuatro, no tres.

## 4. Bloque 19: clasificar no es decidir toda la ruta

### ¿Qué hace el modelo y qué hace Python?

El modelo propone `normativa`, `resumen` o `aclaracion`. La
[`clasificación`](../../src/orquestacion/enrutamiento.py#L74) extrae el texto y lo
normaliza. Después la
[`bifurcación`](../../src/orquestacion/enrutamiento.py#L112) aplica condiciones:

```text
Consulta
→ obtener categoría normalizada y buscar artículo nombrado
→ categoría normativa: ejecutar chain de tres pasos
→ categoría resumen Y artículo encontrado: resumir ese artículo
→ cualquier otro caso: pedir aclaración
```

Normalizar `" NORMATIVA. "` a `"normativa"` evita un fallo de formato.
No corrige una clasificación equivocada ni transforma cualquier palabra en una
categoría válida. Una categoría desconocida cae en aclaración.

### Ejemplos de recorrido

La categoría de la tabla es una **entrada supuesta para explicar el router**;
no prometemos que Gemini clasifique siempre así:

| Consulta | Categoría supuesta | Comprobación local | Ruta y llamadas sin fallos |
| --- | --- | --- | --- |
| «¿Quién fija las metas?» | `normativa` | No exige un artículo nombrado. | Normativa: 1 de clasificación + 3 de la chain = 4. |
| «Resume el artículo 9» | `resumen` | El artículo existe. | Resumen: 1 + 1 = 2. |
| «Resume el artículo 99» | `resumen` | No existe en la copia. | Aclaración: 1 + 1 = 2. |
| «Tengo una duda sobre mi empresa» | `aclaracion` | No basta para saber qué revisar. | Aclaración: 1 + 1 = 2. |
| «Resume el artículo 9» | `categoria_inventada` | Aunque exista el artículo, no hay categoría válida. | Aclaración: 1 + 1 = 2. |
| Solo espacios | No se clasifica. | El envoltorio detecta entrada vacía. | Mensaje local: 0. |

La última fila corresponde a
[`procesar_consulta_segura`](../../src/orquestacion/enrutamiento.py#L154), no a
invocar directamente cualquier pieza de la chain.

### ¿Por qué las rutas no reciben lo mismo?

- Normativa recibe la ley local completa para elaborar una respuesta.
- Resumen recibe solo el artículo encontrado y su referencia.
- Aclaración no recibe artículos: su trabajo es pedir antecedentes, no hacer
  afirmaciones legales.

No son tres nombres para el mismo prompt. La especialización cambia qué
información y qué tarea recibe el modelo.

**Comprueba que lo entendiste:** clasificar «resumen» no demuestra que el artículo
exista. La existencia se decide contra los datos locales, no por confianza en
la respuesta del clasificador.

## 5. Bloque 20: fallar sin inventar una respuesta

### Tres defensas, no tres garantías de verdad

| Defensa | Qué hace | Qué no hace |
| --- | --- | --- |
| [`exigir_texto`](../../src/orquestacion/modelo.py#L56) | Convierte una salida vacía en excepción. | No comprueba citas, condiciones ni veracidad del texto no vacío. |
| [`construir_ruta_segura`](../../src/orquestacion/enrutamiento.py#L144) | Si la ruta falla, intenta su versión con otro modelo; si también falla, devuelve respaldo local. | No detecta una respuesta incorrecta que no lance error. |
| [`procesar_consulta_segura`](../../src/orquestacion/enrutamiento.py#L154) | Captura fallos del flujo invocado, incluida la clasificación. | No protege la creación de modelos, que ocurre antes en `main`. |

**El fallback envuelve la ruta completa, no cada paso individual.** Si el modelo
principal interpreta bien y falla al responder o simplificar, el secundario
empieza de nuevo esa ruta. No continúa automáticamente desde el paso fallido.

```text
Clasificación correcta
→ ruta con principal
   → éxito: respuesta
   → excepción: repetir ruta con secundario
      → éxito: respuesta
      → excepción: texto fijo de respaldo

Fallo de clasificación
→ captura general y mensaje seguro, sin llegar a las rutas
```

Un **reintento** repite una llamada; un **fallback** cambia a una alternativa.
Aquí cada modelo tiene un intento y 30 segundos por llamada. No heredamos el
backoff del cliente anterior ni tenemos un presupuesto global de 30 segundos.
En la ruta normativa, contando clasificación, pueden producirse hasta
`1 + 3 + 3 = 7` llamadas si el principal falla en su tercer paso y el secundario
recorre los tres. El respaldo fijo no llama a Gemini.

### ¿Qué significa recibir un mensaje seguro?

Significa que el sistema comunica que no pudo responder. No significa que
respondió jurídicamente bien ni que el usuario no tenga obligaciones. Por eso
el texto de respaldo distingue una falla técnica de una conclusión sobre la ley.

La respuesta de contenido puede fallar sin excepción: una cita equivocada es
texto válido para Python. Hay que revisar **dos ejes distintos**:

1. ¿Funcionó el recorrido, incluidos sus controles?
2. ¿La respuesta conserva lo que realmente dice la fuente?

## 6. Interpretar los resultados reales

La [corrida final](../entregas/bloques-18-20.md#corrida-final) conserva las tres
rutas:

| Ruta | Llamadas observadas | Tokens totales | Costo estimado USD |
| --- | ---: | ---: | ---: |
| Normativa | 4 | 12.910 | 0,0049400 |
| Resumen | 2 | 782 | 0,0005448 |
| Aclaración | 2 | 445 | 0,0002985 |
| Total de esa corrida final | 8 | 14.137 | 0,0057833 |

### ¿Cómo leer esos números sin sacar una conclusión falsa?

- **4 + 2 + 2 = 8:** confirma el recorrido esperado en esos casos, sin fallback.
  No son ocho preguntas ni ocho llamadas por cada consulta.
- **12.910 tokens en normativa:** suman entrada y salida de sus cuatro llamadas,
  no solo el texto visible de la respuesta. La etapa de responder registró
  11.817 tokens; es consistente con enviar la ley completa.
- **Normativa consume más en esa corrida:** tiene más llamadas y más contexto.
  No es una comparación controlada de calidad: las preguntas y tareas difieren.
- **Costo estimado:** se calcula con uso informado y tarifas del repositorio,
  no con una factura. Un error sin uso informado queda como costo desconocido,
  no como una llamada demostrablemente gratuita.
- **Cero fallos observados:** el proveedor respondió en esos casos. No prueba
  que el fallback actuara; eso se comprueba con fallos simulados.

### ¿Por qué pasar las pruebas no eliminó los errores legales?

En normativa faltó el artículo 37, se citó el 4 para la fijación de metas y
quedaron condiciones insuficientes. La
[revisión de la salida](../entregas/bloques-18-20.md#corrida-final) lo registra.
Como no se guardó la respuesta intermedia del segundo paso, no podemos afirmar
en qué etapa de esa corrida se perdió el artículo 37.

Las pruebas con modelo falso fijan la respuesta: demuestran conexiones, rutas,
contratos y errores, **no la calidad de lo que Gemini elegirá escribir**.
El clon limpio comprueba instalación y archivos necesarios; tampoco certifica
la exactitud legal. La entrega histórica registró 199 pruebas: es el tamaño de
la suite de esa etapa, no el número que debe mostrar hoy todo el repositorio.

## 7. Laboratorio sin Gemini

Es un repaso opcional, **no otra entrega ni una nueva aprobación**. Desde la
raíz del repositorio y con las dependencias instaladas, estos comandos usan
modelos falsos y la red bloqueada por
[`conftest.py`](../../tests/conftest.py#L8). No necesitan una clave real ni
consumen cuota de Gemini:

```bash
uv run python -m pytest tests/orquestacion/test_cadena_tres_pasos.py -v
uv run python -m pytest tests/orquestacion/test_enrutamiento.py -v
uv run python -m pytest tests/orquestacion/test_orquestacion.py -v
```

No te quedes solo con `PASSED`: lee la prueba indicada y trata de anticipar qué
comprobará antes de ejecutarla.

| Ejercicio | Dónde mirar | Qué debes observar |
| --- | --- | --- |
| Dibujar la entrada de cada paso. | [`test_cada_paso_recibe_la_salida_del_anterior`](../../tests/orquestacion/test_cadena_tres_pasos.py#L84). | El segundo recibe consulta e interpretación; el tercero solo la respuesta. |
| Predecir «Resume el artículo 99» aunque la categoría sea `resumen`. | [`test_resumen_sin_articulo_va_a_aclaracion`](../../tests/orquestacion/test_enrutamiento.py#L97). | Se elige aclaración porque no hay artículo válido. |
| Predecir qué hace una respuesta vacía en el segundo paso. | [`test_respuesta_vacia_activa_el_fallback`](../../tests/orquestacion/test_orquestacion.py#L210). | El principal se detiene y el secundario recorre su propia chain. |
| Distinguir un fallo antes de elegir ruta. | [`test_procesar_consulta_segura_no_propaga_excepciones`](../../tests/orquestacion/test_orquestacion.py#L227). | Falla la clasificación y responde la captura general. |

### Preguntas de repaso y respuestas cortas

Intenta contestar primero sin leer la segunda columna:

| Pregunta | Respuesta |
| --- | --- |
| ¿Cada `\|` gasta una llamada? | No; solo las piezas que invocan al modelo. |
| ¿`assign` reemplaza toda la entrada? | No; agrega campos y conserva los anteriores, salvo que se reasigne el mismo nombre. |
| ¿La interpretación es evidencia de la ley? | No; la fuente es el texto local aportado. |
| ¿La ruta normativa de B18 recupera solo artículos pertinentes? | No; envía todos los artículos de la copia. |
| ¿Normalizar equivale a clasificar bien? | No; arregla formato, no intención. |
| ¿Una salida no vacía evita errores legales? | No; `exigir_texto` solo rechaza vacío. |
| ¿El secundario retoma en el tercer paso si ese falló? | No; repite la ruta normativa completa. |
| ¿30 segundos es el máximo de toda la consulta? | No; es el límite configurado por llamada. |
| ¿8 llamadas exitosas demuestran que el fallback funciona con Gemini? | No; no hubo una falla real que lo activara. |

Al terminar, continúa con [herramientas, memoria y supervisión](bloques-21-23.md#mapa-de-la-progresión).
Para profundizar, las fases siguientes conservan las preguntas y hallazgos de la
revisión anterior.

**Procedencia del análisis histórico:** las respuestas de las fases 0 a 4 se
redactaron con ayuda de Claude y se comprobaron el 7 de noviembre de 2026 contra
el commit `4a2622c`, con `langchain` 1.4.9, `langchain-core` 1.7.6,
`langchain-google-genai` 4.4.3 y `google-genai` 2.34.0. Sus mediciones de
comportamiento no usaron Gemini: se hicieron en una copia temporal y con un
servidor local que siempre responde HTTP 503. No son mediciones nuevas de esta
ampliación didáctica; las corridas reales están en la
[entrega](../entregas/bloques-18-20.md).

## Fase 0: dependencias

### 1. Mi cliente ya tenía reintentos, errores tipados y costos. ¿Por qué usar `ChatGoogleGenerativeAI`, y qué pierdo con ese cambio?

**Por qué:** es lo que usan el esqueleto de B18.3 y el agente de B21.3, y es un `Runnable`, así que funciona con `|`, `with_fallbacks` y callbacks. Envolver el cliente propio lo habría conservado, pero se aparta de la actividad y no serviría para el agente.

**Qué se pierde:**

- El backoff con jitter, `Retry-After` y el presupuesto de 90 s.
- Los errores tipados, como `ErrorAutenticacion`.
- El registro de costos automático: por eso existe `RegistroLlamadas`.

Además, ahora hay dos caminos hacia Gemini, y el PRD 01 no cubriría este.

### 2. ¿Qué papel cumple cada archivo: `pyproject.toml`, `uv.lock` y `requirements.txt`? El código importa `langchain_core`, que no está en `pyproject.toml`: ¿por qué funciona y qué riesgo tiene?

| Archivo | Papel |
| --- | --- |
| `pyproject.toml` | Declara lo que el proyecto pide directamente, con rangos de versiones. |
| `uv.lock` | Fija las versiones exactas de todo el árbol, para que `uv sync --locked` sea reproducible. |
| `requirements.txt` | Exportación para `pip`, el camino que usa B11.2. |

**Por qué funciona:** `langchain` y `langchain-google-genai` dependen de `langchain-core`, así que se instala igual y queda fijado en 1.7.6.

**Riesgo:** se importa 17 veces sin declararlo, y ningún rango propio lo protege. Una actualización podría cambiar su versión o dejar de traerlo. Lo mismo pasa con `pydantic` y con `google.genai`, que usan las pruebas. Se arregla declarándolo con `uv add langchain-core`.

### 3. Agregué paquetes y siguieron pasando las 166 pruebas. ¿Qué demuestra y qué no?

**Demuestra:** el código anterior sigue funcionando con el árbol nuevo, que pasó de 33 a 65 paquetes y además subió `certifi` de 2026.7.22 a 2026.10.23.

**No demuestra:** nada sobre LangChain, porque esas pruebas no lo usaban. Tampoco dice nada sobre llamadas reales, porque la suite corre sin red.

## Fase 1: chain de tres pasos

### 1. El paso 3 perdió el artículo 37 aunque la plantilla pedía conservarlo. ¿Qué garantiza una instrucción en un prompt, y por qué no lo detectaron las pruebas?

Una instrucción no garantiza nada: influye en el modelo, pero no lo obliga.

Las pruebas no lo detectaron porque el modelo es falso y la salida la escribe la propia prueba. Solo verifican el armado de la chain y que la plantilla contenga ciertas frases. Para garantizarlo hay que validar la salida real, por ejemplo comparando con código los artículos citados en los pasos 2 y 3.

### 2. Si borro el `StrOutputParser` del paso 1, ¿qué pasa y qué prueba lo detecta?

`exigir_texto` recibe un `AIMessage` en vez de texto y falla con `AttributeError: 'AIMessage' object has no attribute 'strip'`.

**En el flujo:** falla el modelo principal, falla el secundario con el mismo error y sale el texto de respaldo. Se gastan 2 llamadas y lo único que delata el problema es el registro.

**Pruebas que fallan (5 de las 33):**

- `test_cadena_conecta_los_tres_pasos`
- `test_cada_paso_recibe_la_salida_del_anterior`
- `test_main_imprime_respuesta_y_consumo`, de `test_cadena_tres_pasos.py`
- `test_cadena_normativa_usa_fallback_ante_fallo_del_modelo`
- `test_respuesta_vacia_activa_el_fallback`

`test_cada_paso_devuelve_texto` no lo detecta, porque arma su propia chain.

**Antes de `exigir_texto` era más silencioso:** sin parser ni `exigir_texto` en el paso 1, no hay ningún error. El paso 2 recibe `<interpretacion>content='salida del paso 1' additional_kwargs={}...` y solo falla `test_cada_paso_recibe_la_salida_del_anterior`.

### 3. ¿Cuántos intentos hace `max_retries=1`? ¿Por qué el motivo de D-03 ya no sirve para defender ese valor frente a `0`?

Hace un solo intento, sin reintentos. Medido contra el servidor local:

| `max_retries` | Peticiones enviadas |
| --- | --- |
| 0 | 1 |
| 1 | 1 |
| 2 | 2 |

D-03 dice que `0` significa "valor por defecto de Google", pero en `google-genai` 2.34.0 el SDK convierte `attempts=0` en 1 (`google/genai/_api_client.py:679`). Hoy ambos valores hacen lo mismo.

`1` se puede defender porque es lo que documenta el conector para "sin reintentos" y porque no depende de esa conversión interna. Lo que ya no se puede decir es que `0` sea incorrecto.

## Fase 2: clasificación y rutas

### 1. Las pruebas pasaban y el paso 3 inventó una obligación incondicional. ¿Qué verifican las pruebas con mock y qué haría falta para detectar ese error?

Verifican el flujo: qué ruta se ejecuta, cuántas llamadas hay y qué recibe cada paso. No verifican si lo que dice el modelo es verdad, porque ese texto lo escribe la prueba.

Para detectar la obligación inventada hace falta correr casos reales contra respuestas de referencia revisadas, con una rúbrica o con revisión humana. Esa evaluación gasta cuota y por eso no pertenece a la suite sin red.

### 2. Si el modelo responde `resumen` a "Resume el artículo 99", ¿qué ruta se ejecuta y en qué línea se decide? ¿Por qué no basta con confiar en la categoría?

Se ejecuta la ruta de aclaración, con 2 llamadas en total.

| Línea de `enrutamiento.py` | Qué ocurre |
| --- | --- |
| 130 | Calcula `fragmento` con `buscar_fragmento`. |
| 90 | Captura el `ValueError` del artículo inexistente y devuelve `None`. |
| 124 | **Aquí se decide:** exige categoría `resumen` y `fragmento` distinto de `None`, y no se cumple. |
| 125 | Se usa la ruta por defecto. |

No basta con la categoría porque el modelo clasifica la intención, pero no sabe si el artículo existe. La existencia la comprueba el código contra la ley. Lo cubre `test_resumen_sin_articulo_va_a_aclaracion`.

### 3. Clasifiqué bien 9 de 9 mensajes. ¿Qué puedo concluir y qué no?

**Se puede concluir:** esos mensajes, en esas corridas, se clasificaron bien y fueron a su ruta.

**No se puede concluir:** estabilidad ni precisión general. No se repitieron mensajes, no se probaron casos límite y no se puede fijar la temperatura.

Como referencia, con 9 de 9 la cota superior de confianza del 95 % para la tasa de error sigue siendo de 28 %, y eso suponiendo una muestra representativa e independiente.

## Fase 3: manejo de errores

### 1. El secundario tuvo tres HTTP 503 en nueve intentos y 16 s de latencia media, y costó 5,8 veces más. ¿Por qué lo mantuve, qué demuestra la corrida y qué no?

**Por qué:** fue la única alternativa que respondió en la comparación del Bloque 9 y tiene tarifa registrada. Además, solo cuesta más cuando el principal falla. Es un riesgo aceptado, no algo demostrado.

**Demuestra:** una vez, la ruta normativa completó sus tres pasos por LangChain, con un máximo de 14,1 s por paso.

**No demuestra:** que no supere los 30 s, que los 503 hayan desaparecido, ni que responda cuando flash-lite falla. Es el mismo proveedor, y no se ha probado qué pasa ante una falla común.

### 2. ¿Por qué necesito `with_fallbacks` y también `try/except`? ¿Qué cubre cada uno?

| Capa | Qué cubre | Sin ella |
| --- | --- | --- |
| `with_fallbacks` | Fallos dentro de una ruta: intenta con el secundario y, si no puede, entrega el texto de respaldo. | Cualquier fallo terminaría en el mensaje genérico, sin intentar rescatar la respuesta. |
| `try/except` | Lo que ocurre fuera de las rutas, sobre todo la clasificación, que corre antes de que exista una ruta. | Un fallo al clasificar terminaría en un traceback. |

Ninguna cubre `crear_modelo()`, que en `main()` corre antes del `try`.

### 3. ¿Por qué agregué `exigir_texto` si ya tenía dos capas de manejo de errores?

Porque ambas capas solo reaccionan a excepciones, y un bloqueo del proveedor no lanza ninguna: el conector devuelve a propósito un mensaje vacío (`langchain_google_genai/chat_models.py:2195`). Sin `exigir_texto`, el paso 3 escribiría una respuesta de aspecto normal a partir de nada. La función convierte ese fallo silencioso en un error para que actúe el fallback.

Lo cubre `test_respuesta_vacia_activa_el_fallback`. No detecta una respuesta truncada que traiga algo de texto, y nunca se probó con un bloqueo real.

## Fase 4: entrega y clon limpio

### 1. En la corrida final no aparece el artículo 37. ¿Puedes decir en qué paso se perdió? ¿Qué necesitarías para saberlo, y por qué marcaste CA-14 como cubierto?

No se puede saber, porque la salida del paso 2 no se imprime. Para saberlo habría que guardar esa salida intermedia.

CA-14 pide una respuesta coherente y el consumo en stderr, no exactitud legal. Por eso quedó "cubierto, con observaciones" y el problema figura en los límites. Un evaluador más estricto podría discutirlo, porque "coherente" es un criterio blando.

### 2. La corrida terminó con 0 consultas fallidas. ¿Qué demuestra eso sobre el manejo de errores, y qué evidencia tienes realmente de que el fallback funciona?

No demuestra nada sobre el manejo de errores, porque no ocurrió ningún error.

La evidencia del fallback son pruebas con fallos simulados: `test_cadena_normativa_usa_fallback_ante_fallo_del_modelo` confirma las 3 llamadas al secundario y `test_ruta_usa_texto_de_respaldo_si_fallan_ambos_modelos` confirma el texto de respaldo. Nunca se activó con un fallo real de Gemini.

Hay un dato parcial sobre los registros: contra el servidor local, el error de un 503 traía el cuerpo de la respuesta. Ese servidor no repetía la consulta, así que no responde si un error real de Gemini la repite. El primer límite de la entrega sigue abierto.

### 3. El clon pasó las 199 pruebas con `uv` y con `pip`. ¿Qué problemas detecta ese ensayo que no detectan las pruebas en tu carpeta, y cuáles sigue sin detectar?

**Detecta:** dependencias sin declarar, archivos sin commit, rutas absolutas, pasos que faltan en el README y un `.env` filtrado o sin plantilla.

**No detecta:** lo que la máquina esté tapando, como la caché, la versión de Python u otro sistema operativo. Tampoco mide la calidad de las respuestas, y desde el clon solo corrió la ruta de aclaración.
