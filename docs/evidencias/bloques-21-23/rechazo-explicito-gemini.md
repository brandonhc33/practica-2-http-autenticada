# Rechazo explícito con Gemini — Bloque 23

## Procedencia y resultado

El alumno ejecutó el agente real en su terminal y compartió la salida en el hilo.
La sesión fue `rechazo-final-23`, con `gemini-3.5-flash-lite`. No se usó el modelo
falso ni se automatizó la respuesta humana.

**Resultado: rechazo explícito comprobado.** La terminal leyó `n`; el programa
registró `aprobado: false` y no creó el informe correspondiente. Esta evidencia
completa el control funcional que faltaba del Bloque 23. No hace falta repetirlo.

Se utilizó el comando siguiente; la ruta privada del `.env` se sustituye aquí
por un marcador. Es una ejecución histórica, no una instrucción de repetirla:

```bash
uv run --env-file /ruta/a/tu/.env python -m src.orquestacion.agente_con_herramientas --sesion rechazo-final-23 "Lee el artículo 34 de la Ley REP y entrega un informe breve titulado 'Prueba de rechazo manual', citando ese artículo. Solicita mi aprobación mediante entregar_informe."
```

## Evidencia de la terminal

Extracto de la salida compartida por el alumno:

```text
ENTREGA SIMULADA — sesión: rechazo-final-23
Título: Prueba de rechazo manual
```

Tras mostrar el contenido completo:

```text
¿Aprobar esta entrega simulada? [s/N] (límite: 300 s)
Escribe s o n y pulsa Enter; no es un menú de selección.
n
Resultado de aprobación: n recibida: rechazo explícito; espera: 21.6 s.
```

La salida mostró tres respuestas HTTP 200 de Gemini y terminó sin error. Los
avisos anteriores eran las deprecaciones conocidas de la memoria, no fallos de
autenticación ni de aprobación.

## Contraste con los archivos locales

| Dato | Valor comprobado |
| --- | --- |
| Sesión | `rechazo-final-23`, con cero mensajes previos. |
| Decisión | Una sola decisión, `aprobado: false`. |
| Identificador | `171c1f416a5349dfae1a3ff708696abc`. |
| Fecha de la decisión | `2026-11-16T23:12:17.817387+00:00`. |
| Fecha de la traza | `2026-11-16T23:12:19.316033+00:00`. |
| Herramientas, en orden | `obtener_articulo({"numero": "34"})`, después `entregar_informe`. |
| Observación de entrega | `Entrega no aprobada (171c1f416a5349dfae1a3ff708696abc). No se guardó ni se envió el informe.` |
| Error de la traza | `null`. |
| Informe asociado | No existe `output/agente/informes_entregados/171c1f416a5349dfae1a3ff708696abc.md`. |

El artículo leído coincide exactamente con el que devuelve la copia local de la
ley. El título y el contenido propuestos en la traza coinciden con los de la
decisión. También se comprobaron los otros informes: los dos aprobados siguen
íntegros y no existen los tres correspondientes a decisiones negativas.

Se agregaron solo los dos eventos nuevos a las copias revisadas de
[aprobaciones](aprobaciones.jsonl#L5) y [trazas](trazas_agente.jsonl#L6), sin
modificar eventos anteriores. Las copias se contrastaron con los originales de
operación. No se copiaron claves ni archivos `.env`.

## Consumo de esta ejecución

El consumo procede del resumen que el alumno compartió en la terminal:

| Concepto | Valor |
| --- | --- |
| Respuestas con costo | 3 |
| Consultas fallidas | 0 |
| Intentos HTTP | 3 |
| Tokens de entrada | 2.979 |
| Tokens de salida | 423 |
| Tokens totales | 3.402 |
| Costo conocido | USD 0,0019512 |

Las tres operaciones informaron USD 0,0002779, 0,0007693 y 0,000904. La suma
coincide con el resumen. Acumulado con las corridas anteriores: **27 intentos,
24.936 tokens registrados y USD 0,0136782 conocidos**. Sigue habiendo un intento
histórico sin metadatos de uso; no se le atribuye costo cero.

## Contraste con los controles del PRD

Comandos ejecutados después de esta corrida:

```text
grep -n "esperar_aprobacion(" src/orquestacion/herramientas.py
183:    aprobado = esperar_aprobacion(

wc -l output/agente/trazas_agente.jsonl output/agente/aprobaciones.jsonl
6 output/agente/trazas_agente.jsonl
5 output/agente/aprobaciones.jsonl
11 total

grep -c '"herramienta": "obtener_articulo"' output/agente/trazas_agente.jsonl
5

grep -c '"herramienta": "entregar_informe"' output/agente/trazas_agente.jsonl
5

uv run python -m src.orquestacion.supervision
[]
```

Los `grep -c` cuentan líneas que contienen la herramienta, no acciones. El
resultado `[]` indica que el detector no encontró repeticiones consecutivas por
sesión; no demuestra por sí mismo exactitud legal.

## Comprobaciones de esta revisión

Después de conservar la evidencia se ejecutaron:

```text
uv run python -m pytest tests -v
263 passed, 11 warnings, 481 subtests passed

uv run ruff check .
All checks passed!

uv run basedpyright
0 errors, 0 warnings, 0 notes

git diff --check
Sin errores.
```

Los 11 avisos son las deprecaciones de memoria ya documentadas. También se
comprobaron 301 enlaces y anclas de la documentación, la igualdad byte por byte
de ambos JSONL con los originales y la integridad de sus eventos anteriores.
Esta revisión no repitió la consulta a Gemini ni consumió cuota.

## Alcance de la conclusión

La combinación de entrada visible, motivo explícito, decisión, observación de la
herramienta y ausencia del archivo permite certificar el rechazo de esta corrida.
No se infiere una `n` solo a partir de `false`.

Esto no identifica retroactivamente la causa del rechazo inmediato anterior, no
convierte este ensayo en asesoría legal ni añade un envío real a terceros.
Después se completaron el merge y la publicación únicamente de `main`, además de
la [instalación desde un clon de GitHub](verificacion-github.md). La rama de bloques
se conserva local; ver el [checklist de entrega](../../entrega-bloques-21-23.md#condiciones-para-marcar-la-entrega-como-cerrada).
