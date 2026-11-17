# Publicación e instalación desde GitHub — bloques 21 a 23

## Resultado

**Entrega integrada y publicada en `main`, con instalación y pruebas verificadas
desde un clon real de GitHub.** La publicación fue autorizada por el alumno.
La rama `bloques-21-23` se conservó local; no se creó su referencia en GitHub.

| Referencia | Valor |
| --- | --- |
| Repositorio | `git@github.com:brandonhc33/practica-2-http-autenticada.git` |
| Destino publicado | [main](https://github.com/brandonhc33/practica-2-http-autenticada/tree/main) |
| Rama integrada | `bloques-21-23`, en `abc3db8c07b232058b98be75f09302938a70fde1` |
| Commit de merge verificado | [`c12107822a9df787cf8fb8364ce69d11c0ff396a`](https://github.com/brandonhc33/practica-2-http-autenticada/commit/c12107822a9df787cf8fb8364ce69d11c0ff396a) |
| Python del clon | 3.12.13 |
| Entorno del clon | `.venv` nueva, sin copiar la del worktree |
| Credenciales | Sin `.env` ni claves reales disponibles para la validación |

Este registro se agrega después del merge mediante un cambio de documentación en
`main`. La referencia anterior identifica el código instalado y probado, no el
hash del propio registro.

## Integración y publicación

Se revisaron los remotos antes de publicar. `origin` apunta a GitHub; `local`
apunta al checkout original y no se utilizó para el push.

La rama remota `main` era antecesora de los bloques, por lo que no hubo conflictos.
Se realizó un merge explícito, sin reescribir el historial:

```bash
git switch main
GIT_EDITOR=true git merge --no-ff bloques-21-23 -m "Integrar los bloques 21 a 23 en main"
git diff --exit-code bloques-21-23 HEAD
git -c push.followTags=false push origin refs/heads/main:refs/heads/main
git ls-remote --heads origin
```

La comparación entre el árbol del merge y la rama integrada no encontró cambios.
El remoto confirmó `c12107822a9df787cf8fb8364ce69d11c0ff396a` en
`refs/heads/main`. Antes y después de esta publicación, `main` era la única rama
remota. No se usó `--all`, `--mirror`, force-push ni publicación de tags.

Los commits de los bloques forman parte del historial de `main`; lo que queda
exclusivamente local es la referencia de la rama de trabajo.

## Clon limpio y entorno independiente

Se clonó `main` directamente desde GitHub en una carpeta temporal nueva:

```bash
git clone --branch main --single-branch --no-tags git@github.com:brandonhc33/practica-2-http-autenticada.git <carpeta-temporal>
```

Antes de instalar se comprobó que no existían `.env`, `.venv` ni `output/agente/`.
Se retiraron del entorno de esa comprobación las claves del proveedor y el token
local, y se desactivaron las trazas externas. No se modificó la configuración del
usuario ni se copiaron secretos.

`uv sync --locked` creó la `.venv` propia del clon e instaló **66 paquetes** según
el lockfile. Se comprobó que el intérprete correspondía a esa `.venv`, no a la del
worktree original.

## Comandos ejecutados y resultados

Todos se ejecutaron desde el clon:

```bash
uv sync --locked
uv run python -m pytest tests -v
uv run ruff check .
uv run basedpyright
git diff --check
git status --short --branch
```

| Comprobación | Resultado |
| --- | --- |
| Instalación | Correcta; Python 3.12.13 y entorno nuevo. |
| Suite completa | 263 pruebas y 481 subpruebas aprobadas; 11 avisos de deprecación de la memoria. |
| `ruff` | `All checks passed!` |
| `basedpyright` | `0 errors, 0 warnings, 0 notes` |
| `git diff --check` | Sin errores. |
| Estado del clon | Limpio, en `main`, siguiendo `origin/main`. |
| Archivos privados o de operación | Sin `.env` y sin `output/agente/` también después de las pruebas. |

La suite bloquea las conexiones externas. No se hizo ninguna consulta a Gemini,
no se consumieron tokens ni se autorizó una entrega de informe.
Estas son comprobaciones locales sobre un clon real de GitHub, no una ejecución
de CI remota.

## Cierre de la actividad

Esta comprobación sí satisface la instalación desde GitHub de la Fase 4. La
[verificación local anterior](verificacion-local.md) se conserva como evidencia
histórica y complementaria, no se cambia su procedencia.

Junto con el [rechazo explícito con Gemini](rechazo-explicito-gemini.md) y los
ensayos conservados de los bloques 21 y 22, completa los puntos del
[checklist de entrega](../../entregas/bloques-21-23.md#condiciones-para-marcar-la-entrega-como-cerrada).
Los límites funcionales documentados siguen vigentes: entrega simulada, memoria
no persistente, búsqueda léxica y ausencia de validación automática de citas.
