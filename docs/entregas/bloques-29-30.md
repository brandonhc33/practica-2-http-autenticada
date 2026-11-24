# Entrega de bloques 29 y 30 — personalización y actividad core 30

**Estado: implementación y comprobaciones sin cuota completadas; falta la línea
base con Gemini y redactar la decisión.** El dataset, su validación, la
configuración PEFT, el método de decisión y la medición están implementados y
probados sin red. Las etiquetas fueron propuestas con asistencia de IA y su
revisión figura en el checklist.

Plan y fuentes: [PRD 05](../planes/prd-05-personalizacion-ley-rep.md).
Explicaciones y ejercicios: [guía de estudio](../estudio/bloques-29-30.md).
Evidencias: [resultados conservados](../evidencias/bloques-29-30/README.md).
La API, las chains, el agente y el RAG anteriores no se modifican.

## Entregables y correspondencia

| Actividad | Pide el curso | En este proyecto |
| --- | --- | --- |
| 29, práctica | `dataset_tuning.py` con dataset, balance y validación. | [`scripts/dataset_tuning.py`](../../scripts/dataset_tuning.py), que usa [`src/personalizacion/dataset.py`](../../src/personalizacion/dataset.py) y [`datos/personalizacion/rutas_ley_rep.json`](../../datos/personalizacion/rutas_ley_rep.json): 24 ejemplos, balance 8/8/8, validación y copias rotas. |
| 30, core | `decision.py` y `decision_personalizacion.md` con cuatro secciones. | [`scripts/decision_personalizacion.py`](../../scripts/decision_personalizacion.py) con [`src/personalizacion/decision.py`](../../src/personalizacion/decision.py); documento final en `docs/arquitectura/decision-personalizacion.md`, **pendiente de la línea base**. |
| Evidencia de la pregunta de formato | Revisar 20 respuestas reales con criterios fijos. | [`scripts/linea_base_rutas.py`](../../scripts/linea_base_rutas.py) con [`src/personalizacion/linea_base.py`](../../src/personalizacion/linea_base.py): 24 respuestas del clasificador actual. |

## Recorrido de ejecución

Desde la raíz del proyecto. No hace falta iniciar la API. Cada salida debe ser
**nueva**: si el archivo existe, el comando falla antes de llamar a Gemini.

### 1. Preparación sin cuota

```bash
uv sync --locked
uv run python -m scripts.dataset_tuning --comprobar-validador --comprobar-api
uv run python -m scripts.linea_base_rutas --solo-regla-local
uv run python -m scripts.decision_personalizacion
uv run python -m pytest tests -v
uv run ruff check .
uv run basedpyright
git diff --check
```

Resultados ya observados, sin clave ni red:

- 24 ejemplos, 0 problemas; balance 8/8/8; 10 copias rotas detectadas.
- La API para desarrolladores rechaza `adapter_size` antes de enviar: PEFT
  requiere Gemini Enterprise Agent Platform.
- La regla local de artículos acierta 23 de 24; falla «resume art 27».
- Escenarios del método antes de medir: RAG si el formato incumple menos de 15 %;
  PEFT si incumple 15 % o más.

### 2. Revisión de las etiquetas

Leer las reglas R1 a R3 y las 24 etiquetas del
[dataset](../../datos/personalizacion/rutas_ley_rep.json) **antes** de la línea
base. Si una etiqueta no corresponde a su regla, se corrige ahora: después de
medir, cambiarla para mejorar el resultado contaminaría la evaluación.

Confirmar también dos hechos de
[`hechos_decision.json`](../../datos/personalizacion/hechos_decision.json) que
dependen del proyecto y no del código: cuántos entrenamientos se podrían costear
y cuántas versiones del clasificador hacen falta.

### 3. Línea base real

El comando siguiente **hace 24 llamadas a `gemini-3.5-flash-lite` y consume
cuota**. Requiere `GEMINI_API_KEY` en el entorno o en `.env`:

```bash
uv run python -m scripts.linea_base_rutas --confirmar-consumo \
  --salida output/personalizacion/linea-base-01.json
```

Desde un worktree sin `.env`, se puede cargar el archivo original con
`uv run --env-file /ruta/al/.env python -m scripts.linea_base_rutas ...`.

Un error detiene la medición sin reintentar y queda registrado con lo medido
hasta ese momento. Una medición incompleta no responde la pregunta de formato.

### 4. Documento de decisión

```bash
uv run python -m scripts.decision_personalizacion \
  --linea-base output/personalizacion/linea-base-01.json \
  --salida output/personalizacion/decision-base-01.md
```

El comando rechaza una línea base medida con otra versión del dataset o del
prompt. El documento base trae las secciones 1 y 2 completas, la sensibilidad y
dos marcas `[COMPLETAR]`. Las secciones 3 y 4 se redactan a mano con los
resultados, y el texto final se guarda en `docs/arquitectura/decision-personalizacion.md`.

## Evidencias y checklist de cierre

Lo generado en `output/personalizacion/` es local e ignorado por Git. Solo se
copian a `docs/evidencias/bloques-29-30/` las mediciones reales revisadas.

- [x] Material de los bloques 29 y 30 y sus actividades analizados y planificados.
- [x] Caso de comportamiento elegido y justificado frente a RAG.
- [x] Dataset de 24 ejemplos con reglas de etiquetado, balance y validación.
- [x] Validador comprobado con diez copias rotas a propósito.
- [x] Configuración PEFT construida y rechazo local de la API para desarrolladores comprobado sin red.
- [x] Espera asíncrona y método de decisión probados sin red.
- [x] Regla local de artículos evaluada y escenarios del método registrados antes de medir.
- [x] Suite completa, ruff, basedpyright y ejecutor de unittest.
- [ ] Revisión de las etiquetas del dataset.
- [ ] Confirmación de los hechos del proyecto: intentos de entrenamiento y variantes.
- [ ] Línea base real completa con autorización, sin copiar ni mostrar credenciales.
- [ ] Documento de decisión con cuatro secciones, sensibilidad y números.
- [ ] Evidencias reales revisadas y conservadas; estado actualizado.
- [ ] Ampliación integrada y publicada en `main`, sin publicar la rama de bloques.
- [ ] Instalación desde un clon limpio de GitHub.
- [ ] Presentación de las actividades en Skillnest.

Las comprobaciones de esta versión se detallan en la
[verificación local](../evidencias/bloques-29-30/verificacion-local.md).

## Qué presentar

**Actividad 29, práctica:**
[`scripts/dataset_tuning.py`](../../scripts/dataset_tuning.py), dentro del proyecto,
junto con el [dataset](../../datos/personalizacion/rutas_ley_rep.json) y su
[salida de validación](../evidencias/bloques-29-30/dataset-validacion.txt).

**Actividad 30, core:** el documento de decisión, cuando esté redactado. El
formulario acepta un archivo (PDF, Word o ZIP) o un enlace; sirve el enlace al
archivo en `main` una vez publicado.
