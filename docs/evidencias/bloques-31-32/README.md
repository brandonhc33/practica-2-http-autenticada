# Evidencias de observabilidad y gobernanza — bloques 31 y 32

## Procedencia y archivos

Generadas el 24-11-2026 en la rama local `bloques-31-32`, con `langgraph` 1.2.20,
`langgraph-checkpoint-sqlite` 3.1.3 y `langchain-core` 1.7.6. Las pruebas
de prompts y de la orden escondida usaron **Gemini real**; el resto se obtuvo sin Gemini, clave ni
red, con consultas, documentos y decisiones de prueba.

| Archivo | Origen | Qué muestra |
| --- | --- | --- |
| [`logging-ensayo.txt`](logging-ensayo.txt) | `scripts.logging_rag` | Eventos de 5 consultas de prueba y 6 comprobaciones correctas. |
| [`registro-prompts.txt`](registro-prompts.txt) | `scripts.registro_prompts` | Dos versiones, la activa y su diferencia. |
| [`supervision-demo.txt`](supervision-demo.txt) | `scripts.grafo_supervision demo` | Pausa, rechazo y aprobación **simulados** sobre copias temporales. |
| [`matriz-resultado.txt`](matriz-resultado.txt) | `scripts.matriz_riesgos` | Ocho riesgos ordenados y validados. |
| [`prueba-prompts-criterio.md`](prueba-prompts-criterio.md) | Escrito antes de medir | Preguntas, qué cuenta como cumplimiento y cómo se decide. |
| [`prueba-prompts-resultado.md`](prueba-prompts-resultado.md) | **Gemini real**, `scripts.logging_rag --consultar` | 10 consultas: 5 con v1 y 5 con v2. |
| [`prueba-prompts-registro.txt`](prueba-prompts-registro.txt) | Publicado con `proponer-evidencia` y decisión en la terminal | Respuestas y eventos de esas 10 consultas. |
| [`orden-escondida-criterio.md`](orden-escondida-criterio.md) , [resultado](orden-escondida-resultado.md) y [registro](orden-escondida-registro.txt) | **Gemini real**, `scripts.ensayo_inyeccion_indirecta` | 2 generaciones con una orden que el filtro no reconoce. |
| [`verificacion-local.md`](verificacion-local.md) | Pruebas, ruff, basedpyright y unittest | Comprobaciones de la implementación. |

| Archivo | SHA-256 |
| --- | --- |
| `logging-ensayo.txt` | `095b4b4869a184a1a2be9a61c457812f9d165e85be0b95e6e531e19bd51d11ad` |
| `registro-prompts.txt` | `20ef4b9cd8cc4a8af093f28e21046cad14a548771f3eeedb5983e33af60969ec` |
| `supervision-demo.txt` | `af68c9ef0f4795a76a177e9a40477aaa16aa1f1bba205ffa5834947ba3fdd942` |
| `matriz-resultado.txt` | `7f4a2fe2ba579b3eda846ed85f04ae32f2dc9c85cdd38b7c1ca1395621d28348` |
| `prueba-prompts-criterio.md` | `19f220d955f185629f46709b264a523f9692cb3871385ef3a4fda7ec9788c798` |
| `prueba-prompts-registro.txt` | `35fcf6f28489bb3f65ad989b7a364d4c70886f7ce96446967d36e6cc556f23b5` |
| `orden-escondida-criterio.md` | `d17d445a06e4f7d2291be4b94b2152934e3c85fe59d7a4ac11cbd001561cc345` |
| `orden-escondida-registro.txt` | `07f7a1f231a32c7bd1c319a5c4a9eb3d82f0f3ec8270587e14ab50ed246bc768` |
| `datos/gobernanza/prompts_rag.json` | `6a416f90967affa22652c9c616e5d7079bbc90d89bf5c3d923cf541a017771e3` |
| `datos/gobernanza/prompt_activo.json` | `4e6e891e483dfe6fb49eb09c8cbd441e96d3d51d88b35a290967943f66f09347` |
| `datos/gobernanza/matriz_riesgos.json` | `ef507a4d8878ee4f445a4c1a7e6e8d19eeb2dd62718ec6af4130e4d78a1cf898` |

## B31: qué se observa

- **Filtro:** de dos documentos, uno limpio y uno con inyección, el segundo se descarta
  (tres patrones) y el primero llega al modelo de prueba.
- **Consumo:** los 210 tokens de entrada y 18 de salida del mensaje de prueba aparecen
  en su evento. El costo usa la tarifa del proyecto; no corresponde a una llamada.
- **Aislamiento:** dos consultas simultáneas tienen trazas distintas, con cinco eventos
  cada una.
- **Citas:** una respuesta sin citas termina en abstención.
- **Contenido:** la pregunta de prueba incluye un correo ficticio. No aparece en los
  registros, ni tampoco la pregunta, la respuesta o los fragmentos.

Los tiempos `ms` son de un modelo de prueba y no miden la latencia del sistema.

## B32: qué se observa

- **Prompts:** v1 `18db60ea8163` es el prompt de los bloques 26 a 28; v2
  `fa9063213deb` agrega tres líneas. Ambas cumplieron los cinco casos de la
  prueba real; eso no demuestra que v2 proteja más. v2 se activó el
  24-11-2026 con decisión en la terminal. Los ensayos sin red son anteriores y usan v1.
- **Supervisión:** mientras espera, la versión activa no cambia; con rechazo se mantiene
  y con aprobación cambia solo la copia temporal. Un segundo intento se rechaza.
- **Matriz:** 3 CRITICO, 1 ALTO y 4 MEDIO, todos al límite. Las estimaciones se
  propusieron con asistencia de IA y se revisaron: una subió de P3 a P4.

Los cuatro archivos `.txt` sin Gemini se guardaron directamente porque no contienen consultas de
personas. Los registros de consultas reales pasan por `proponer-evidencia`.
