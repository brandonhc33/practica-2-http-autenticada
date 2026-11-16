# Entrega de los bloques 21 a 23 — agente de Ley REP

**Estado: implementación y corridas humanas revisadas; falta verificar el rechazo
explícito con `n` dentro del agente y comprobar la instalación desde GitHub después
de publicar.** El segundo intento produjo una entrega aprobada y otra sin aprobar,
pero no demuestra que esta última haya leído `n`. La consulta adicional se rechazó
de inmediato; antes de gastar más cuota se hará el diagnóstico gratuito descrito abajo.

## Entregables

| Bloque | Implementación y revisión |
| --- | --- |
| 21 — agente con herramientas | [Herramientas](../src/orquestacion/herramientas.py), [agente](../src/orquestacion/agente_con_herramientas.py), límite de cuatro iteraciones y `intermediate_steps`. |
| 22 — herramienta estructurada y memoria | `ArgumentosArticulo`, validación como observación y memoria separada por `session_id`, en los mismos módulos. |
| 23 — supervisión y límites | `entregar_informe`, [supervisión y registros](../src/orquestacion/supervision.py), [límites de autonomía](limites-autonomia-agente.md) y ensayo preparado para aprobar y rechazar. |

La API y el flujo de los bloques 18 a 20 no se reemplazan. El agente es una entrada
adicional por terminal, con `langchain-classic` y el conector nativo de Gemini.

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
| Total registrado | No equivale a aceptación completa | 24 intentos | 21.534 registrados | 0,0117270 conocidos |

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
| CA-19 | Ensayos reales de los tres bloques conservados; falta verificar `n` explícita dentro del agente. |
| CA-20 | Control contrastado con las trazas reales: lecturas y propuestas de entrega presentes. Ver [revisión](evidencias/bloques-21-23/revision-bloque-23.md). |

También se prueba el caso en que el modelo falla después de una entrega aprobada:
no se repite el flujo y sobreviven el informe y la aprobación, aunque la traza
pierda los pasos. Un error al escribir la aprobación impide entregar; un error al
escribir el informe no se presenta como éxito.

## Ensayo humano pendiente — Bloque 23

Este paso lo ejecuta el alumno en **su terminal interactiva**, desde la raíz del
worktree que contiene estos cambios, no desde otra copia antigua del proyecto.
No usar tuberías, `echo s`, respuestas automáticas ni pedir a un agente que apruebe.

Ya se verificó la aprobación real y la función leyó dos entradas consecutivas en
la prueba local. **No hace falta repetir las dos consultas del ensayo completo.**
Sin embargo, la consulta adicional terminó en unos siete segundos sin dejar
introducir `n`. Eso descarta el timeout de 300 segundos para esa ejecución.
**Antes de repetir una consulta pagada**, ejecutar:

```bash
uv run python -m tests.orquestacion.ensayo_terminal
```

Es un modelo falso con el circuito del agente, red bloqueada y archivos
temporales: no requiere clave ni consume cuota. Pedirá `s` y luego `n`; si un
aviso se cierra solo, mostrará el motivo. Compartir esa salida antes de continuar.
Ver [diagnóstico y pruebas con pseudoterminal](evidencias/bloques-21-23/diagnostico-aprobacion.md).

Solo después de resolver la entrada, se coordinará una nueva consulta para
comprobar el rechazo explícito dentro del agente:

1. Configurar `GEMINI_API_KEY` localmente. No hace falta iniciar la API.
   Un worktree no hereda el `.env` ignorado por Git de la carpeta original.
   `uv run --env-file /ruta/a/tu/.env ...` permite usar ese archivo sin copiarlo.
2. El siguiente comando consume cuota: se esperan tres llamadas, con un máximo
   de cuatro iteraciones. Reemplazar la ruta del `.env` por la propia:

   ```bash
   uv run --env-file /ruta/a/tu/.env \
     python -m src.orquestacion.agente_con_herramientas \
     --sesion rechazo-manual-23-verificado \
     "Lee el artículo 34 de la Ley REP y entrega un informe breve titulado 'Prueba de rechazo manual', citando ese artículo. Solicita mi aprobación mediante entregar_informe."
   ```

3. Cuando aparezca **sesión: `rechazo-manual-23-verificado`**, leer el informe, escribir `n` y
   pulsar Enter antes de 300 segundos. El caso se considera comprobado si la
   terminal muestra esa entrada, la decisión queda en `false` y no se crea su
   archivo. Un nuevo timeout no se presenta como rechazo explícito.
4. Compartir la salida sin claves. Revisar las nuevas líneas de aprobación y
   traza, el identificador del informe ausente y el consumo mostrado en stderr.
5. Contrastar los archivos locales y revisar repeticiones:

   ```bash
   grep -n "esperar_aprobacion(" src/orquestacion/herramientas.py
   wc -l output/agente/trazas_agente.jsonl output/agente/aprobaciones.jsonl
   grep -c '"herramienta": "obtener_articulo"' output/agente/trazas_agente.jsonl
   grep -c '"herramienta": "entregar_informe"' output/agente/trazas_agente.jsonl
   uv run python -m src.orquestacion.supervision
   ```

Los JSONL acumulan ejecuciones anteriores: los conteos son de líneas, no de acciones,
y no bastan por sí solos para probar el caso. Hay que revisar sesión, fecha e
identificador: `informe-rechazado` se usó en dos intentos con decisiones distintas.
`coincide` compara el booleano, no distingue `n` de timeout o EOF. La confirmación
del alumno es necesaria para no presentar estos últimos como rechazo explícito.

Los eventos de los dos intentos y del control de rechazo inmediato están conservados en
`docs/evidencias/bloques-21-23/trazas_agente.jsonl` y `aprobaciones.jsonl`.
Después del control pendiente se agregarán solo los eventos nuevos revisados, sin
alterar las decisiones anteriores ni introducir claves.

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
- [ ] Rechazo explícito con `n` dentro del agente y ausencia de su archivo verificados.
- [ ] Publicación de la rama autorizada por el alumno.
- [ ] Clonado desde GitHub, `uv sync --locked` y suite en una instalación limpia.

No se hace push ni merge a `main` como parte de preparar estos cambios. La
instalación desde un archivo local sin `.venv` es una comprobación complementaria;
no sustituye el clonado desde GitHub exigido en la Fase 4.
