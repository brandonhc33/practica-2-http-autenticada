# Entrega de los bloques 21 a 23 — agente de Ley REP

**Estado: implementación preparada; cierre pendiente de ensayo humano del Bloque 23
y comprobación desde GitHub después de publicar.** No se declara la entrega cerrada
sin esas evidencias.

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
| Total observado | 6 de 6 | 10 | 7.101 | 0,0038969 |
| 23 | Pendiente de decisiones humanas | — | — | — |

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

Estas evidencias son históricas: se generaron antes de incorporar la tercera
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
| CA-19 | Ensayos reales de 21 y 22 conservados; falta el de 23. |
| CA-20 | Control de aprobación presente en código; falta contrastarlo con las trazas reales de 23. |

También se prueba el caso en que el modelo falla después de una entrega aprobada:
no se repite el flujo y sobreviven el informe y la aprobación, aunque la traza
pierda los pasos. Un error al escribir la aprobación impide entregar; un error al
escribir el informe no se presenta como éxito.

## Ensayo humano pendiente — Bloque 23

Este paso lo ejecuta el alumno en **su terminal interactiva**, desde la raíz del
worktree que contiene estos cambios, no desde otra copia antigua del proyecto.
No usar tuberías, `echo s`, respuestas automáticas ni pedir a un agente que apruebe.

1. Configurar `GEMINI_API_KEY` localmente. No hace falta iniciar la API.
2. Confirmar que se autoriza esta corrida: son unas seis llamadas, hasta ocho
   iteraciones de modelo entre los dos casos; el costo final depende del consumo.
3. Ejecutar con una ruta de salida nueva:

   ```bash
   uv run python -m scripts.ensayo_agente --bloque 23 \
     --salida docs/evidencias/bloques-21-23/ensayo-bloque-23.json
   ```

4. Leer el primer informe, sobre el artículo 12. Si es correcto, escribir `s` y
   Enter. Si no lo es, rechazarlo y conservar la diferencia, no aprobar solo para
   hacer pasar el ensayo.
5. Leer el segundo informe, sobre el artículo 34, y escribir `n` y Enter.
6. Revisar el JSON del ensayo: dos casos, secuencias
   `obtener_articulo` → `entregar_informe`, una aprobación y un rechazo. Si Gemini
   toma otro recorrido, queda como diferencia; no se modifica la evidencia.
7. Contrastar los archivos locales y revisar repeticiones:

   ```bash
   grep -n "esperar_aprobacion(" src/orquestacion/herramientas.py
   wc -l output/agente/trazas_agente.jsonl output/agente/aprobaciones.jsonl
   grep -c '"herramienta": "obtener_articulo"' output/agente/trazas_agente.jsonl
   grep -c '"herramienta": "entregar_informe"' output/agente/trazas_agente.jsonl
   uv run python -m src.orquestacion.supervision
   ```

Los JSONL acumulan ejecuciones anteriores: los conteos son de líneas, no de acciones,
y no bastan por sí solos para probar el caso. Hay que revisar las sesiones
`informe-aprobado` e `informe-rechazado`, sus decisiones y los identificadores. El
ensayo guarda solo las decisiones nuevas de cada caso. Debe haber un archivo del
caso aprobado y ninguno del rechazado.

Después, revisar que las trazas no tengan información privada y conservar solo
los eventos de este ensayo en `docs/evidencias/bloques-21-23/trazas_agente.jsonl` y
`aprobaciones.jsonl`. No sobrescribir evidencias previas. Ese paso y la actualización
del estado de entrega se harán al revisar el resultado con el alumno.

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

La explicación completa está en [límites de autonomía](limites-autonomia-agente.md).

## Condiciones para marcar la entrega como cerrada

- [x] Implementación de herramientas, memoria, aprobación y trazas.
- [x] Pruebas sin red y comandos de revisión preparados.
- [x] Evidencias reales de 21 y 22 conservadas.
- [x] Documentación, guía y arquitectura del nuevo flujo.
- [ ] Ensayo real de 23 ejecutado por el alumno y revisado.
- [ ] Trazas y decisiones de ese ensayo conservadas, sin datos privados.
- [ ] Publicación de la rama autorizada por el alumno.
- [ ] Clonado desde GitHub, `uv sync --locked` y suite en una instalación limpia.

No se hace push ni merge a `main` como parte de preparar estos cambios. La
instalación desde un archivo local sin `.venv` es una comprobación complementaria;
no sustituye el clonado desde GitHub exigido en la Fase 4.
