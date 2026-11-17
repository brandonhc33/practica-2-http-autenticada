# Publicación e instalación desde GitHub — bloques 24 a 28

## Integración y publicación verificadas

**Ampliación integrada y publicada en `main` con autorización explícita del
alumno.** Incluye el RAG de B24–28, las mediciones reales de la actividad 28,
la interpretación de métricas y la reorganización de `docs/`.
La rama `bloques-24-28` se conserva local; no se publicó su referencia en GitHub.

| Referencia | Valor |
| --- | --- |
| Repositorio | `git@github.com:brandonhc33/practica-2-http-autenticada.git` |
| Destino publicado | [main](https://github.com/brandonhc33/practica-2-http-autenticada/tree/main) |
| Rama integrada | `bloques-24-28`, en `0691a16e9522f0e95d834949887d16b053f08332` |
| Main anterior | `607c61f2b5b8fbf13081cca6b414d969e0351b04` |
| Merge publicado | [`12cca9731556ac82591eb7875dcc8862d0bb7696`](https://github.com/brandonhc33/practica-2-http-autenticada/commit/12cca9731556ac82591eb7875dcc8862d0bb7696) |
| Fecha de publicación | 17 de noviembre de 2026, UTC |

Este registro se añade después del merge mediante un cambio documental en `main`.
El hash de merge identifica la ampliación publicada, no el propio registro.

Se revisaron los remotos: `origin` apunta a GitHub; `local` es el enlace al
checkout original y no se utilizó para publicar. `origin/main` era antecesor
de la rama de bloques; la integración no produjo conflictos.

```bash
git fetch --no-tags origin refs/heads/main:refs/remotes/origin/main
git switch main
GIT_EDITOR=true git merge --no-ff bloques-24-28 \
  -m "Integrar los bloques 24 a 28 y ordenar la documentación"
git diff --exit-code bloques-24-28 HEAD
git -c push.followTags=false push origin refs/heads/main:refs/heads/main
git ls-remote --heads origin
```

Los comandos remotos usaron SSH en modo no interactivo (`BatchMode=yes`).
La comparación confirmó que el árbol del merge era idéntico al de la rama
integrada. GitHub confirmó el hash del merge en `refs/heads/main`; antes y
después del push esa era la única rama remota. No se usó force-push, `--all`,
`--mirror` ni publicación de tags.

## Comprobaciones previas a integrar

| Comando en el worktree | Resultado |
| --- | --- |
| `uv run python -m pytest tests -v` | 303 pruebas y 588 subpruebas aprobadas en 9,03 s; 11 avisos heredados de deprecación. |
| `uv run ruff check .` | Correcto. |
| `uv run basedpyright` | 0 errores, 0 advertencias, 0 notas. |
| `git diff --check` | Sin errores. |
| Estado antes de integrar | Limpio; no había cambios locales sin guardar. |

Estas comprobaciones no hicieron consultas reales a Gemini ni repitieron
las mediciones de los bloques.

## Instalación desde un clon limpio de GitHub

Se clonó `main` directamente desde GitHub en una carpeta temporal nueva:

```bash
git clone --branch main --single-branch --no-tags \
  git@github.com:brandonhc33/practica-2-http-autenticada.git <carpeta-temporal>
```

El clon confirmó exactamente el merge `12cca9731556ac82591eb7875dcc8862d0bb7696`.
La comprobación transcurrió el 17-11-2026, entre `03:57:10` y `03:57:31` UTC.
No fue una copia del worktree ni del ZIP: se descargó la rama ya publicada.

Antes de instalar no existían `.env`, `.venv`, `vectorstore/`, `output/rag/`
ni `output/agente/`. Se retiraron las variables de claves y tokens del entorno de
validación y se desactivaron las trazas externas. No se copiaron credenciales ni
la `.venv` del worktree.

`uv sync --locked` instaló 123 paquetes en una `.venv` propia. El intérprete
reportado por pytest fue el del clon, con Python 3.12.13.

Todos los comandos siguientes se ejecutaron desde ese clon:

```bash
uv sync --locked
uv run python -V
uv run python -m pytest tests -v
uv run ruff check .
uv run basedpyright
uv run python -m scripts.indexar_corpus --comparar
git diff --check
git status --short --branch
```

| Comprobación | Resultado |
| --- | --- |
| Instalación | Correcta desde el lock, Python 3.12.13 y entorno nuevo. |
| Suite completa | **303 pruebas y 588 subpruebas aprobadas**, 8,19 s; 11 avisos heredados de deprecación de memoria. |
| Ruff | `All checks passed!` |
| Basedpyright | `0 errors, 0 warnings, 0 notes` |
| Comparación de chunking | Cuatro configuraciones, sin pérdida de caracteres no blancos; recursivo 800/100: 50 documentos y 99 chunks. |
| `git diff --check` | Sin errores. |
| Estado final del clon | Limpio, en `main`, siguiendo `origin/main`. |
| Secretos, índices y runtime | `.env`, `vectorstore/`, `output/rag/` y `output/agente/` seguían ausentes al terminar. |

La suite usa modelos falsos y bloquea conexiones externas. `--comparar` solo
fragmenta el corpus local: **no genera embeddings reales ni consulta Gemini**.
Las evidencias de las llamadas reales anteriores no se modificaron ni repitieron.
Son comprobaciones locales sobre un clon de GitHub, no una ejecución remota de CI.

## Estado de la entrega

La integración, el push solo de `main` y la instalación desde GitHub están
completados. Después se actualizan únicamente documentación y checklist para
registrarlo; no cambia el código validado.

Siguen pendientes la revisión del alumno de las etiquetas y conclusiones y el
envío de la actividad en Skillnest. No se marca una revisión humana como cumplida
solo por autorizar la publicación. Ver el
[checklist de entrega](../../entregas/bloques-24-28.md#evidencias-y-checklist-de-cierre).
