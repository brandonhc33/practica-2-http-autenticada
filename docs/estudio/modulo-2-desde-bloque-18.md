# Mapa de estudio del módulo 2: desde el bloque 18

## Para qué sirve esta guía

Conectar las actividades con lo que construimos, sin tener que memorizar primero
los nombres de LangChain. Este recorrido cubre **los bloques 18 a 30 ya trabajados
en el repositorio**; no pretende cubrir las unidades posteriores del módulo 2.

Si aparecen demasiados términos nuevos, usa el
[glosario con ejemplos cotidianos y diagramas](glosario.md#diez-conceptos-para-empezar).
Puedes empezar por diez conceptos y volver al resto cuando aparezcan en una guía.

Las fuentes son los requisitos conservados en los
[PRD 02](../planes/prd-02-orquestacion-langchain.md#10-entregables-por-bloque),
[PRD 03](../planes/prd-03-agente-ley-rep.md#10-entregables-por-bloque),
[PRD 04](../planes/prd-04-rag-ley-rep.md#2-fuente-y-requisitos-del-curso) y
[PRD 05](../planes/prd-05-personalizacion-ley-rep.md#2-fuente-y-requisitos-del-curso), junto con
el código y las evidencias enlazadas en cada guía. No es una nueva transcripción
del curso ni cambia el estado de las entregas.

## Índice

1. [El recorrido en una sola idea](#1-el-recorrido-en-una-sola-idea)
2. [Siete conceptos que conviene separar](#2-siete-conceptos-que-conviene-separar)
3. [La misma consulta en tres sistemas](#3-la-misma-consulta-en-tres-sistemas)
4. [Orden recomendado de estudio](#4-orden-recomendado-de-estudio)
5. [Cómo saber qué parte no entendí](#5-cómo-saber-qué-parte-no-entendí)
6. [Qué significa haberlo comprendido](#6-qué-significa-haberlo-comprendido)

## 1. El recorrido en una sola idea

**Primero organizamos el trabajo, después permitimos elegir acciones, luego
mejoramos cómo llega la evidencia, decidimos si hace falta cambiar el modelo mismo
y, al final, agregamos registros, controles y autorizaciones.** Son problemas relacionados, no una lista de
librerías que haya que usar siempre juntas.

| Bloques | Pregunta central | Qué construimos | Guía para profundizar |
| --- | --- | --- | --- |
| 18 | ¿Cómo separo una tarea en pasos conectados? | Interpretar → responder con la ley → simplificar. | [Chain y movimiento de datos](bloques-18-20.md#3-bloque-18-seguir-los-datos-de-una-chain). |
| 19 | ¿Todas las preguntas necesitan ese mismo recorrido? | Clasificador y rutas de normativa, resumen o aclaración. | [Categoría frente a decisión de ruta](bloques-18-20.md#4-bloque-19-clasificar-no-es-decidir-toda-la-ruta). |
| 20 | ¿Qué ocurre cuando una pieza falla? | Fallbacks, mensajes seguros y pruebas del flujo. | [Errores frente a respuestas incorrectas](bloques-18-20.md#5-bloque-20-fallar-sin-inventar-una-respuesta). |
| 21 | ¿Y si no conozco de antemano todos los pasos necesarios? | Agente que propone herramientas; Python las ejecuta. | [Ciclo del agente](bloques-21-23.md#bloque-21-del-flujo-fijo-al-agente). |
| 22 | ¿Cómo invoca bien las herramientas y entiende el turno siguiente? | Argumentos estructurados e historial por sesión. | [Contratos y memoria](bloques-21-23.md#bloque-22-contratos-de-herramientas-y-memoria). |
| 23 | ¿Qué acciones no debe realizar por su cuenta? | Aprobación humana antes de guardar un informe simulado y registros. | [Supervisión y autonomía](bloques-21-23.md#bloque-23-autonomía-con-supervisión). |
| 24–25 | ¿Cómo preparo y conservo documentos para buscarlos por significado? | Chunks, embeddings e índice persistente en Chroma. | [Indexación](bloques-24-28.md#2-bloque-24-documentos-chunks-y-embeddings) y [persistencia](bloques-24-28.md#3-bloque-25-persistencia-y-diagnóstico). |
| 26 | ¿Cómo respondo con lo que recuperé y dejo sus fuentes visibles? | Pregunta → recuperación → contexto numerado → generación y mapa de citas. | [Recuperación y citas](bloques-24-28.md#4-bloque-26-recuperación-contexto-y-citas). |
| 27 | ¿Recuperé la evidencia que necesitaba? | Casos etiquetados, precisión y recall. | [Interpretación de métricas](bloques-24-28.md#5-bloque-27-precisión-y-recall). |
| 28 | ¿Cuánto tarda y qué consumo tiene ese flujo? | Tiempos por etapa, tokens y costo conocido. | [Latencia y costo](bloques-24-28.md#6-bloque-28-latencia-tokens-y-costo). |
| 29 | ¿Qué técnica responde a mi problema: RAG, fine-tuning, PEFT o soft-prompting? | Dataset validado para el clasificador de rutas; comprobación local de PEFT. | [Cuatro técnicas](bloques-29-30.md#2-bloque-29-cuatro-formas-de-personalizar) y [dataset](bloques-29-30.md#3-bloque-29-el-dataset-de-nuestro-proyecto). |
| 30 | ¿Conviene entrenar, con qué costo y con qué evidencia? | Método puntuado, línea base del clasificador y documento de decisión. | [Costos](bloques-29-30.md#5-bloque-30-lo-que-cuesta-personalizar) y [método](bloques-29-30.md#6-bloque-30-el-método-de-decisión). |
| 31 | ¿Puedo saber qué pasó en una consulta y limitar una orden escondida en un documento? | Eventos JSON con `trace_id`, consumo, filtro de inyección y citas obligatorias. | [Registros](bloques-31-32.md#2-bloque-31-registros-que-se-pueden-consultar) e [inyección](bloques-31-32.md#4-bloque-31-inyección-de-prompt). |
| 32 | ¿Quién autoriza un cambio y qué riesgos quedan? | Versiones de prompt, pausa con decisión humana y matriz de riesgos. | [Pausar](bloques-31-32.md#7-bloque-32-pausar-antes-de-actuar) y [riesgos](bloques-31-32.md#8-bloque-32-matriz-de-riesgos). |
| Gate 2 | ¿Funciona todo junto, desde cero y con más de una norma? | Servicio completo, índice incremental y dos puertas con firma. | [Guía del Gate 2](gate-2.md#1-la-idea-en-una-imagen). |

No reescribimos un único programa que se convierte en todo lo anterior.
La API, el router, el agente y el RAG siguen siendo entradas diferentes.
En particular, **nuestro RAG no fue añadido como herramienta del agente**:
implementa un recorrido fijo separado. Esa integración sería otro trabajo.
Tampoco entrenamos un modelo en los bloques 29 y 30: preparamos el dataset y
decidimos con evidencia si convendría hacerlo. Los bloques 31 y 32 agregan un camino
RAG auditable; no cambian la API, el agente ni la medición del B28.

## 2. Siete conceptos que conviene separar

| Concepto | Qué significa aquí | No significa |
| --- | --- | --- |
| Prompt | Instrucciones y datos que recibe el modelo en una llamada. | Una garantía de obediencia o de verdad. |
| Chain | Piezas conectadas con entradas y salidas definidas. | Un modelo entrenado nuevo ni necesariamente un agente. |
| Herramienta | Función que el programa permite solicitar con argumentos. | Que el modelo pueda ejecutar cualquier Python o actuar sin límites. |
| Memoria de conversación | Mensajes anteriores que el programa vuelve a enviar. | Aprendizaje de pesos, persistencia automática ni fuente normativa. |
| RAG | Recuperar documentos y aportarlos al generador como evidencia. | Fine-tuning ni autonomía para elegir acciones. |
| Evaluación | Comparar un comportamiento con un criterio explícito. | Que una única cifra certifique todo el sistema. |
| Fine-tuning o PEFT | Entrenar con ejemplos para cambiar el comportamiento del modelo. | Una forma de agregar información que cambia; para eso está RAG. |

**Contexto** es la información que recibe el modelo en esa llamada. Puede incluir
instrucciones, historial y documentos, pero no tienen la misma función:
el historial explica a qué se refiere «el siguiente»; la ley respalda una
afirmación; las instrucciones fijan la tarea. Confundirlos hace que una respuesta
anterior del asistente parezca una fuente legal cuando no lo es.

También conviene separar responsabilidades:

- **El modelo** interpreta, clasifica, propone herramientas o redacta.
- **Python** conecta pasos, comprueba datos, ejecuta funciones permitidas, limita
  iteraciones y aplica la aprobación.
- **La persona** revisa contenido y autoriza la acción sensible cuando corresponde.
- **Las evidencias** permiten contrastar qué pasó; no sustituyen esos controles.

## 3. La misma consulta en tres sistemas

Usaremos «Resume el artículo 9» para comparar recorridos. Es un ejemplo
didáctico, **no tres nuevas corridas reales**:

| Sistema | Recorrido | Llamadas en el caso explicado | De dónde llega el texto legal |
| --- | --- | --- | --- |
| Router B18–20 | Clasifica como resumen, comprueba que exista el artículo y lo resume. | 2 al modelo si no hay fallos. | Lectura exacta del artículo nombrado. |
| Agente B21–23 | Propone `obtener_articulo`, Python lo lee y el modelo resume su observación. | Normalmente 2 al modelo para esa secuencia; la elección no está fijada. | Resultado de la herramienta local. |
| RAG B24–28 | Obtiene el vector de la pregunta, recupera k chunks y genera con ese contexto. | 1 embedding de consulta y 1 generación, con el índice ya preparado. | Vecinos del índice; no una selección exacta garantizada por número de artículo. |

La chain de B18 **invocada sola**, sin router, sí haría interpretar, responder y
simplificar: tres llamadas con toda la ley en el segundo paso. No confundir esa
entrada con la ruta de resumen de B19.

¿Cuál es mejor? Depende del problema:

- Si el usuario nombra un artículo y queremos leerlo exactamente, la consulta
  directa es más predecible que buscar vecinos por significado.
- Si necesita combinar varias operaciones cuyo orden depende de sus resultados,
  un agente puede aportar flexibilidad, con más controles y costo variable.
- Si pregunta por un tema distribuido en documentos, recuperar fragmentos puede
  evitar enviar el corpus completo. Sigue siendo necesario revisar si llegaron
  los adecuados y si la respuesta los usa fielmente.

**Más autonomía, más pasos o más contexto no equivalen por sí solos a mejor
calidad.** Esa es una de las conclusiones que conecta todo el recorrido.

## 4. Orden recomendado de estudio

No hace falta ejecutar nuevas consultas pagadas. Los ejercicios de las guías
usan pruebas sin Gemini o lectura de evidencias ya conservadas. Son repaso
opcional y no añaden requisitos de entrega.

| Sesión de estudio | Lectura | Ejercicio antes de avanzar |
| --- | --- | --- |
| 1. Entender los datos | [Guía 18–20, secciones 1 a 3](bloques-18-20.md#1-qué-cambia-y-qué-debes-aprender). | Dibujar qué campos recibe cada paso y contar solo las llamadas al modelo. |
| 2. Elegir y proteger rutas | [Guía 18–20, secciones 4 a 7](bloques-18-20.md#4-bloque-19-clasificar-no-es-decidir-toda-la-ruta). | Explicar por qué «artículo 99» pide aclaración y qué cambia al fallar el principal. Leer el análisis histórico al final después, no como punto de partida. |
| 3. Separar decisión y ejecución | [Guía 21–23](bloques-21-23.md#bloque-21-del-flujo-fijo-al-agente). | Reconstruir una propuesta de herramienta, su observación y la respuesta. Separar historial, traza y aprobación. |
| 4. Encontrar evidencia | [Guía 24–28, secciones 2 a 4](bloques-24-28.md#2-bloque-24-documentos-chunks-y-embeddings). | Dibujar documento → chunk → vector → índice, y pregunta → recuperación → contexto → cita. |
| 5. Interpretar resultados | [Guía 24–28, secciones 5 a 8](bloques-24-28.md#5-bloque-27-precisión-y-recall). | Explicar por qué recall 1 y precisión 0,30 pueden coexistir; distinguir costo de generación y costo completo del RAG. |
| 6. Decidir si personalizar | [Guía 29–30](bloques-29-30.md#1-qué-cambia-respecto-de-los-bloques-anteriores). | Clasificar tres problemas como información o comportamiento y explicar por qué un empate no se resuelve con `max()`. |
| 7. Observar y gobernar | [Guía 31–32](bloques-31-32.md#1-qué-cambia-respecto-de-los-bloques-anteriores). | Reconstruir una consulta con su `trace_id` y explicar qué controles son de Python, cuáles del prompt y cuáles de una persona. |
| 8. Integrar y comprobar | [Guía del Gate 2](gate-2.md#1-la-idea-en-una-imagen). | Explicar por qué un promedio de 88,8 puede no aprobar y por qué una norma a medias no debe responder. |

En cada sesión usa este orden: **problema → ejemplo → código → evidencia →
limitación**. Si puedes explicar el ejemplo con tus palabras, entonces los
nombres de las clases empiezan a tener un propósito.

## 5. Cómo saber qué parte no entendí

| Duda | Volver a |
| --- | --- |
| «No sé qué hace `assign` ni qué se pierde entre pasos». | [Movimiento de datos de B18](bloques-18-20.md#3-bloque-18-seguir-los-datos-de-una-chain). |
| «Si el modelo dijo resumen, ¿por qué pide aclaración?». | [Condiciones del router](bloques-18-20.md#4-bloque-19-clasificar-no-es-decidir-toda-la-ruta). |
| «Respondió texto, así que no hubo ningún error». | [Error técnico frente a error de contenido](bloques-18-20.md#5-bloque-20-fallar-sin-inventar-una-respuesta). |
| «El modelo ejecuta la función por su cuenta». | [Ciclo propuesta y observación](bloques-21-23.md#cómo-es-el-ciclo). |
| «La memoria ya contiene la ley porque antes la citamos». | [Memoria frente a evidencia](bloques-21-23.md#qué-significa-que-el-agente-tenga-memoria). |
| «Aprobación verdadera significa archivo entregado». | [Estados de una entrega](bloques-21-23.md#leer-la-aprobación-como-un-proceso-no-como-un-solo-booleano). |
| «Chroma recuerda mis conversaciones». | [Qué guarda el índice](bloques-24-28.md#qué-guarda-chroma). |
| «Precisión 0,30 significa 70 % de respuestas falsas». | [Interpretación de los valores](bloques-24-28.md#cómo-se-interpretan-estos-valores). |
| «Si entreno el modelo con la ley, la sabrá siempre». | [Información frente a comportamiento](bloques-29-30.md#la-pregunta-que-ordena-todo). |
| «El método dio RAG, entonces al clasificador le faltan documentos». | [Cómo leer el resultado](bloques-29-30.md#8-cómo-interpretar-nuestro-resultado). |
| «El filtro no encontró nada, entonces el documento es seguro». | [Lista negra](bloques-31-32.md#una-lista-negra-siempre-es-incompleta). |
| «Registré el prompt nuevo, entonces ya responde con él». | [Registrar no es activar](bloques-31-32.md#6-bloque-32-versionar-prompts). |
| «Pasaron las pruebas, entonces Gemini siempre elige bien». | [Alcance de las evidencias](bloques-21-23.md#costos-y-evidencia-qué-conclusiones-son-válidas). |

## 6. Qué significa haberlo comprendido

No necesitas recitar las firmas de las clases. Deberías poder tomar una consulta
y explicar:

1. Qué programa la recibe y si su recorrido es fijo o propuesto por el modelo.
2. Qué información entra al modelo y qué parte cuenta como fuente.
3. Qué comprobaciones hace Python sin depender de una instrucción de prompt.
4. Cuántas llamadas esperas en ese caso y qué podría aumentar su consumo.
5. Qué sucede si no hay evidencia, falla una llamada o no se autoriza una acción.
6. Qué evidencia respalda tu explicación y qué cosas no quedaron demostradas.

Las entregas indican lo completado; estas guías sirven para entenderlo.
Estudiar una limitación no reabre automáticamente una actividad ni exige otra
prueba pagada.
