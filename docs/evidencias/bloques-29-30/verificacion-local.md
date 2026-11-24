# Verificación local — bloques 29 y 30

**Alcance:** dataset, validación, método de decisión y mecánica de la línea base
con modelos falsos. La medición real está en el [índice](README.md#b30-línea-base-real). Revisión del
24-11-2026 sobre `c3a4746`, en la rama local `bloques-29-30`, con Python 3.12.13,
`google-genai` 2.34.0 y `langchain-google-genai` 4.4.3.

## Comprobaciones ejecutadas

| Comando | Resultado |
| --- | --- |
| `uv run python -m pytest tests -v` | **346 pruebas y 630 subpruebas aprobadas**; 11 avisos de deprecación de la memoria del agente, ya conocidos. |
| `uv run python -m tests` | **346 pruebas aprobadas**, ejecutor alternativo. |
| `uv run ruff check .` | Sin errores. |
| `uv run basedpyright` | 0 errores, 0 advertencias, 0 notas. |
| `git diff --check` | Sin errores de espacios. |
| `uv run python -m scripts.dataset_tuning --comprobar-validador --comprobar-api` | Sin clave: 0 problemas, 10 copias rotas detectadas, rechazo local de PEFT. |
| `uv run python -m scripts.linea_base_rutas --solo-regla-local` | Sin clave: 22 de 24 artículos detectados. |
| `uv run python -m scripts.linea_base_rutas --salida ...` sin `--confirmar-consumo` | Termina con error antes de crear el modelo o el archivo. |
| `uv run python -m scripts.decision_personalizacion` | Sin clave: respuestas, horas faltantes y escenarios. |
| `git check-ignore output/personalizacion/...` | Ruta ignorada. |

La línea base del repositorio tenía 303 pruebas y 588 subpruebas. Se agregan
**43 pruebas y 42 subpruebas**. No se cambiaron dependencias: `google-genai` ya
estaba instalado como dependencia de `langchain-google-genai`.

## Qué prueban las comprobaciones nuevas

- El dataset real: mínimo de ejemplos, tres rutas, IDs únicos, reglas documentadas
  y salidas JSON con comillas dobles y tildes.
- El validador reproduce el resultado esperado de la lección con su dataset roto
  y detecta las diez copias rotas del proyecto sin modificar el original.
- La configuración PEFT usa tipos reales del SDK; la conversión local la rechaza
  en modo desarrollador sin red. Una configuración sin PEFT no tiene ese rechazo.
- La espera asíncrona consulta con `get`, no con `tune`; termina también con
  `EXPIRED` y avisa al agotar la espera máxima sin cancelar el trabajo.
- El método reproduce los dos casos y la sensibilidad de la lección, rechaza
  textos y `None`, y calcula los costos de etiquetado de la lección.
- Las respuestas derivadas no inventan la de formato sin una línea base completa
  y aplican los umbrales de 15 % y 200 ejemplos.
- La línea base usa el prompt real del B19, separa errores del modelo y de la
  regla local, registra tokens y costo, y se detiene en el primer error. Obedecer
  una consulta que intenta cambiar las instrucciones cuenta como incumplimiento.
- Los comandos no crean modelos sin consentimiento o sin clave, conservan una
  salida existente y rechazan una línea base de otro dataset. Una medición
  interrumpida se continúa sin repetir lo respondido; una terminada, no.

Los modelos y clientes falsos comprueban la mecánica, no la calidad real.
