# Publicación e instalación desde GitHub — bloques 31 y 32

## Integración y publicación

| Referencia | Valor |
| --- | --- |
| Destino publicado | [main](https://github.com/brandonhc33/practica-2-http-autenticada/tree/main) |
| Rama integrada, solo local | `bloques-31-32`, en `1b6d427a9cb7a3f7fdfd53eb64df215cb1fe7312` |
| Main anterior | `92679d7c7c93a988857963b277cf572f5aed21f3` |
| Merge publicado | [`d2188d08e8bf3f79d83af7820f369b7ac3c80865`](https://github.com/brandonhc33/practica-2-http-autenticada/commit/d2188d08e8bf3f79d83af7820f369b7ac3c80865) |
| Fecha | 24 de noviembre de 2026, 23:42:16 UTC |

La integración no produjo conflictos y el árbol del merge es idéntico al de la rama.
`refs/heads/main` es la única rama en GitHub. No se usó force-push ni se publicaron
tags. Este registro se añade después del merge.

## Instalación desde un clon limpio

Entre las 23:42:30 y las 23:43:10 UTC, en una carpeta temporal nueva y exactamente en el
merge publicado. No existían `.env`, `.venv` ni `vectorstore/`, y se retiraron las
variables de claves del entorno.

| Comprobación | Resultado |
| --- | --- |
| `uv sync --locked` | 126 paquetes, Python 3.12.13. |
| `uv run python -m pytest tests -q` | **407 pruebas y 698 subpruebas aprobadas**; 11 avisos de deprecación ya conocidos. |
| `uv run python -m tests` | Aprobado. |
| `uv run ruff check .` | Sin errores. |
| `uv run basedpyright` | 0 errores, 0 advertencias, 0 notas. |
| `scripts.logging_rag` | 6 comprobaciones correctas. |
| `scripts.registro_prompts` y `scripts.matriz_riesgos` | Salidas idénticas a las evidencias. |
| `scripts.grafo_supervision demo` | Ambos caminos; termina sin error. |
| Huellas del índice de evidencias | 11 de 11 coinciden. |

No se hicieron consultas a Gemini en esta verificación.
