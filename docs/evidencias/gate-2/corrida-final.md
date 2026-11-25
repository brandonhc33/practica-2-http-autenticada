# Corrida final con Gemini

25-11-2026, 01:25 UTC, con el prompt 3 activo, `gemini-3.5-flash-lite`, `k = 5` y el índice
persistido de 233 fragmentos.

| Paso | Resultado |
| --- | --- |
| `python verificar_entorno.py` | «Entorno listo para la corrida final»; salida 0. |
| `python servicio_rag.py preguntar …` | Estado `ok`, salida 0, sin excepciones. |
| `GATE2_REAL=1 python -m pytest test_gate2.py -v` | 4 pruebas aprobadas en 7,99 s. |
| `grep -ri ana.perez output/servicio` | Ninguna línea. |

**Consulta:** ¿Qué meta tienen los envases domiciliarios de vidrio el primer año?
**Respuesta:** 11 %, con DS 12/2020, artículo 21, en el texto y en la lista de fuentes.
Coincide con la tabla de la publicación.

| Etapa | Tiempo |
| --- | --- |
| Embedding de la pregunta | 1.019,8 ms |
| Búsqueda en Chroma | 2,7 ms |
| Generación | 1.710,1 ms |
| Total | 2.735,0 ms |

Tokens: 2.770 de entrada y 80 de salida. Costo estimado de la generación: US$ 0,001031. El
costo del embedding es desconocido. La traza tiene cinco eventos con el mismo `trace_id`;
ninguno contiene la pregunta ni la respuesta.

## Entrega supervisada

La respuesta sobre el plástico en el tercer año, de la
[prueba de prompts](prueba-prompts-resultado.md), se pidió entregar después de activar el
prompt 3. Quedó pausada (`entregar_respuesta-21631a3881bd`), se revisó junto a los fragmentos
citados y se aprobó en la terminal a las 01:24 UTC. Solo entonces se creó el archivo, en una carpeta
local que no se publica. No se envió a ningún cliente.

En `GATE2_REAL=1` las pruebas 1 a 3 usan Gemini. La 4 recupera con el índice real, pero genera
con el modelo simulado y decide en código: comprueba el mecanismo. La decisión humana es la de
esta sección.
