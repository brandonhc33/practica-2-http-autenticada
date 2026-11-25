# Evidencias del Gate 2

## Procedencia y archivos

Generadas el 24 y 25-11-2026 en la rama local `gate-2`, con Python 3.12.13, `chromadb` 1.5.9,
`langgraph` 1.2.20 y `langchain-core` 1.7.6.

| Archivo | Origen | Qué muestra |
| --- | --- | --- |
| [`ensayo.txt`](ensayo.txt) | `servicio_rag.py`, **simulado** sobre las normas reales | Servicio completo, eventos y 11 comprobaciones. |
| [`evaluacion-gemini.txt`](evaluacion-gemini.txt) y [JSON](evaluacion-gemini.json) | **Gemini real** | Recuperación de 27 preguntas con el índice de dos normas. |
| [`evaluacion-palabras.txt`](evaluacion-palabras.txt) | Local, sin Gemini | Las mismas preguntas con búsqueda por palabras. |
| [`prueba-prompts-resultado.md`](prueba-prompts-resultado.md) | **Gemini real**, resumen | 12 consultas: seis con cada versión del prompt. |
| [`corrida-final.md`](corrida-final.md) | **Gemini real**, resumen | Entorno, consulta, cuatro pruebas y entrega aprobada. |
| [`autoevaluacion.txt`](autoevaluacion.txt) | `scripts.autoevaluacion_gate2` | Puntajes revisados y no compensables ejecutados. |
| [`verificacion-local.md`](verificacion-local.md) | Pruebas, ruff, basedpyright y clon con `pip` | Comprobaciones de la implementación. |

| Archivo | SHA-256 |
| --- | --- |
| `ensayo.txt` | `dbdce66e6a3ed779cc48e92fc33a205e553207cebe5ba15f87bbbd8198778d2a` |
| `evaluacion-gemini.txt` | `f6d88c1fda9498e4c0d4a0f4f35aee9a24e7004f9a923501ca5bbaf26143817f` |
| `evaluacion-gemini.json` | `e645099c1af1cc3ce3ff768616d9f0ef70a1c2035d7f13a0a48e0e0bbc9ecd51` |
| `evaluacion-palabras.txt` | `29c9b54692e9008593611ef86d9f547e50e9c10b7d09419c952b8b99ef3a7b05` |
| `autoevaluacion.txt` | `9516551bd191a489a6f073421fac989c8aa109f1fb546aeb903e663852b6b7e6` |
| `datos/ds_12_2020/DS-12-2020_DO-16-MAR-2021.pdf` | `a9f712fdc83007f1655d6280530ac21a939b1404946f2e22a68284badae4fdf7` |
| `datos/ds_12_2020/tablas.json` | `a384c4ed6f7b32dd303f9fb57b569616ea01328cf4bdc9edfb8762509f1dfb25` |
| `datos/ds_12_2020/ds_12_2020.json` | `b032ddb733d1862657ae0fdcba4c12b9a36ab17b3a7b66e73c0096e8f56695d9` |
| `datos/gobernanza/normas_activas.json` | `5963f77eff39cfb8091cdbebf682f01b3855099122d38a21496563c52522cc30` |
| `datos/gobernanza/prompts_rag.json` | `68a795e9045a3151591958074b7354e0ae0ec71707a7fa6fb65077eeecac183f` |
| `datos/gobernanza/prompt_activo.json` | `e9acd053cc08ff74dd35ee0a3a4c40e0f4c233ebac772e3e8e14d99b484e6aa4` |
| `datos/gobernanza/matriz_riesgos.json` | `cda2931ef3c08982d8103cbb49add8f934eb1026966de9226821a3b3a18ae357` |
## Indexación real

| Hora UTC, 25-11-2026 | Qué ocurrió | Embeddings |
| --- | --- | --- |
| 00:40 | Solo la Ley 20.920, con un archivo temporal de normas activas. | 99, en 6,7 s |
| 00:40 a 00:42 | Primer intento con el decreto: lo rechazó el proveedor, sin guardar fragmentos. La consulta respondió «quedó a medias». | 0 guardados |
| 00:43 | Segundo intento: cortado por el proveedor tras 100 fragmentos. | 100 |
| 00:44 | Continuación: solo los que faltaban. | 34 |

Al terminar, los 99 vectores de la ley eran idénticos a los del primer paso. Huella del
índice: `1e214ae608fb`. El almacenamiento de Chroma no se versiona: se reconstruye.

## Cómo se interpretan

- El ensayo comprueba la mecánica: su modelo copia el primer fragmento.
- La evaluación mide fragmentos, no respuestas. Las etiquetas se prepararon con asistencia de
  IA antes de buscar y no tienen revisión jurídica.
- El criterio de las preguntas cruzadas **no se cumple** y se conserva así.
