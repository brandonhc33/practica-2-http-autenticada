# Publicación e instalación desde GitHub — bloques 29 y 30

## Integración y publicación

| Referencia | Valor |
| --- | --- |
| Repositorio | `git@github.com:brandonhc33/practica-2-http-autenticada.git` |
| Destino publicado | [main](https://github.com/brandonhc33/practica-2-http-autenticada/tree/main) |
| Rama integrada, solo local | `bloques-29-30`, en `064adcbcd8c001b08ae7c59ad44db830288604a1` |
| Main anterior | `c3a47468087ab5ff9f8bc6a3dd129a8945593a18` |
| Merge publicado | [`0a792e37733803fe4becd33f4e1eda04ae33cc1c`](https://github.com/brandonhc33/practica-2-http-autenticada/commit/0a792e37733803fe4becd33f4e1eda04ae33cc1c) |
| Fecha | 24 de noviembre de 2026, 22:09:47 UTC |

La integración no produjo conflictos y el árbol del merge es idéntico al de la rama.
Después del push, `refs/heads/main` es la única rama en GitHub. No se usó
force-push ni se publicaron tags. Este registro se añade después del merge.

## Instalación desde un clon limpio

Se clonó `main` desde GitHub en una carpeta temporal nueva, entre `22:10:01` y
`22:11:26` UTC. El clon quedó exactamente en el merge publicado. No existían `.env`,
`.venv` ni `vectorstore/`, y se retiraron las variables de claves del entorno.

| Comprobación | Resultado |
| --- | --- |
| `uv sync --locked` | 123 paquetes, Python 3.12.13. |
| `uv run python -m pytest tests -q` | **346 pruebas y 630 subpruebas aprobadas**; 11 avisos de deprecación ya conocidos. |
| `uv run python -m tests` | Aprobado. |
| `uv run ruff check .` | Sin errores. |
| `uv run basedpyright` | 0 errores, 0 advertencias, 0 notas. |
| `scripts.dataset_tuning --comprobar-validador --comprobar-api` | 10 copias rotas detectadas y rechazo local de PEFT. |
| `scripts.linea_base_rutas --solo-regla-local` | 22 de 24. |
| `scripts.decision_personalizacion --linea-base .../linea-base-02.json` | Mismo resultado conservado; solo falta la línea que anuncia el archivo generado con `--salida`. |
| `git diff --check` y estado final | Sin errores; clon limpio, en `main`. |

Son comprobaciones locales sin Gemini: no repiten la medición ni son una ejecución
remota de CI. El estado de la actividad se mantiene en el
[checklist de entrega](../../entregas/bloques-29-30.md#evidencias-y-checklist-de-cierre).
