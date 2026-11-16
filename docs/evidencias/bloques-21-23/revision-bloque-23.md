# Revisión de los dos primeros intentos humanos del Bloque 23

## Alcance y procedencia

El alumno ejecutó las corridas en su terminal. Se conservan los JSON originales,
sin corregir sus resultados, junto con copias de los cuatro eventos de traza y
las tres decisiones locales. Se verificó la igualdad de los JSONL conservados
con los de `output/agente/` al hacer esta revisión.

Los conteos de esta sección corresponden a esa primera revisión. Posteriormente se
agregaron una quinta traza y una cuarta decisión de `rechazo-manual-23`; el
[diagnóstico posterior](diagnostico-aprobacion.md) documenta por qué esa consulta
tampoco certifica una `n` explícita.

Finalmente se agregaron una sexta traza y una quinta decisión de `rechazo-final-23`,
que sí recibió `n` explícita con Gemini. Su
[verificación final](rechazo-explicito-gemini.md) está separada de los intentos
históricos descritos aquí.

No se incluyeron claves ni archivos `.env`. Los registros sí identifican la
cuenta local del supervisor y contienen las rutas locales y el contenido de los
informes, como prevé D-12. No se publicaron archivos en un servicio externo.

## Intento 1

[Ensayo original](ensayo-bloque-23.json): 0 de 2 coincidencias.

- La sesión `informe-aprobado` recibió un error de Gemini: `503 UNAVAILABLE`, por
  alta demanda. No llegó a pedir aprobación. El fallo quedó en la primera traza.
- La sesión `informe-rechazado` sí leyó el artículo 34 y pidió aprobación, pero se
  aprobó. La entrega local se completó y no coincide con el rechazo esperado.
- Fueron 5 intentos de llamada: 4 respuestas con consumo y 1 fallo sin metadatos
  de uso. Se registraron 4.320 tokens y **USD 0,0023102 conocidos**; no se atribuye
  costo cero al intento sin uso informado.

El nombre de una sesión no fuerza la decisión. El control obedeció la aprobación
real, no el nombre `informe-rechazado`. No se borró ese informe ni se cambió el
JSON para hacer pasar el ensayo.

## Intento 2

[Ensayo original](ensayo-bloque-23-intento-02.json): 2 de 2 coincidencias
automáticas, 6 llamadas con consumo, 6.656 tokens y USD 0,0034708.

| Sesión | Decisión registrada | Archivo verificado |
| --- | --- | --- |
| `informe-aprobado` | `true`, a las 17:45:19 UTC | `7fc1a0078c724945a8bec1a6e60dd8dd.md`, íntegro respecto al título y contenido aprobados. |
| `informe-rechazado` | `false`, a las 17:50:44 UTC | No existe `748a6fe671114492a27dea7241599692.md`. |

El alumno compartió la entrada `s` del primer caso, pero reportó que no pudo
introducir `n` en el segundo. Hay 324,94 segundos entre las decisiones, incluyendo
las llamadas al modelo entre ambas: es compatible con el límite de 300 segundos
del segundo aviso. El registro no conserva el motivo de la decisión negativa,
por lo que **no se certifica como rechazo explícito mediante `n`**.

`aprobacion_coincide` compara únicamente el booleano: un timeout o EOF también
pueden producir `false`. El total de coincidencias no sustituye la revisión humana
de ese detalle. La observación del modelo que dice «aprobación rechazada» tampoco
prueba qué entrada leyó el programa.

Los resúmenes de los artículos 12 y 34 se contrastaron manualmente con la copia
local usada por las herramientas: describen sus obligaciones sin añadir una
entrega real. Esto no constituye una validación automática de citas ni asesoría
legal.

## Artefactos y decisiones

Los identificadores permiten distinguir los intentos aunque reutilicen las sesiones:

| Identificador de aprobación | Origen | Resultado |
| --- | --- | --- |
| `896930a914ce46bb90f27fd1da87a7fe` | Intento 1, artículo 34 | Aprobado y guardado, aunque se esperaba rechazar. |
| `7fc1a0078c724945a8bec1a6e60dd8dd` | Intento 2, artículo 12 | Aprobado y guardado. |
| `748a6fe671114492a27dea7241599692` | Intento 2, artículo 34 | No aprobado; no hay informe guardado. |

Las [trazas](trazas_agente.jsonl) conservan los cuatro casos, incluido el error 503.
Las [aprobaciones](aprobaciones.jsonl) conservan las tres decisiones. Los informes
aprobados se comprobaron contra el contenido exacto de sus decisiones, sin mover
ni borrar los archivos de operación.

## Contraste con el PRD

Comandos ejecutados sobre los archivos locales del agente:

```text
grep -n "esperar_aprobacion(" src/orquestacion/herramientas.py
183:    aprobado = esperar_aprobacion(

wc -l output/agente/trazas_agente.jsonl output/agente/aprobaciones.jsonl
4 output/agente/trazas_agente.jsonl
3 output/agente/aprobaciones.jsonl
7 total

grep -c '"herramienta": "obtener_articulo"' output/agente/trazas_agente.jsonl
3

grep -c '"herramienta": "entregar_informe"' output/agente/trazas_agente.jsonl
3

uv run python -m src.orquestacion.supervision
[]
```

Los dos `grep -c` cuentan líneas que contienen una herramienta, no el número total
de acciones. Las tres trazas exitosas contienen una lectura y una propuesta de
entrega cada una. La traza del 503 no contiene pasos: el ejecutor los pierde al
fallar, como se documentó en los límites.

## Prueba de entrada y control posterior

La [prueba local de dos entradas](prueba-entrada-terminal.md), sin Gemini, sí leyó
`s` y luego `n`, en 4,5 y 1,9 segundos respectivamente. No reprodujo la dificultad
de entrada del ensayo.

El alumno completó después el diagnóstico con modelo falso y la consulta
`rechazo-final-23` con Gemini. Esta última leyó `n` explícita; se conservaron la
traza y la decisión nuevas y se comprobó que el informe no existe. Ver
[rechazo final verificado](rechazo-explicito-gemini.md). La comprobación desde
GitHub sigue pendiente de publicación autorizada.
