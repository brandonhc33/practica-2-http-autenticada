# Verificación local — Gate 2

Revisión del 25-11-2026 (UTC) sobre `02fd04f`, en la rama local `gate-2`, con Python 3.12.13.

| Comando | Resultado |
| --- | --- |
| `uv run python -m pytest tests -q` | **453 pruebas y 759 subpruebas aprobadas**; 11 avisos de deprecación ya conocidos. |
| `uv run python -m pytest test_gate2.py -v` | **4 aprobadas**, sin clave. |
| `uv run python -m tests` | **453 aprobadas**, ejecutor alternativo. |
| `uv run ruff check .` y `uv run basedpyright` | Sin errores ni advertencias. |
| `git diff --check` y `uv lock --check` | Sin errores; `requirements.txt` corresponde al bloqueo. |
| Copia en otra carpeta: `python -m venv`, `pip install -r requirements.txt` | Ensayo con 11 comprobaciones correctas y 4 pruebas aprobadas, sin clave. |
| `verificar_entorno.py` en esa copia | Salida 1: pide la clave y el índice, como corresponde. |

La línea base tenía 407 pruebas y 698 subpruebas. Se agregan **46 pruebas y 61 subpruebas**, y
las 4 de `test_gate2.py`. La suite bloquea la red; `test_gate2.py` no llama a Gemini salvo con
`GATE2_REAL=1`.
