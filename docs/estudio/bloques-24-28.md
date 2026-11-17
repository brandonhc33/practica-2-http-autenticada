# Guía de estudio: bloques 24 a 28

## Objetivo y fuentes

Construir y entender un RAG de Ley REP: **indexar una vez → recuperar por
significado → generar con fuentes → evaluar → medir**. No estamos entrenando a
Gemini ni convirtiendo el agente anterior en un modelo que «ya sabe la ley».

Esta guía explica las lecciones y actividades de la Unidad 2.5 revisadas en la
copia local de Skillnest. El [PRD 04](../planes/prd-04-rag-ley-rep.md#2-fuente-y-requisitos-del-curso)
conserva sus enlaces originales y las adaptaciones del proyecto. No es una
transcripción de los videos ni una rúbrica docente adicional.
La [entrega](../entregas/bloques-24-28.md) separa implementación, pruebas y
[mediciones reales ya conservadas](../evidencias/bloques-24-28/README.md).

## Índice

1. [Qué cambia respecto de los bloques anteriores](#1-qué-cambia-respecto-de-los-bloques-anteriores)
2. [Bloque 24: documentos, chunks y embeddings](#2-bloque-24-documentos-chunks-y-embeddings)
3. [Bloque 25: persistencia y diagnóstico](#3-bloque-25-persistencia-y-diagnóstico)
4. [Bloque 26: recuperación, contexto y citas](#4-bloque-26-recuperación-contexto-y-citas)
5. [Bloque 27: precisión y recall](#5-bloque-27-precisión-y-recall)
6. [Bloque 28: latencia, tokens y costo](#6-bloque-28-latencia-tokens-y-costo)
7. [Laboratorio progresivo](#7-laboratorio-progresivo)
8. [Preguntas de repaso y respuestas](#8-preguntas-de-repaso-y-respuestas)

## 1. Qué cambia respecto de los bloques anteriores

| Flujo | Cómo consigue evidencia | Quién elige los pasos |
| --- | --- | --- |
| Prompt documental anterior | Envía todos los artículos o un artículo explícito. | El programa. |
| Agente de B21–23 | Busca palabras o lee un artículo mediante herramientas. | El modelo propone herramientas; el ejecutor limita y ejecuta. |
| RAG de B24–28 | Busca vectores cercanos a la pregunta en un índice persistente. | El programa ejecuta un flujo fijo de recuperación y generación. |

**RAG no es sinónimo de agente.** Puede ser una secuencia completamente fija.
La memoria conversa; el índice aporta documentos. Una pregunta anterior del
usuario no se convierte por eso en fuente normativa.

La API y el agente supervisado siguen disponibles. El nuevo código está separado
en `src/rag/` y sus entradas están en `scripts/`. Esta etapa usa únicamente la
copia de 2016 de Ley 20.920, no todo el corpus del futuro proyecto final.

## 2. Bloque 24: documentos, chunks y embeddings

### ¿Qué pedía la actividad?

Un corpus propio de al menos cinco documentos relacionados, dividido antes de
calcular **embeddings reales**, persistido en Chroma y recargable sin reindexar.
No basta con guardar vectores inventados ni con mantenerlos solo en memoria.

### ¿Qué es un documento y qué es un chunk?

El documento es la unidad de origen. Aquí cada artículo o transitorio es un
documento: tenemos 50, cada uno con referencia, páginas, versión y procedencia.
Un **chunk** es la unidad que recuperaremos: un artículo largo produce varios.

Ejemplo: el artículo 9 de esta copia queda en tres chunks con IDs como
`ley20920-articulo-9-c000`. El número `c000` es la posición dentro de ese artículo,
no una cita `[1]` ni un nuevo artículo de la ley.

Mantener el límite del documento evita un chunk que mezcle el final del artículo
8 con el comienzo del 9. La metadata debe viajar con cada fragmento desde el
principio; no se puede reconstruir su origen solo mirando el vector.

### ¿Por qué no usar siempre 200 caracteres como el ejemplo?

El tamaño del ejemplo didáctico no es una regla universal. Una obligación legal
puede ser más larga que una política de tienda.

Se compararon dos estrategias y dos tamaños sobre la misma copia:

| Estrategia | Tamaño / solapamiento | Chunks |
| --- | --- | --- |
| Fijo | 400 / 50 | 164 |
| Fijo | 800 / 100 | 95 |
| Recursivo | 400 / 50 | 187 |
| Recursivo | 800 / 100 | 99 |

Los cortes fijos parten palabras en el artículo 9. Con recursivo 400, una misma
obligación queda dividida en dos. **Recursivo 800 / 100 es el punto de partida
elegido**, no un óptimo demostrado por las métricas.
La [comparación local](../evidencias/bloques-24-28/comparacion-chunking.md) conserva
la justificación y los límites, incluido un fragmento final corto.

El tamaño se mide en **caracteres**, no tokens. El splitter recursivo intenta
separar por párrafos, saltos y palabras antes de cortar por caracteres. No
comprende jurídicamente el texto: una lista puede quedar partida.

### ¿Para qué sirve el overlap?

Repite parte del texto entre fragmentos próximos para no perder el contexto en
el borde. Un overlap de 100 es un máximo de configuración, no una promesa de
exactamente 100 caracteres repetidos en cada pareja de chunks recursivos.

Por eso sumar las longitudes de todos los chunks no debe dar necesariamente lo
mismo que sumar los documentos. En esta configuración:

- Corpus: 52.727 caracteres.
- Chunks: 53.731 caracteres, contando repeticiones.
- Texto no blanco perdido: **0**.
- Espacios/saltos de borde no indexados: **66**, por limpieza del splitter.
- Textos de chunk duplicados completos: **0**.

La integridad se verifica con offsets: cada chunk coincide con una porción exacta
del artículo y todo carácter no blanco del original aparece en algún chunk.
No se promete conservación de espacios de borde ni identidad de los totales.

### ¿Qué representa un embedding?

Un vector de números calculado por un modelo para representar el texto. Textos
semánticamente relacionados tienden a ocupar zonas cercanas. No es una lista de
palabras, una respuesta ni una prueba de aplicabilidad legal.

Usamos `GoogleGenerativeAIEmbeddings` con `models/gemini-embedding-001` y 3072
dimensiones, como el modelo textual de la actividad. El conector usa
`RETRIEVAL_DOCUMENT` al indexar y `RETRIEVAL_QUERY` al consultar. Son dos tareas
compatibles dentro del mismo espacio; no dos modelos intercambiables.

**Misma dimensión no significa mismo espacio.** Dos modelos de 3072 dimensiones
pueden producir vectores incompatibles. Cambiar de modelo obliga a reindexar.
Se mantienen las dimensiones completas; no es necesaria la normalización manual
que la documentación de ese modelo pide al reducirlas.

### ¿Qué guarda Chroma?

IDs, textos, metadata y vectores; el índice permite buscar vecinos de un vector.
Se guarda localmente en `vectorstore/`, ignorado por Git. El repositorio conserva
lo necesario para reconstruirlo, no los binarios generados.

## 3. Bloque 25: persistencia y diagnóstico

### ¿Cómo sabemos que persistió?

Que el proceso de indexación termine no basta. Se ejecuta otro proceso que abre
la misma carpeta, verifica el manifiesto y lee sus documentos, **sin llamar al
modelo de embeddings**. Hay una prueba automática de ese recorrido con Chroma
real y datos de prueba.

La prueba con datos falsos demuestra la mecánica de persistencia. La recarga del
índice real de la ley se confirma después de la indexación autorizada.

### ¿Por qué un manifiesto además de la carpeta?

Una carpeta existente puede estar vacía, incompleta o contener otro corpus.
`manifiesto.json` identifica corpus, chunks, modelo, dimensiones, estrategia,
tamaño, overlap, colección y distancia. Su huella fija la configuración y el
contenido que deben coincidir.

El lector no crea silenciosamente una colección vacía. Compara conteo, IDs,
textos y metadata con el corpus local. El comando de indexación:

- Reutiliza un índice completo compatible sin recalcular embeddings.
- Rechaza uno incompatible o interrumpido.
- Pide una carpeta nueva en lugar de borrar archivos automáticamente.

No hay actualización incremental en esta entrega: es un índice reconstruible e
inmutable. Los IDs explícitos dejan preparada la trazabilidad, pero no significan
que ya implementamos una política de actualización de producción.

### ¿Y la réplica de tienda?

El B25 propone cinco políticas ficticias, con tamaño 150 y overlap 20. Producen
cinco chunks y 490 caracteres. Se puede usar `--corpus ejemplo`; su índice vive
en `output/rag/vectorstore_ejemplo/`, separado del de la ley.

El material dice que esta réplica es un ejercicio, **no una entrega adicional**.
Su chunking y persistencia se prueban gratuitamente con embeddings deterministas;
no se declara ejecutada con Gemini si no se hizo esa corrida.

### Diagnóstico ordenado

| Síntoma | Revisar primero |
| --- | --- |
| No existe manifiesto | Ruta y ejecución de indexación; una interrupción no equivale a éxito. |
| Conteo o contenido distinto | Índice incompleto o modificado; no culpar al ranking todavía. |
| Modelo o dimensión incompatible | Configuración con la que se construyó el índice. |
| Todo se parece a un mismo tema incorrecto | Corpus/colección equivocados o embeddings incompatibles. |
| Clave ausente o cuota agotada | Entorno y respuesta del proveedor; no reindexar repetidamente. |
| Error de SQLite | Versión de SQLite; no instalar un parche si tu entorno ya funciona. |

## 4. Bloque 26: recuperación, contexto y citas

### ¿Qué sucede con una pregunta?

```text
Pregunta
→ calcular su embedding una vez
→ buscar k vecinos en Chroma con ese vector
→ numerar los fragmentos recuperados
→ construir el prompt con pregunta, fuentes y límites
→ generar una respuesta
→ conservar respuesta y mapa de fuentes para revisarla
```

Buscar **por vector** es importante para la medición: calcular `embed_query` y
después llamar a `similarity_search(pregunta)` calcularía otra vez el embedding.
Aquí la búsqueda recibe el vector ya obtenido.

### ¿Qué es k y qué significa la distancia?

`k=3` pide hasta tres chunks, no tres artículos únicos. Pueden proceder del mismo
artículo. Si el índice tiene menos, se registran las fuentes realmente devueltas.

Se usa distancia coseno: **menor significa más cercano**. No se presenta como un
porcentaje de confianza. El método del adaptador contiene la expresión
`relevance_scores`, pero su documentación aclara que devuelve distancias; el
registro las nombra `distancia_coseno`.

No se aplica un umbral inventado. Una pregunta sobre impuestos también obtiene
vecinos de una ley de residuos: top-k siempre busca los más cercanos disponibles,
no decide si el corpus tiene respuesta.

### ¿Cómo se construye una cita?

El contexto es JSON con un número `cita` por fragmento. El modelo debe usar `[1]`,
`[2]`, etc. en sus afirmaciones. El mapa que conserva el programa permite seguir:

```text
[1]
→ id_chunk
→ id_documento y referencia
→ archivo local, páginas, versión y URL oficial
→ texto exacto que recibió el modelo
```

`[1]` significa primer fragmento del contexto de **esa consulta**, no artículo 1.
Puede apuntar al artículo 34 en una pregunta y al 12 en otra.

La instrucción de sistema exige usar solo el contexto, citar y reconocer
información insuficiente. Pregunta y documentos son datos: no deben cambiar esas
reglas. Esto reduce riesgos de inyección, pero no demuestra inmunidad.

### ¿Qué valida el programa y qué debe revisar una persona?

Comprueba si los números citados existen en el mapa y avisa cuando no hay citas.
No sustituye silenciosamente una cita inventada por otra.

**No comprueba que la frase esté realmente respaldada.** Una respuesta puede
citar `[1]` correctamente y atribuirle algo que ese chunk no dice. Para la
actividad se revisa una cita real, comparando la afirmación con su texto y el
artículo original. Una abstención correcta puede no llevar citas; el aviso
`sin_citas` no la convierte automáticamente en un fallo.

## 5. Bloque 27: precisión y recall

### ¿Por qué evaluar antes de opinar sobre la respuesta?

Si no recuperamos la evidencia correcta, Gemini no la puede citar desde ese
contexto. Pero recuperarla tampoco garantiza que redacte bien. Son dos problemas
distintos: **calidad del retrieval** y **fidelidad de la generación**.

Se versionan diez casos en
[`recuperacion_rag.json`](../../datos/evaluacion/recuperacion_rag.json). Los IDs
relevantes se propusieron leyendo el corpus antes de cualquier recuperación. El
archivo declara que el etiquetado inicial es del asistente y requiere revisión
del alumno: no se finge una validación docente o jurídica.

Se etiqueta por **chunk con evidencia directa**, no por artículo entero. El caso
del plazo municipal espera `ley20920-articulo-23-c001`, porque allí están los cinco
años; no basta con recuperar el primer chunk de ese artículo.

### Fórmulas y ejemplo

Sean $R$ los IDs recuperados únicos y $G$ los relevantes etiquetados:

$$
\mathrm{Precisión}=\frac{|R\cap G|}{|R|},\qquad
\mathrm{Recall}=\frac{|R\cap G|}{|G|}
$$

Si `R = [a, b, c]` y `G = {b, d}`, hay un acierto:
precisión $1/3$ y recall $1/2$. Recuperar otra vez `b` no debe contar como otro
acierto. Por eso las funciones no dejan que duplicados inflen el resultado.

Sin recuperados, precisión es 0. Sin relevantes, recall no está definido:
guardamos `null` y el TXT muestra `n/a`; ese caso se excluye del promedio de
recall. Si todos son indefinidos, el promedio también es `null`.

### ¿Qué comparamos?

El evaluador recupera una vez hasta `max(k)` por pregunta y evalúa los prefijos
para `k=3` y `k=5`. No genera texto y no hace otro embedding por cada k.
`--repeticiones 2` vuelve a ejecutar las preguntas y registra si ambos resultados
fueron idénticos.

Sobre un mismo ranking, agregar resultados no reduce recall. **La precisión no
tiene que bajar siempre**: puede subir si los nuevos resultados son relevantes.
Las afirmaciones generales del material son una intuición del trade-off, no una
propiedad matemática de cada muestra.

La evaluación guarda fecha, configuración, huella, preguntas, IDs y promedios,
en TXT y JSON nuevos. Si cambia el chunking, el etiquetado anterior se rechaza
en lugar de comparar IDs incompatibles.

Diez casos son una referencia de estudio, no prueba de cobertura del dominio.
Si elegimos k usando esos mismos casos, después necesitaremos preguntas
independientes para evaluar esa elección sin sobreajuste.

### ¿Qué ocurrió al medir nuestro índice?

Las dos repeticiones reales fueron idénticas: precisión promedio 0,30 con k=3
y 0,18 con k=5; recall 1,00 en ambos. Nueve preguntas tienen un único relevante
etiquetado, recuperado en ambos k; la décima no tiene respuesta en el corpus y
su recall es indefinido. No significa que el sistema sea «100 % correcto»:
medimos recuperación contra un pequeño etiquetado inicial, no la respuesta legal
ni todos los fragmentos posiblemente útiles. Se conserva también el intento
previo interrumpido como antecedente, sin inventarle métricas; la evaluación sí
se completó. Ver [resultados del B27](../evidencias/bloques-24-28/README.md#b27-evaluación-completada-y-resultados).

## 6. Bloque 28: latencia, tokens y costo

### ¿Qué pide la actividad core?

Instrumentar el RAG real y guardar `registros_latencia_costo.jsonl`: al menos
tres preguntas del conjunto del B27, además de comparar una misma pregunta con
`k=3` y `k=6`. Nuestro comando de actividad hace cuatro corridas, no cinco:
reutiliza como referencia la primera de las tres preguntas con k=3.

### ¿Qué medimos?

| Campo | Qué incluye |
| --- | --- |
| `tiempos_ms.embed_query` | Función que obtiene el vector de la pregunta; incluye red y posibles intentos internos del SDK. |
| `tiempos_ms.busqueda_vectorial` | Solo búsqueda local con el vector ya calculado. |
| `tiempos_ms.generacion` | Invocación de Gemini con todo el prompt. |
| `tiempo_etapas_ms` | Suma de los tiempos de las etapas ejecutadas. |
| `tiempo_total_ms` | Tiempo de pared de esa consulta con índice/clientes cargados; incluye armado de contexto y prompt. |

Se usa `perf_counter`, un reloj para duraciones. No incluye instalación, arranque,
carga inicial del índice ni indexación. Esos costos iniciales se distinguen del
rendimiento de una consulta con el sistema preparado.

El total de pared puede ser algo mayor que la suma de etapas. No lo falsificamos
para que coincida. Una etapa no ejecutada tras un fallo queda `null`, no 0.

La generación suele dominar, pero hay que leer lo medido: cachés, red, respuestas
cortas y estado del proveedor pueden cambiar el orden. Si no domina en una
corrida, se explica; no se corrigen los tiempos para parecerse al ejemplo.

### ¿De dónde salen los tokens y el costo?

`tokens` conserva `usage_metadata` del mensaje de generación. Incluye entrada
del **prompt completo**, no solo la pregunta, y salida según lo informado por el
conector. La calculadora existente aplica las tarifas de pago versionadas,
incluyendo caché cuando se informa:

$$
C_\text{generación} =
\frac{T_\text{entrada normal}P_\text{entrada}
+ T_\text{caché}P_\text{caché}
+ T_\text{salida}P_\text{salida}}{10^6}
$$

El conector de embeddings instalado devuelve vectores, **no tokens de uso**.
No inventamos su consumo. Su registro separa:

- Tokens y costo real de embeddings: `null`.
- Aproximación: caracteres / 4, redondeado hacia arriba, explícitamente rotulado.
- Tarifa de referencia de `gemini-embedding-001`: USD 0,15 por millón de tokens,
  verificada en la página oficial el 16-11-2026.
- `costo_conocido_usd`: subtotal calculable de generación.
- `costo_total_usd`: `null`, porque no conocemos todas las partes.

La aproximación tampoco prueba la factura del proveedor ni el costo de intentos
fallidos. La indexación de los documentos se paga una vez por construcción del
índice y se presupuesta aparte; este comando no la repite.

Subir k suele aumentar tokens de entrada; la comparación real debe comprobarlo.
El costo total de generación no aumenta en la misma proporción si cambia la
longitud de la respuesta, y aún puede haber caché.

En nuestra comparación real, la misma pregunta pasó de **1297 a 2540 tokens de
entrada** al subir de k=3 a k=6: +1243 (+95,84 %). Las cuatro generaciones
sumaron **USD 0,0032103 estimados**, sin incluir embeddings. La generación fue
la etapa más lenta en las cuatro, pero sus tiempos variaron ampliamente: no
podemos atribuir esa variación solo a k. Los [registros y conclusiones](../evidencias/bloques-24-28/README.md#actividad-28-tiempos-tokens-y-costo-observado)
permiten comprobar los números y contrastarlos con el texto.

### ¿Qué ocurre si falla una corrida?

Se guarda su registro parcial, con etapa y tipo de error, sin el cuerpo del
error del SDK. El comando termina con código no exitoso y no sigue con más
preguntas. Los registros anteriores ya quedaron escritos y vaciados al archivo.

No hay fallback ni repetición de todo el flujo. El cliente de generación conserva
un intento y timeout de 30 s del proyecto. El SDK de embeddings conserva sus
reintentos internos predeterminados y timeout por intento de 30 s; no declaramos
una única petición HTTP ni un costo conocido para esos intentos.

## 7. Laboratorio progresivo

Todos los comandos están en la [entrega](../entregas/bloques-24-28.md#recorrido-de-ejecución).
Hazlos en este orden:

1. **Sin cuota:** comparar cortes, leer el artículo 9 y revisar las etiquetas.
2. **Sin cuota:** ejecutar las pruebas. Identificar qué se prueba con Chroma real y
   qué se sustituye por modelos falsos.
3. **Con cuota y autorización:** indexar la ley una vez. Abrir desde otro proceso
   y comprobar que verifica 99 chunks sin calcular embeddings.
4. **Con cuota:** evaluar diez preguntas, dos repeticiones y dos k; guardar
   resultados y explicar un fallo si lo hay.
5. **Con cuota:** ejecutar las cuatro corridas de la actividad 28. Revisar que
   cambie el contexto entre preguntas y comparar tokens de la primera y la cuarta.
6. **Con cuota:** preguntar por el impuesto a la renta de 2027 y revisar abstención.
   Si inventa información, conservar el fallo, no marcar ese criterio aprobado.
7. **Revisión:** seguir una cita real hasta el chunk y el artículo; redactar la
   conclusión de costo y latencia con esos resultados, no con cifras del curso.

Los comandos reales exigen `--confirmar-consumo`. No hay modo falso escondido
cuando falta la clave. En un worktree se puede cargar el `.env` original mediante
`uv run --env-file /ruta/al/.env ...`, sin copiar la clave al repositorio.

## 8. Preguntas de repaso y respuestas

Intenta responder antes de leer la columna de la derecha:

| Pregunta | Respuesta que debes poder explicar |
| --- | --- |
| ¿Tener un vector store significa tener un RAG completo? | No. Falta recuperar, construir contexto, generar y evaluar. |
| ¿Qué se paga otra vez por cada pregunta? | Embedding de consulta y generación; no los embeddings de documentos si reutilizamos el índice. |
| ¿Por qué un índice con 0 resultados no demuestra que «la ley no dice nada»? | Puede ser ruta equivocada o índice incompleto. Primero verificar integridad. |
| ¿Puede cambiar el modelo sin cambiar las dimensiones? | Sí, pero eso no hace compatibles sus vectores. Hay que reindexar. |
| ¿Un chunk más largo siempre es mejor? | No. Puede conservar una obligación completa o agregar mucho ruido. Se compara. |
| ¿`[1]` corresponde al artículo 1? | No. Es el primer chunk del contexto actual y se resuelve mediante el mapa. |
| ¿Una cita existente prueba que una afirmación es cierta? | No. Hay que comprobar que el texto citado respalde esa afirmación. |
| ¿Con k=6 siempre baja precisión respecto de k=3? | No. Depende de si los nuevos chunks son relevantes. Recall no baja sobre el mismo ranking. |
| ¿Una pregunta sin relevantes tiene recall 0? | No está definido; se registra `null` y se excluye del promedio. |
| ¿Por qué no usar los resultados para «arreglar» los IDs relevantes? | Contaminaría el criterio independiente. Un error genuino de etiquetado se corrige con justificación y nueva versión, no para mejorar el número. |
| ¿La suite verde demuestra calidad semántica? | No. Demuestra contratos y mecánica con vectores/modelos de prueba. Hace falta la evaluación real. |
| ¿`null` en el costo de embeddings significa gratis? | No. Significa desconocido. La tarifa gratuita de la cuenta tampoco se puede inferir desde este registro. |
| ¿Cuatro corridas bastan para afirmar un p95 de producción? | No. Cubren la actividad mínima, no una muestra estadística de operación. |
| ¿El repositorio está «entregado» por tener los scripts? | No. Faltan corridas reales revisadas y la publicación/envío que corresponda. |
