# Guía de estudio: bloques 21 a 23

## Objetivo y fuente

Aprender a pasar de un flujo fijo a un agente que usa herramientas, conserva el
contexto de una conversación y necesita autorización humana para una acción
sensible. El dominio sigue siendo la Ley REP; no se entrenó un modelo nuevo.

Esta guía explica los requisitos del curso recogidos en el
[PRD 03](../planes/prd-03-agente-ley-rep.md#10-entregables-por-bloque) y los contrasta con el
código. No es una transcripción de la clase ni una rúbrica docente adicional.
Los resultados concretos están en la [entrega](../entregas/bloques-21-23.md).

Para ubicar esta etapa, consulta el
[mapa del módulo desde B18](modulo-2-desde-bloque-18.md#1-el-recorrido-en-una-sola-idea)
y la [guía de chains y rutas](bloques-18-20.md#1-qué-cambia-y-qué-debes-aprender).
No hace falta dominar primero todos los nombres de LangChain: sigue quién
propone una acción, quién la ejecuta y qué datos vuelven al modelo.

## Índice

1. [Mapa de la progresión](#mapa-de-la-progresión)
2. [Bloque 21: del flujo fijo al agente](#bloque-21-del-flujo-fijo-al-agente)
3. [Bloque 22: contratos de herramientas y memoria](#bloque-22-contratos-de-herramientas-y-memoria)
4. [Bloque 23: autonomía con supervisión](#bloque-23-autonomía-con-supervisión)
5. [Qué acabamos de depurar](#qué-acabamos-de-depurar)
6. [Costos y alcance de la evidencia](#costos-y-evidencia-qué-conclusiones-son-válidas)
7. [Laboratorio sin Gemini](#laboratorio-sin-gemini)
8. [Preguntas y respuestas de repaso](#preguntas-para-comprobar-que-lo-entendiste)

## Mapa de la progresión

| Etapa | Quién decide el recorrido | Qué aporta |
| --- | --- | --- |
| Bloques 18 a 20: chain y rutas | El programa define las rutas y los pasos; el modelo ayuda a clasificar. | Un flujo conocido y manejo de errores. |
| Bloque 21: agente | El modelo propone herramientas o una respuesta; el ejecutor realiza las llamadas permitidas. | Flexibilidad para resolver consultas diferentes. |
| Bloque 22: contratos y memoria | El código valida los argumentos y selecciona el historial de la sesión. | Herramientas menos ambiguas y continuidad entre turnos. |
| Bloque 23: supervisión | Una persona autoriza la acción sensible y el código aplica esa decisión. | Límites de autonomía y registros para revisar lo ocurrido. |

No reemplazamos la API ni el enrutamiento anterior. Agregamos una entrada por
terminal que reutiliza la ley local, el modelo y el registro de costos.

## Actividad, solución y aprendizaje de un vistazo

La progresión es **elegir herramientas → recordar el contexto → actuar con
supervisión**. El modelo puede proponer herramientas y argumentos; el programa
sigue controlando cuáles existen, cómo se ejecutan y qué se autoriza. No
entrenamos un modelo nuevo ni construimos todavía un RAG con embeddings.

| Bloque | Qué pedía la actividad, según el PRD 03 | Cómo lo resolvimos | Qué debes poder explicar |
| --- | --- | --- | --- |
| 21 | Implementar un agente con al menos dos herramientas. | `buscar_en_ley` busca por tema y `obtener_articulo` lee un artículo. `AgentExecutor` ejecuta las propuestas del modelo y devuelve los pasos intermedios. | La diferencia entre una chain y un agente, y el ciclo propuesta → ejecución → observación → respuesta. |
| 22 | Construir e integrar una herramienta personalizada; trabajar sus argumentos y la memoria de conversación. | Esquema Pydantic con `numero` y `transitorio`, errores de validación como observaciones e historial aislado por `session_id`. | Un esquema valida datos, no su veracidad; la memoria da contexto, no evidencia legal. |
| 23 | Documentar los límites de autonomía, apoyados en supervisión y trazas. | `entregar_informe` muestra el contenido, exige `s`, registra la decisión y solo entonces guarda un archivo local. Se documentan riesgos y se revisan repeticiones. | Por qué una instrucción de prompt no sustituye un control en código y por qué «no aprobado» no siempre significa «la persona escribió n». |

## Bloque 21: del flujo fijo al agente

### ¿Qué pedía la actividad?

Implementar un agente con **al menos dos herramientas**. En nuestro proyecto las
herramientas debían pertenecer al dominio de Ley REP y tener propósitos distintos.

### ¿Qué es una herramienta?

Es una función de Python que se expone al modelo con nombre, descripción y
argumentos. El modelo no ejecuta Python: produce una solicitud estructurada, por
ejemplo `obtener_articulo` con `{"numero": "34"}`. El programa ejecuta la función y
devuelve su resultado al modelo.

La descripción debe decir **cuándo usarla**, no solo cómo funciona internamente.
Si dos herramientas parecen hacer lo mismo, el modelo puede elegir de forma
inconsistente.

### ¿Qué implementamos?

En [herramientas.py](../../src/orquestacion/herramientas.py#L86):

- `buscar_en_ley(consulta)`: busca por palabras en la copia local y devuelve hasta
  tres artículos. Los textos largos se recortan y se indica cómo leerlos completos.
- `obtener_articulo(numero, transitorio=False)`: devuelve un artículo completo.
  El segundo parámetro y su esquema explícito se agregaron en el Bloque 22.

En [agente_con_herramientas.py](../../src/orquestacion/agente_con_herramientas.py#L65):

- `create_tool_calling_agent` conecta el modelo, las herramientas y el prompt.
- `AgentExecutor` ejecuta las herramientas propuestas y vuelve a consultar al
  modelo con las observaciones.
- `max_iterations=4` limita las vueltas al modelo.
- `return_intermediate_steps=True` permite revisar herramientas, argumentos y
  resultados, además de la respuesta final.

Usamos `langchain-classic` porque contiene las interfaces exigidas por esta
actividad con las versiones instaladas, no porque sea la recomendación para
cualquier proyecto nuevo.

### ¿Cómo es el ciclo?

```text
Consulta: «¿Qué obligaciones tienen los consumidores?»
→ Modelo solicita buscar_en_ley
→ Python devuelve fragmentos con sus referencias
→ Modelo puede solicitar obtener_articulo si necesita el texto completo
→ Python devuelve ese artículo
→ Modelo redacta la respuesta final
```

Una consulta como «Hola, ¿qué puedes hacer?» puede terminar sin herramientas.
Usarlas siempre también sería un error de diseño.

**Observación** significa el resultado de una herramienta, no el razonamiento
privado del modelo. Los pasos intermedios permiten auditar acciones, no leer su
pensamiento interno.

### Seguir una llamada sin confundir al modelo con Python

Para «¿Qué dice el artículo 34?», esta tabla muestra una secuencia posible,
**didáctica, no una nueva corrida real**:

| Momento | Quién trabaja | Qué entra | Qué sale |
| --- | --- | --- | --- |
| 1. Decidir | Modelo. | Reglas, consulta y descripción de herramientas; historial si existe. | Solicitud de `obtener_articulo` con `numero="34"` y `transitorio=false`. |
| 2. Ejecutar | Python, mediante el ejecutor. | Nombre y argumentos de la herramienta. | Texto del artículo local con su referencia, o aviso de problema. |
| 3. Responder | Modelo. | El contexto de la consulta más la solicitud y su observación. | Respuesta final basada en ese resultado. |

Dos llamadas al modelo y una ejecución local **no son tres llamadas a Gemini**.
La función no consulta al proveedor; las llamadas son las de decidir y redactar.
Si la primera observación no alcanza y el modelo pide otra herramienta, habrá
otra vuelta, dentro del límite.

El ejecutor no es otro modelo que piensa en paralelo: es el componente que
coordina el ciclo. `agent_scratchpad` transporta solicitudes y observaciones del
turno actual; `chat_history` aporta mensajes de turnos anteriores.

### Buscar por palabras todavía no es recuperar por embeddings

[`buscar_en_ley`](../../src/orquestacion/herramientas.py#L86) normaliza palabras,
quita términos sin tema y puntúa coincidencias en los artículos; una palabra
del título pesa el triple. Devuelve hasta tres artículos con puntaje positivo
y recorta los largos a 1.500 caracteres.

Eso puede fallar ante sinónimos sin coincidencia literal. El agente puede
reformular la búsqueda, pero no transforma esa función en un buscador vectorial.
La recuperación por significado llega en B24–28 como flujo separado.
Leer por número, por su parte, evita depender de un ranking si ya sabemos qué
artículo necesitamos.

### ¿Qué debes aprender y qué comprobamos?

Debes distinguir una secuencia definida por el programador de una selección de
acciones propuesta por el modelo. La autonomía sigue limitada por las herramientas
disponibles, sus validaciones y el ejecutor.

El ensayo real comprobó los tres casos previstos: búsqueda temática, lectura de
artículo y respuesta sin herramienta. Coincidieron 3 de 3, con 5 llamadas al
modelo. Es evidencia de esa corrida, no garantía de todas las elecciones futuras.

## Bloque 22: contratos de herramientas y memoria

### ¿Qué pedía la actividad?

Construir e integrar una herramienta personalizada. El bloque también trabaja
argumentos estructurados, historial y aislamiento entre conversaciones. Son dos
problemas distintos: **cómo se invoca una herramienta** y **qué contexto recibe
el modelo en cada turno**.

### ¿Para qué sirve `args_schema`?

Define el contrato de entrada de una herramienta mediante Pydantic: nombres,
tipos, valores por defecto y descripciones. Para
[`ArgumentosArticulo`](../../src/orquestacion/herramientas.py#L112) distinguimos:

```json
{"numero": "1", "transitorio": false}
```

del artículo primero transitorio:

```json
{"numero": "primero", "transitorio": true}
```

Así la diferencia no depende de interpretar una sola cadena ambigua. También
existe un esquema para el título y el contenido de los informes del Bloque 23.
La búsqueda, de un único texto, conserva el esquema inferido por `@tool`.

Un argumento inválido vuelve al agente como observación explicativa, para que
pueda corregir la solicitud dentro del límite de pasos. **Validar el formato no
garantiza que el artículo sea pertinente ni que una afirmación sea verdadera.**

### Tres controles distintos: forma, existencia y pertinencia

| Pregunta | Quién la responde | Ejemplo |
| --- | --- | --- |
| ¿Los argumentos cumplen el esquema? | Pydantic y la configuración de la herramienta. | Deben incluir `numero`; `transitorio` tiene valor por defecto. |
| ¿Existe ese artículo en nuestra copia? | La lógica local de lectura. | `{"numero": "99"}` cumple la forma, pero la lectura informa que no está disponible. |
| ¿Ese artículo respalda lo que estoy afirmando? | Revisión del texto y su uso en la respuesta. | Un artículo existente y bien leído puede ser irrelevante para la pregunta. |

Un error de argumentos puede volver al modelo como observación para corregirlo.
No garantiza que lo corrija, y la vuelta adicional consume parte del presupuesto
de llamadas. Un esquema no reemplaza una evaluación del contenido.

### ¿Qué significa que el agente tenga memoria?

No significa que Gemini aprendió ni que cambiamos sus pesos. El programa guarda
mensajes y los vuelve a incluir en la siguiente llamada al modelo.

[`RunnableWithMessageHistory`](../../src/orquestacion/agente_con_herramientas.py#L107)
selecciona un `InMemoryChatMessageHistory` por `session_id`:

```text
cliente-1, turno 1: «¿Qué dice el primero transitorio?»
cliente-1, turno 2: «¿Y el transitorio siguiente?»
→ Recibe el turno anterior y puede interpretar «siguiente».

cliente-2, turno 1: «¿Sobre qué artículo te pregunté recién?»
→ No recibe la conversación de cliente-1.
```

La sesión es una clave de separación, **no una contraseña ni autenticación**.
Se conserva solo dentro del mismo proceso. Ejecutar dos comandos independientes
con el mismo `--sesion` no recupera la conversación anterior.

### ¿Qué ajuste técnico necesitó la memoria?

Gemini puede devolver bloques de contenido, mientras que nuestro historial
necesita texto. Por eso
[`salida_como_texto`](../../src/orquestacion/agente_con_herramientas.py#L76) convierte
la respuesta **antes** de guardarla. También rechaza salidas vacías y traduce el
aviso de límite de pasos.

### ¿Qué debes aprender y qué comprobamos?

- Una conversación necesita identidad de sesión y separación de historiales.
- Recordar lo dicho por el usuario no lo convierte en evidencia legal: hay que
  volver a consultar la fuente cuando la respuesta depende de la ley.
- El historial guarda pregunta y respuesta final, no las observaciones de las
  herramientas. Crece sin resumen ni límite y se pierde al cerrar el proceso.
- Reenviarlo consume tokens de entrada en cada turno.

El ensayo real coincidió en 3 de 3 casos: el segundo turno de `cliente-1` consultó
el segundo transitorio y `cliente-2` empezó sin historial ajeno. No es una prueba
de persistencia entre reinicios, porque esa función no existe.

### Interpretar los mensajes y tokens de la corrida real

El [ensayo conservado de B22](../evidencias/bloques-21-23/ensayo-bloque-22.json)
permite leer algo más que «3 de 3»:

| Consulta | Sesión | Mensajes previos | Acción observada | Llamadas al modelo | Tokens de entrada / salida |
| --- | --- | ---: | --- | ---: | ---: |
| Primero transitorio. | `cliente-1` | 0 | Lee el primero transitorio. | 2 | 1.223 / 147 |
| «El transitorio siguiente». | `cliente-1` | 2 | Lee el segundo transitorio. | 2 | 1.563 / 208 |
| «¿Sobre qué artículo te pregunté recién?». | `cliente-2` | 0 | Responde sin herramienta ni historial de la otra sesión. | 1 | 522 / 33 |

Después del primer turno exitoso hay **dos mensajes**: pregunta y respuesta final.
Después del segundo hay cuatro en esa sesión; las observaciones no se agregan
como mensajes permanentes de ese historial. Por eso dos llamadas al modelo
en un turno no implican cuatro mensajes nuevos guardados.

Los totales fueron 1.370 → 1.771 tokens en `cliente-1`. No podemos atribuir
los 401 adicionales solo a memoria: también cambiaron el artículo leído y
la respuesta. Sabemos por el código que se reenvía el historial, pero esa
comparación no aísla su costo. Para medirlo necesitaríamos mantener iguales
consulta, observación y demás condiciones, variando solo el historial.

Los casos prueban continuidad e aislamiento en esa ejecución. No prueban que
`session_id` autentique usuarios, que el modelo nunca confunda referencias o que
el historial persista al reiniciar. Tampoco hacen de una respuesta previa una
fuente de lo que dice la ley.

## Bloque 23: autonomía con supervisión

### ¿Qué pedía la actividad?

**Documentar los límites de autonomía del agente**, apoyados por el código y las
trazas. No bastaba con escribir «hay supervisión»: debía existir un punto real de
aprobación antes de la acción sensible y evidencia para revisar sus resultados.

La adaptación al proyecto es una entrega de informe. Representa una acción
dirigida a terceros, pero la implementación es deliberadamente **simulada**:
solo crea un archivo local, nunca envía correos ni publica documentos.

### ¿Qué implementamos?

[`entregar_informe`](../../src/orquestacion/herramientas.py#L177):

1. Recibe el título y el contenido, validados con Pydantic.
2. Obtiene la sesión del contexto de ejecución, no de un argumento del modelo.
3. Muestra el informe completo y llama a `esperar_aprobacion`.
4. Espera hasta 300 segundos en una terminal interactiva.
5. Registra la decisión antes de actuar.
6. Solo con `s` y un registro exitoso intenta guardar el Markdown local.

`n`, Enter vacío, silencio, EOF, entrada no interactiva o error no aprueban.
Se llama **fallo seguro**: ante la duda no se ejecuta la acción. El nombre del
archivo lo genera el programa y no se sobrescribe un informe anterior.

### Ejemplo del recorrido completo de una entrega

```text
Usuario pide un informe del artículo 34
→ Modelo propone obtener_articulo
→ Python lee la copia local y devuelve el texto
→ Modelo propone entregar_informe con título y contenido
→ Python muestra el informe y espera a la persona
→ s: registra la aprobación y guarda el archivo si no hay error
→ n, silencio o fallo: no guarda ni envía el informe
→ Modelo recibe el resultado de la herramienta y responde
```

Ni siquiera con `s` se envía algo a un cliente real: solo se autoriza el guardado
local de esta simulación.

### Leer la aprobación como un proceso, no como un solo booleano

La propuesta, la autorización y el guardado son eventos distintos. La
[`herramienta de entrega`](../../src/orquestacion/herramientas.py#L177) los
ordena para no confundir intención con efecto:

| Situación | ¿Puede existir decisión registrada? | ¿Qué podemos afirmar del informe? |
| --- | --- | --- |
| La persona escribe `n` y se registra la decisión. | Sí, `aprobado: false`. | La herramienta no lo guarda; hubo rechazo explícito observado. |
| Se agota el tiempo o llega EOF y se registra la decisión. | Sí, también `false`. | No se guarda, pero no demuestra que una persona escribió `n`. |
| La persona escribe `s`, pero falla el registro. | No hay confirmación del registro. | No se intenta guardar el informe. |
| Se registra `true`, pero falla la escritura del informe. | Sí, `aprobado: true`. | La autorización existe; la entrega no está confirmada. |
| Se registra `true` y se escribe el archivo. | Sí. | Se completó el guardado local, no un envío externo. |
| Se guarda y después falla el modelo al responder. | Sí; el archivo puede seguir presente. | El mensaje seguro del agente no revierte la acción ya hecha. |

Por eso «el ensayo coincide con el booleano esperado» no basta para afirmar
«el alumno rechazó con `n`». En nuestro cierre se contrastaron entrada humana,
decisión, sesión/identificador y presencia o ausencia del archivo. Los intentos
anteriores no se borraron para que pareciera que todo funcionó a la primera.

Tampoco hay que esperar necesariamente 300 segundos para obtener `false`: EOF,
entrada no interactiva o Enter vacío terminan antes. El tiempo máximo no es
una demora obligatoria ni prueba de la causa de una corrida antigua.

### ¿Por qué el control debe estar dentro de la herramienta?

Decirle al modelo «pide permiso» es una instrucción, no una garantía. En cambio,
cada invocación de nuestra herramienta pasa por la aprobación en Python.

Esa barrera no valida la exactitud del informe. Citar bien, leer la ley antes y
no insistir después de un rechazo siguen siendo instrucciones del prompt; la
persona tiene que revisar el contenido. No es asesoría legal.

### ¿Por qué no reintentamos todo el agente ante un error?

Una herramienta podría haber guardado un informe aprobado y el modelo fallar
después, al redactar la respuesta final. Repetir el flujo o cambiar de modelo
podría duplicar la acción.

Por eso este agente no hereda el fallback del enrutamiento anterior. Devuelve un
mensaje seguro y conserva los registros independientes. Una aprobación tampoco
prueba que el guardado terminó: hay que comprobar el archivo y el resultado de
la herramienta.

### ¿Qué diferencia hay entre historial, traza y aprobación?

| Elemento | Para qué sirve | Dónde vive |
| --- | --- | --- |
| Historial | Entender referencias de los turnos siguientes. | Memoria del proceso, separado por sesión. |
| `intermediate_steps` | Examinar las llamadas y observaciones de una ejecución. | Resultado del ejecutor; se usa para construir la traza. |
| Traza JSONL | Revisar consulta, herramientas, argumentos, observaciones, respuesta y errores. | `output/agente/trazas_agente.jsonl`. |
| Registro de aprobación | Relacionar una propuesta de informe y su decisión con un identificador. | `output/agente/aprobaciones.jsonl`. |
| Informe aprobado | Materializar la entrega simulada. | `output/agente/informes_entregados/<id>.md`. |

JSONL es un objeto JSON por línea: se agregan eventos sin reescribir los
anteriores. No es una base de datos protegida contra alteraciones. Las trazas
contienen texto completo, así que no hay que introducir secretos ni datos
personales ni publicar esos archivos sin revisarlos.

El detector de repeticiones marca sesiones con la misma herramienta usada dos
veces seguidas. **Es una señal para revisar**, no prueba de un bucle ni un bloqueo
automático. Dos lecturas consecutivas pueden ser necesarias.

## Qué acabamos de depurar

En una corrida con Gemini, el informe quedó sin aprobar antes de que el alumno
pudiera escribir `n`. Como duró unos siete segundos, no fue el timeout de 300.
El código anterior no mostraba el motivo; los registros booleanos no permiten
reconstruirlo. No se atribuye una causa que no se observó.

Agregamos:

- Motivo y duración en stderr: `s`, `n`, línea vacía, EOF, timeout o error.
- Instrucción explícita de escribir una letra y pulsar Enter, sin menú.
- Un diagnóstico del circuito memoria → ejecutor → herramienta → terminal con
  modelo falso, red bloqueada y archivos temporales.
- Pruebas automáticas con pseudoterminal para entradas consecutivas y Enter vacío.

El alumno ejecutó `uv run python -m tests.orquestacion.ensayo_terminal` y compartió:

```text
Resultado de aprobación: s recibida: aprobación explícita; espera: 5.6 s.
Resultado de aprobación: n recibida: rechazo explícito; espera: 4.4 s.
Decisiones simuladas: [true, false]
```

**Sí demuestra:** el circuito probado leyó las dos decisiones humanas y no las
confundió con silencio o EOF. **No demuestra:** la causa del incidente anterior,
el comportamiento del conector real de Gemini ni una autorización para una
entrega real. Se eliminaron los archivos temporales.

La salida y su alcance están en el
[diagnóstico conservado](../evidencias/bloques-21-23/diagnostico-aprobacion.md#resultado-compartido-por-el-alumno).

Después el alumno ejecutó el agente con Gemini y la sesión `rechazo-final-23`.
La terminal leyó `n` tras 21,6 segundos; se contrastaron la decisión negativa,
la traza sin error y la ausencia del informe. Esta
[evidencia real](../evidencias/bloques-21-23/rechazo-explicito-gemini.md) completa el
control de rechazo. No explica la causa del incidente anterior ni exige otra
consulta pagada.

## Costos y evidencia: qué conclusiones son válidas

- Usar una herramienta local no llama por sí mismo a Gemini. El costo aparece al
  pedirle al modelo que decida y luego que procese la observación.
- Sin herramientas suele bastar una llamada; con una lectura y respuesta suelen
  ser dos; leer, proponer entrega y responder suele usar tres.
- Cuatro iteraciones limitan las llamadas al modelo, **no a cuatro herramientas**:
  una respuesta del modelo puede solicitar varias juntas.
- Memoria, definiciones de herramientas y observaciones agregan contexto y tokens.
- Las pruebas con modelo falso comprueban conexiones y controles, no la calidad
  de las decisiones ni la exactitud jurídica del modelo real.
- Los ensayos con Gemini prueban casos observados, no una precisión universal.
- `aprobado: false` puede significar `n`, timeout, EOF u otro fallo. Un resultado
  automático coincidente no reemplaza observar la entrada humana explícita.
- Un fallo sin metadatos de uso no se registra como si costara cero.

El cierre de B21–23 registró **263 pruebas y 481 subpruebas** sin red, con `ruff`
y `basedpyright` sin errores; es un conteo histórico, no el tamaño actual de la
suite completa tras agregar RAG. Los avisos de memoria son
deprecaciones: no invalidan esa ejecución, pero anticipan una migración futura.
El detalle y la revisión de instalación local están en
[verificación local](../evidencias/bloques-21-23/verificacion-local.md).

## Qué está hecho y qué falta

| Estado | Alcance |
| --- | --- |
| Implementado | Herramientas, argumentos estructurados, memoria por sesión, aprobación, entrega simulada, trazas y detector de repeticiones. |
| Comprobado sin red | Controles, errores, aislamiento y flujo con modelo falso; diagnóstico humano con `s` y `n`. |
| Comprobado con Gemini | Ensayos de 21 y 22, una entrega aprobada y rechazo explícito con `n` en `rechazo-final-23`, contrastado con decisión, traza y archivo ausente. Se conservan los intentos anteriores con sus diferencias. |
| Validación funcional | Completada para el alcance de los bloques 21 a 23. No se requiere repetir las consultas. |
| Publicación e instalación | Merge autorizado y publicado únicamente en `main`; rama de bloques conservada local. Instalación y pruebas verificadas desde un clon limpio de GitHub. |

Las decisiones humanas de las corridas reales las tomó el alumno; no se
automatizaron ni se hicieron nuevas llamadas para redactar esta guía.
La [comprobación desde GitHub](../evidencias/bloques-21-23/verificacion-github.md)
completó el cierre sin usar claves ni consumir tokens.
El [checklist de entrega](../entregas/bloques-21-23.md#condiciones-para-marcar-la-entrega-como-cerrada)
es la referencia para declarar el trabajo cerrado.

No son pendientes de esta actividad: embeddings y recuperación semántica,
memoria persistente, un endpoint para el agente, envío real a clientes o migración
a LangGraph. Son extensiones fuera del alcance actual, no funciones ya construidas.
Los riesgos vigentes se detallan en [límites de autonomía](../arquitectura/limites-autonomia-agente.md).

## Laboratorio sin Gemini

Estos ejercicios son repaso opcional, no otra entrega ni una solicitud de repetir
la aprobación o el rechazo real. Desde la raíz, con dependencias instaladas:

```bash
uv run python -m pytest tests/orquestacion/test_herramientas.py -v
uv run python -m pytest tests/orquestacion/test_agente_con_herramientas.py -v
uv run python -m pytest tests/orquestacion/test_supervision.py -v
```

La [suite bloquea la red](../../tests/conftest.py#L8), sustituye las respuestas del
modelo y usa archivos temporales para las acciones. No necesita una clave real
ni llama a Gemini. La instalación de dependencias, si faltaran, es un paso aparte.

| Repaso | Prueba para leer | Pregunta antes de ejecutarla |
| --- | --- | --- |
| Propuesta y observación. | [`test_agente_registra_la_herramienta_elegida`](../../tests/orquestacion/test_agente_con_herramientas.py#L44). | ¿Qué eligió el modelo falso y qué ejecutó Python? |
| Límite de autonomía. | [`test_agente_se_detiene_en_el_limite_de_pasos`](../../tests/orquestacion/test_agente_con_herramientas.py#L76). | ¿Qué devuelve el agente si sigue solicitando herramientas? |
| Continuidad. | [`test_segundo_turno_recibe_el_primero`](../../tests/orquestacion/test_agente_con_herramientas.py#L216). | ¿Qué mensajes debe recibir el segundo turno? |
| Aislamiento. | [`test_sesiones_distintas_no_comparten_historial`](../../tests/orquestacion/test_agente_con_herramientas.py#L240). | ¿Qué debe quedar fuera de la segunda sesión? |
| Fallo tras autorización. | [`test_entregar_informe_fallo_de_guardado_conserva_aprobacion`](../../tests/orquestacion/test_herramientas.py#L232). | ¿Por qué una aprobación no demuestra un archivo guardado? |
| Fallo después de actuar. | [`test_fallo_tras_entrega_conserva_aprobacion_y_no_repite`](../../tests/orquestacion/test_agente_con_herramientas.py#L194). | ¿Por qué repetir todo podría duplicar una acción? |

Para analizar evidencia real sin nuevas llamadas, abre el
[ensayo de memoria](../evidencias/bloques-21-23/ensayo-bloque-22.json) y el
[rechazo final](../evidencias/bloques-21-23/rechazo-explicito-gemini.md).
Busca sesión, argumentos, mensajes previos y resultado, no solo el contador de
coincidencias. Es lectura de resultados históricos, no reproducción del ensayo.

## Preguntas para comprobar que lo entendiste

Intenta responder sin mirar las secciones anteriores:

1. ¿Por qué el modelo propone una herramienta, pero no ejecuta Python?
2. ¿Cuándo conviene buscar por tema y cuándo leer un artículo directamente?
3. ¿Qué valida Pydantic y qué no puede validar sobre una respuesta legal?
4. ¿En qué se diferencian `chat_history` y `agent_scratchpad`?
   El primero contiene turnos previos; el segundo, llamadas y observaciones del
   turno actual. Ninguno cambia los pesos del modelo.
5. ¿Qué ocurre si repites el mismo `session_id` en un proceso nuevo?
6. ¿Por qué la memoria no se considera evidencia de lo que establece la ley?
7. ¿Qué impide que `entregar_informe` guarde sin aprobación?
8. ¿Por qué `aprobado: false` no demuestra que una persona escribió `n`?
9. ¿Por qué sería peligroso reintentar todo después de una entrega aprobada?
10. ¿Qué prueba el diagnóstico con modelo falso y qué aporta la comprobación posterior con Gemini?

Si puedes explicar el recorrido **consulta → propuesta de herramienta → ejecución
→ observación → aprobación cuando corresponda → respuesta y registros**, y
distinguir lo implementado de lo realmente observado, comprendiste la idea
central de estos tres bloques.

### Respuestas breves para contrastar

1. El modelo produce una solicitud estructurada; el ejecutor llama a una función
   permitida. El modelo no dispone por ello de ejecución arbitraria.
2. Por tema, cuando no conocemos el artículo; por número, cuando está nombrado o
   hay que leer completo un resultado recortado.
3. Pydantic valida la forma de los argumentos según el esquema. No demuestra
   existencia, pertinencia ni exactitud jurídica.
4. `chat_history` contiene los turnos guardados de la sesión; `agent_scratchpad`,
   solicitudes y observaciones del turno actual. No son razonamiento privado.
5. En un proceso nuevo el historial está vacío, aunque se reutilice el nombre.
6. Una conversación puede contener errores o afirmaciones del usuario: hay que
   contrastar la ley con una herramienta, no citar la memoria como fuente.
7. La herramienta exige aprobación afirmativa y registro exitoso antes de
   intentar escribir. Un prompt por sí solo no impone esa barrera.
8. El mismo `false` representa rechazo explícito o distintas formas de no obtener
   autorización. Hace falta evidencia del motivo.
9. El efecto puede haberse completado antes del fallo final; repetir todo
   podría crear una segunda entrega.
10. El diagnóstico falso verifica el circuito de entrada sin proveedor; el
    control posterior comprueba el caso con Gemini. Ninguno explica por sí solo
    la causa del incidente anterior.

**Siguiente paso:** [RAG, evaluación y mediciones de B24–28](bloques-24-28.md#1-qué-cambia-respecto-de-los-bloques-anteriores).
Ahora cambiamos cómo obtenemos evidencia, no convertimos el historial en ley
ni damos más permisos al agente.
