# Preguntas y respuestas: bloques 18 a 20

Guía de estudio para defender la orquestación con LangChain. Intenta responder cada pregunta antes de leer su respuesta.

Las respuestas se redactaron con ayuda de Claude y se comprobaron el 7 de noviembre de 2026 contra el commit `4a2622c`, con `langchain` 1.4.9, `langchain-core` 1.7.6, `langchain-google-genai` 4.4.3 y `google-genai` 2.34.0. Las mediciones de esta guía no usaron Gemini: se hicieron en una copia temporal del código y con un servidor local que siempre responde HTTP 503. Los resultados de las corridas reales están en la [entrega](entrega-bloques-18-20.md).

## Índice

1. [Fase 0: dependencias](#fase-0-dependencias)
2. [Fase 1: chain de tres pasos](#fase-1-chain-de-tres-pasos)
3. [Fase 2: clasificación y rutas](#fase-2-clasificación-y-rutas)
4. [Fase 3: manejo de errores](#fase-3-manejo-de-errores)
5. [Fase 4: entrega y clon limpio](#fase-4-entrega-y-clon-limpio)

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
