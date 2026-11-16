# Límites de autonomía del agente de Ley REP — Bloque 23

## Qué puede hacer sin aprobación

El agente puede buscar por palabras en la copia local de la Ley 20.920, leer un
artículo completo y responder una consulta. No modifica la ley ni utiliza una
búsqueda web. Estas son las herramientas `buscar_en_ley` y `obtener_articulo` de
[herramientas.py](../src/orquestacion/herramientas.py).

El modelo decide qué herramienta usar. `AgentExecutor` limita cada consulta a
cuatro iteraciones; no hay fallback a otro modelo ni reintento del flujo completo.
Una iteración puede incluir varias herramientas si el modelo las solicita juntas:
el límite controla llamadas al modelo, no el número total de acciones.

## Qué requiere una persona

`entregar_informe(titulo, contenido)` representa una acción de riesgo alto: entregar
un informe a un tercero. En esta actividad **la entrega es simulada**: solo escribe
un archivo Markdown en `output/agente/informes_entregados/`. No envía correos, no
contacta clientes y no publica documentos.

Antes de escribir, la herramienta:

1. Muestra en stderr la sesión, el título y el contenido completo.
2. Espera hasta 300 segundos en una terminal interactiva.
3. Acepta únicamente `s`, sin distinguir mayúsculas ni espacios alrededor.
4. Registra la decisión en `output/agente/aprobaciones.jsonl`.
5. Solo si fue aprobada y el registro se pudo escribir, guarda el informe.

`n`, `si`, una línea vacía, tiempo agotado, fin de entrada, cancelación o error de
terminal no aprueban. Una entrada redirigida tampoco aprueba, aunque contenga `s`.
Las pruebas automáticas simulan las decisiones; no constituyen aprobación humana
para una ejecución real. En Windows la espera con `select` puede fallar y rechaza
la acción de manera segura.

La espera muestra ahora en stderr el motivo de salida y su duración. Una línea
vacía recibida rechaza de inmediato; no se ignora ni se convierte en aprobación.
Este diagnóstico permite distinguirla de `n`, EOF o un error, pero el motivo no
se agrega retrospectivamente a las decisiones booleanas ya registradas.

El nombre de archivo se genera en el programa: el modelo no elige rutas y el título
no se interpreta como una ruta. Cada archivo se abre en modo exclusivo, sin
sobrescribir una entrega anterior. No hay garantía de idempotencia: otra llamada
aprobada crea otra entrega, por eso cada llamada vuelve a pedir aprobación.

## Qué queda registrado

| Archivo local, ignorado por Git | Contenido |
| --- | --- |
| `output/agente/aprobaciones.jsonl` | Identificador, fecha UTC, sesión, cuenta local del supervisor, título, contenido y decisión. |
| `output/agente/trazas_agente.jsonl` | Fecha UTC, sesión, consulta, tamaño previo del historial, herramientas, argumentos, observaciones completas, respuesta y error si lo hubo. |
| `output/agente/informes_entregados/<id_aprobacion>.md` | Informe aprobado; el identificador permite relacionarlo con su decisión. |

El identificador de sesión se toma del contexto de ejecución de LangChain, no de
un argumento generado por el modelo. La cuenta local es una referencia operativa,
**no una identidad autenticada ni una firma digital**.

Una consulta vacía no llama al modelo ni genera traza. Un turno fallido genera
traza con el tipo y mensaje del error, pero no se agrega al historial. Si falla la
escritura de la traza, se avisa por el registro de errores y no se repite la consulta.

Una decisión `aprobado: true` **no demuestra por sí sola una entrega exitosa**: la
escritura del informe puede fallar después. Hay que contrastarla con el archivo y
con la observación de la herramienta. Si falla el modelo después de una entrega,
`AgentExecutor` no devuelve los pasos ya ejecutados: la traza queda sin esos pasos,
pero la decisión y el informe conservan su registro independiente. No se debe
repetir el pedido automáticamente.

## Cómo revisar repeticiones

```bash
uv run python -m src.orquestacion.supervision
```

El comando devuelve las sesiones donde una herramienta se usó dos veces seguidas.
Recorre las llamadas a herramientas en orden por sesión, incluso entre turnos;
intercalar otra sesión o un turno sin herramientas no rompe esa secuencia.
Devuelve cada sesión una sola vez y detalla las coincidencias en stderr. Si no
existe el archivo, avisa y devuelve `[]`. Un JSONL dañado produce un error: no se
omite evidencia silenciosamente.

Es un aviso para revisar, no una prueba de un bucle: leer dos artículos seguidos
puede ser correcto. No bloquea acciones, no revoca aprobaciones ni repite consultas.

## Límites que siguen vigentes

- Las instrucciones piden leer la ley antes de entregar y no insistir después de
  un rechazo, pero son reglas de prompt, no una barrera de seguridad verificable.
  Cada ejecución de la herramienta sí exige aprobación en código.
- La aprobación no valida hechos ni citas. El supervisor debe leer el informe y
  rechazar contenido incorrecto; esto no es asesoría legal.
- La búsqueda es léxica, sin embeddings. Puede omitir artículos pertinentes.
- La memoria guarda solo consulta y respuesta final; no guarda las observaciones.
  Se pierde al terminar el proceso, no tiene límite de tamaño y aumenta el costo
  de los siguientes turnos. El historial no es fuente de evidencia legal.
- Las clases de memoria emiten avisos de deprecación. Se conservan por el alcance
  del curso; habrá que migrarlas antes de actualizar a LangChain 2.
- Los registros contienen consultas e informes completos en texto plano. No
  introducir datos personales ni secretos en el ensayo; revisar cualquier archivo
  antes de incorporarlo a la entrega. No hay cifrado, control de acceso adicional
  ni protección contra modificaciones manuales del registro.
- El flujo está pensado para una terminal local y ejecución secuencial, no para
  varios procesos escribiendo al mismo tiempo.

## Estado de la comprobación

La aprobación, el rechazo, el tiempo agotado, el fin de entrada, el aislamiento de
sesiones, las trazas y las repeticiones tienen pruebas sin red. Las corridas humanas
del Bloque 23 ya comprobaron una entrega aprobada y una no aprobada, con su archivo
presente y ausente respectivamente. Está pendiente el rechazo explícito con `n`
dentro del agente: el registro booleano no distingue una `n` de un timeout o EOF.
La prueba local sin Gemini sí leyó `s` y luego `n`, pero no explica la dificultad
reportada durante la corrida ni reemplaza ese control. Ver
[revisión de evidencias](evidencias/bloques-21-23/revision-bloque-23.md).
La consulta adicional también terminó sin `n` en unos siete segundos; se conserva
como no aprobada y no como rechazo explícito. El
[diagnóstico con modelo falso](evidencias/bloques-21-23/diagnostico-aprobacion.md)
permite revisar la entrada sin seguir gastando cuota.
El estado y los pasos de cierre están en
[la entrega de los bloques 21 a 23](entrega-bloques-21-23.md).

Para contrastar el control con el código:

```bash
grep -n "esperar_aprobacion(" src/orquestacion/herramientas.py
```

Las trazas humanas ya se contrastaron con `wc -l` y `grep -c`, como establece el
PRD 03. Los conteos y el resultado del detector están en la revisión de evidencias.
