# Verificación local de los bloques 21 a 23

- **Fecha:** 16 de noviembre de 2026.
- **Código verificado:** commit `4557845` (`Agregar supervisión humana y trazas al agente`).
- **Entorno:** Linux, Python 3.12.13, pytest 9.2.0.
- **Alcance:** ejecución sin llamadas reales a Gemini; no se aprobó ningún informe real.

## Línea base de la Fase 2

Antes de agregar supervisión se ejecutaron:

```text
uv sync --locked
uv run python -m pytest tests -v
uv run ruff check .
uv run basedpyright
git diff --check
```

Resultado: **233 pruebas y 464 subpruebas aprobadas**, 10 avisos de deprecación de
LangChain; `ruff`, `basedpyright` y `git diff --check` sin errores. La Fase 2 se
guardó en el commit `e301894`.

## Código con supervisión

Comprobaciones ejecutadas desde el worktree:

| Comando | Resultado |
| --- | --- |
| `uv run python -m pytest tests -v` | 258 pruebas y 476 subpruebas aprobadas; 11 avisos de deprecación. |
| `uv run python -m tests -v` | 258 pruebas, `OK`. Ejecutor alternativo; el bloqueo de red de pytest no se aplica a este comando. |
| `uv run ruff check .` | `All checks passed!` |
| `uv run basedpyright` | `0 errors, 0 warnings, 0 notes` |
| `git diff --check` | Salida vacía, código 0. |
| `uv run python -m src.orquestacion.agente_con_herramientas --help` | Ayuda disponible con `--sesion`. |
| `uv run python -m scripts.ensayo_agente --help` | Bloques disponibles: `{21,22,23}`. |
| `uv run python -m src.orquestacion.supervision --help` | Ayuda disponible con `--trazas`. |
| `grep -n "esperar_aprobacion(" src/orquestacion/herramientas.py` | Encuentra el control dentro de `entregar_informe`. |

Extracto de la suite completa:

```text
collected 258 items
258 passed, 11 warnings, 476 subtests passed in 2.16s
```

Los tiempos son datos de esta máquina, no un benchmark. Los avisos proceden de
`RunnableWithMessageHistory` e `InMemoryChatMessageHistory`; no se suprimieron.
Las pruebas nuevas cubren decisiones simuladas, timeout, EOF, cancelación,
errores, entrada no interactiva, JSONL, repeticiones y fallos después de entregar.
Los registros y los informes de prueba se aíslan en carpetas temporales tanto con
pytest como con unittest. No se generaron archivos en `output/agente/`.

## Instalación limpia local complementaria

Se extrajo `git archive HEAD` del commit `4557845` en una carpeta temporal nueva,
sin `.git`, `.env`, `.venv` ni archivos locales de operación, y se ejecutó allí:

```bash
uv sync --locked
uv run python -m pytest tests -v
uv run ruff check .
uv run basedpyright
```

`uv` creó una `.venv` nueva e instaló 66 paquetes según el lockfile. Emitió un
aviso de que no podía usar hardlinks entre los sistemas de archivos y copió los
paquetes; la instalación terminó con código 0.

Resultado:

```text
collected 258 items
258 passed, 11 warnings, 476 subtests passed in 2.79s
All checks passed!
0 errors, 0 warnings, 0 notes
```

Esto demuestra instalación y pruebas desde los archivos versionados, sin depender
del entorno del worktree. **No sustituye el clonado desde GitHub** solicitado por
la Fase 4: no hubo push ni se comprobó una publicación remota.

## Lo que no se ejecutó durante esta verificación de código

- Ensayo real del Bloque 23: requiere las decisiones del alumno en su terminal.
- Captura de trazas y aprobaciones humanas de ese ensayo.
- Nuevas corridas de los bloques 21 y 22 con el prompt final.
- Push, merge o clonado desde GitHub.

Los resultados reales anteriores de 21 y 22 se conservan sin modificarlos. El
[estado de entrega](../../entrega-bloques-21-23.md) mantiene pendientes los pasos que
no se han comprobado.

Posteriormente el alumno ejecutó dos intentos reales de 23 y una prueba local de
entrada. Sus resultados, las decisiones y los límites de lo que demuestran se
registran aparte en [la revisión del Bloque 23](revision-bloque-23.md).
