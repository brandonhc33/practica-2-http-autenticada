# Entrega de los bloques 21 a 23 — agente de Ley REP

**Estado: implementación y validación funcional de los bloques 21 a 23
completadas, incluido el rechazo explícito con `n` usando Gemini.** La decisión,
la traza y la ausencia del informe de `rechazo-final-23` se contrastaron con la
salida del alumno. Quedan la publicación de la rama y la instalación desde un
clon de GitHub. Se conservan los intentos anteriores con sus diferencias, sin
atribuirles retroactivamente una `n` ni una causa al rechazo inmediato.

## Entregables

| Bloque | Implementación y revisión |
| --- | --- |
| 21 — agente con herramientas | [Herramientas](../src/orquestacion/herramientas.py), [agente](../src/orquestacion/agente_con_herramientas.py), límite de cuatro iteraciones y `intermediate_steps`. |
| 22 — herramienta estructurada y memoria | `ArgumentosArticulo`, validación como observación y memoria separada por `session_id`, en los mismos módulos. |
| 23 — supervisión y límites | `entregar_informe`, [supervisión y registros](../src/orquestacion/supervision.py), [límites de autonomía](limites-autonomia-agente.md), aprobación y [rechazo explícito comprobado](evidencias/bloques-21-23/rechazo-explicito-gemini.md). |

La API y el flujo de los bloques 18 a 20 no se reemplazan. El agente es una entrada
adicional por terminal, con `langchain-classic` y el conector nativo de Gemini.
La [guía de estudio](preguntas-bloques-21-23.md) explica los conceptos y cómo cada
implementación responde a la actividad.

## Uso

Desde la raíz del repositorio:

```bash
uv sync --locked
uv run python -m src.orquestacion.agente_con_herramientas --help
```

El comando siguiente **sí consulta Gemini y consume cuota**. Requiere
`GEMINI_API_KEY` configurada localmente en el entorno o en `.env`; nunca compartir
la clave:

```bash
uv run python -m src.orquestacion.agente_con_herramientas --sesion cliente-1 \
  "¿Qué establece el artículo primero transitorio de la Ley REP?" \
  "¿Y qué dice el artículo transitorio siguiente?"
```

Las respuestas salen por stdout. Las herramientas, los errores, el consumo y los
avisos de aprobación salen por stderr. Las consultas de un comando comparten
sesión, pero otro proceso empieza sin historial aunque use el mismo identificador.

## Evidencias reales conservadas

| Bloque | Casos coincidentes | Llamadas | Tokens | USD |
| --- | --- | --- | --- | --- |
| [21](evidencias/bloques-21-23/ensayo-bloque-21.json) | 3 de 3 | 5 | 3.405 | 0,0019345 |
| [22](evidencias/bloques-21-23/ensayo-bloque-22.json) | 3 de 3 | 5 | 3.696 | 0,0019624 |
| [23, intento 1](evidencias/bloques-21-23/ensayo-bloque-23.json) | 0 de 2 | 5 intentos, uno sin uso informado | 4.320 registrados | 0,0023102 conocidos |
| [23, intento 2](evidencias/bloques-21-23/ensayo-bloque-23-intento-02.json) | 2 de 2 automáticos; no prueba rechazo explícito | 6 | 6.656 | 0,0034708 |
| [23, control de rechazo](evidencias/bloques-21-23/diagnostico-aprobacion.md) | No aprobado, sin `n` comprobada | 3 | 3.457 | 0,0020491 |
| [23, rechazo final](evidencias/bloques-21-23/rechazo-explicito-gemini.md) | `n` explícita, registro negativo y archivo ausente | 3 | 3.402 | 0,0019512 |
| Total registrado | Validación funcional completada; publicación por comprobar | 27 intentos | 24.936 registrados | 0,0136782 conocidos |

Los intentos del Bloque 23 fueron ejecutados por el alumno. En el primero hubo un
503 de Gemini y una aprobación donde se esperaba rechazo. En el segundo sí se
guardó el informe del artículo 12 y no se guardó el del artículo 34. El registro
solo distingue `true` de `false`; los tiempos son compatibles con un timeout en
el segundo aviso, y el alumno no reportó haber introducido `n` en ese caso.

Se conservan ambos resultados sin corregirlos, junto con las
[trazas y decisiones revisadas](evidencias/bloques-21-23/revision-bloque-23.md).
El intento fallido sin metadatos no se considera de costo cero; el total de USD es
solo el costo conocido. La [prueba local de entrada](evidencias/bloques-21-23/prueba-entrada-terminal.md)
sí leyó `s` y `n`, sin Gemini, pero no sustituye el rechazo de un informe del agente.

El control final `rechazo-final-23` sí leyó una `n` con Gemini, tras 21,6 segundos
de espera. Su decisión fue negativa y no existe el informe correspondiente. La
[evidencia final](evidencias/bloques-21-23/rechazo-explicito-gemini.md) completa ese
control sin modificar los resultados de los intentos previos.

En el Bloque 21 se comprobaron búsqueda por tema, lectura de un artículo y una
respuesta sin herramienta. El [consumo del conector](evidencias/bloques-21-23/consumo-gemini-bloque-21.json)
coincide con el registro del ensayo.

En el Bloque 22, `cliente-1` interpretó «el siguiente» como el segundo transitorio;
`cliente-2` empezó con cero mensajes y no recibió el primer historial. Los turnos
usaron 1.370, 1.771 y 555 tokens respectivamente. El segundo turno reenvía historial
y además lee un artículo más largo, así que el aumento no mide solo la memoria.

La [observación del conector del Bloque 22](evidencias/bloques-21-23/consumo-gemini-bloque-22.json)
registra dos llamadas a herramientas con firma y dos reenvíos de las firmas
originales, sin comodín. Que Gemini aceptara los pedidos del Bloque 21 no probaba
por sí solo ese reenvío. Gemini no informó tokens de razonamiento en esas diez
llamadas; no se infiere por ello que no haya razonado.

Las evidencias de 21 y 22 son históricas: se generaron antes de incorporar la tercera
herramienta y sus instrucciones. No se han repetido con el prompt final ni se
espera obtener exactamente el mismo consumo al repetirlas.

Los observadores usados en las corridas anteriores estaban en `/tmp` y no se
incorporaron al repositorio. Se conservan sus resultados, pero no se garantiza la
reproducción de aquella instrumentación. Las pruebas con el SDK simulado verifican
consumo por streaming y reenvío de firmas sin depender de esos archivos temporales.

## Comprobaciones sin red

```bash
uv run python -m pytest tests -v
uv run ruff check .
uv run basedpyright
git diff --check
```

`tests/conftest.py` bloquea la red para toda la suite. Los informes y registros de
las pruebas se escriben en directorios temporales, no en `output/agente/`.
Los resultados de esta revisión se conservan en
[verificación local](evidencias/bloques-21-23/verificacion-local.md).

| Criterios del PRD 03 | Cobertura |
| --- | --- |
| CA-01 a CA-03 | Búsqueda y lectura local, recortes, inexistentes y copia ausente. |
| CA-04 a CA-08 | Herramienta, ninguna, límite, salida en bloques, errores y entrada vacía. |
| CA-09 a CA-12 | Esquemas, argumentos inválidos, transitorios, memoria, aislamiento y orden de mensajes. |
| CA-13 y CA-14 | Aprobación, rechazo, timeout, EOF, cancelación, errores y entrada no interactiva. |
| CA-15 y CA-16 | JSONL completo, error sin pasos, repeticiones dentro de un turno y entre turnos por sesión. |
| CA-17 y CA-18 | Ensayos con modelo falso para los tres bloques y suite completa sin red. |
| CA-19 | Ensayos reales de los tres bloques conservados; aprobación y `n` explícita con Gemini comprobadas, con archivo presente y ausente respectivamente. |
| CA-20 | Control contrastado con las trazas reales: lecturas y propuestas de entrega presentes. Ver [revisión](evidencias/bloques-21-23/revision-bloque-23.md). |

También se prueba el caso en que el modelo falla después de una entrega aprobada:
no se repite el flujo y sobreviven el informe y la aprobación, aunque la traza
pierda los pasos. Un error al escribir la aprobación impide entregar; un error al
escribir el informe no se presenta como éxito.

## Verificación final del Bloque 23 con Gemini

**Completada por el alumno. No se requiere otra consulta pagada.**

En `rechazo-final-23`, Gemini leyó el artículo 34 y propuso la entrega. La terminal
recibió `n` y mostró:

```text
Resultado de aprobación: n recibida: rechazo explícito; espera: 21.6 s.
```

Se comprobó una decisión `aprobado: false` con identificador
`171c1f416a5349dfae1a3ff708696abc`, la traza sin error y la ausencia de
`output/agente/informes_entregados/171c1f416a5349dfae1a3ff708696abc.md`.
Se conservan la [salida, el consumo y los controles](evidencias/bloques-21-23/rechazo-explicito-gemini.md).

Antes de esta corrida, el diagnóstico con modelo falso también leyó `s` y `n`.
La nueva evidencia comprueba el recorrido con el conector real, pero no explica
retroactivamente por qué una corrida anterior rechazó de inmediato.

Los JSONL acumulan ejecuciones anteriores: los conteos son de líneas, no de acciones,
y no bastan por sí solos para probar el caso. Hay que revisar sesión, fecha e
identificador: `informe-rechazado` se usó en dos intentos con decisiones distintas.
`coincide` compara el booleano, no distingue `n` de timeout o EOF. La confirmación
del alumno es necesaria para no presentar estos últimos como rechazo explícito.

Los eventos de los dos intentos y de ambos controles posteriores están conservados
en `docs/evidencias/bloques-21-23/trazas_agente.jsonl` y `aprobaciones.jsonl`:
seis trazas y cinco decisiones, sin alterar las anteriores ni introducir claves.

Para repetir el ensayo completo en el futuro, usar una ruta JSON nueva y guiarse
por la sesión mostrada, no por el orden de los avisos: un caso puede fallar sin
llegar a pedir aprobación. No sobrescribir los dos JSON ya conservados.

## Diferencias y límites relevantes

- El prompt aclara que el historial ayuda a entender la consulta pero no acredita
  lo que dice la ley.
- La salida se convierte a texto **antes** de la memoria; invertir ese orden
  intenta guardar los bloques de Gemini y puede fallar.
- `handle_validation_error` se asigna después de `@tool`, porque el decorador no
  acepta esa opción.
- Solo las herramientas de varios parámetros tienen un esquema explícito.
  `buscar_en_ley` mantiene la inferencia de su único argumento de texto.
- El ensayo agrega sesión, tamaño previo del historial, primera línea de la
  observación y contraste de secuencia y decisiones para el Bloque 23.
- La cuenta del supervisor se registra como cuenta local, sin autenticar a la
  persona. La aprobación usa la sesión del contexto, no una sesión elegida por
  el modelo.
- Los avisos de deprecación se conservan y se documentan, no se ocultan.
- La espera de aprobación ahora explica en stderr si leyó `s`, `n`, una línea
  vacía, EOF, agotó el tiempo o encontró una condición de terminal inválida. Los
  JSONL conservan el contrato booleano; los motivos antiguos siguen siendo desconocidos.

La explicación completa está en [límites de autonomía](limites-autonomia-agente.md).

## Condiciones para marcar la entrega como cerrada

- [x] Implementación de herramientas, memoria, aprobación y trazas.
- [x] Pruebas sin red y comandos de revisión preparados.
- [x] Evidencias reales de 21 y 22 conservadas.
- [x] Documentación, guía y arquitectura del nuevo flujo.
- [x] Dos intentos reales de 23 ejecutados por el alumno y revisados, con sus diferencias.
- [x] Trazas y decisiones de esos intentos conservadas, sin claves.
- [x] Diagnóstico humano sin Gemini: `s` y `n` explícitas con modelo falso y archivos temporales.
- [x] Rechazo explícito con `n` en el agente con Gemini y ausencia de su archivo verificados.
- [ ] Publicación de la rama autorizada por el alumno.
- [ ] Clonado desde GitHub, `uv sync --locked` y suite en una instalación limpia.

No se hace push ni merge a `main` como parte de preparar estos cambios. La
instalación desde un archivo local sin `.venv` es una comprobación complementaria;
no sustituye el clonado desde GitHub exigido en la Fase 4.
