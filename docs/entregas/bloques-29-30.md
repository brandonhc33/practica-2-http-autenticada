# Entrega de bloques 29 y 30 — personalización y actividad core 30

**Estado: implementación, medición y documento de decisión completados; actividades
listas para presentar.** Las etiquetas se propusieron con asistencia de IA y se
revisaron antes de medir. La línea base real tiene 24 respuestas.

Documento de la actividad 30: [decisión de personalización](../arquitectura/decision-personalizacion.md).

Plan y fuentes: [PRD 05](../planes/prd-05-personalizacion-ley-rep.md).
Explicaciones y ejercicios: [guía de estudio](../estudio/bloques-29-30.md).
Evidencias: [resultados conservados](../evidencias/bloques-29-30/README.md).
La API, las chains, el agente y el RAG anteriores no se modifican.

## Entregables y correspondencia

| Actividad | Pide el curso | En este proyecto |
| --- | --- | --- |
| 29, práctica | `dataset_tuning.py` con dataset, balance y validación. | [`scripts/dataset_tuning.py`](../../scripts/dataset_tuning.py), que usa [`src/personalizacion/dataset.py`](../../src/personalizacion/dataset.py) y [`datos/personalizacion/rutas_ley_rep.json`](../../datos/personalizacion/rutas_ley_rep.json): 24 ejemplos, balance 8/9/7, validación y copias rotas. |
| 30, core | `decision.py` y `decision_personalizacion.md` con cuatro secciones. | [`scripts/decision_personalizacion.py`](../../scripts/decision_personalizacion.py) con [`src/personalizacion/decision.py`](../../src/personalizacion/decision.py); documento final en [`decision-personalizacion.md`](../arquitectura/decision-personalizacion.md). |
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

- 24 ejemplos, 0 problemas; balance 8/9/7; 10 copias rotas detectadas.
- La API para desarrolladores rechaza `adapter_size` antes de enviar: PEFT
  requiere Gemini Enterprise Agent Platform.
- La regla local de artículos acierta 22 de 24; fallan «resume art 27» y «Resume el artículo primero».
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

Hace una pausa de 5 segundos entre llamadas. Un error detiene la medición y queda
registrado con lo medido. Una medición incompleta no responde la pregunta de
formato; `--continuar ANTERIOR.json` consulta solo las que faltan y rechaza otro
dataset, prompt, modelo o criterio.

Resultado observado: **3 incumplimientos de 24 (12,5 %)**, formato correcto en las
24, 4.931 tokens y US$ 0,0015981 estimados. Se midió en dos tramos por un límite
de frecuencia; ver [evidencias](../evidencias/bloques-29-30/README.md#b30-línea-base-real).

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
- [x] Revisión de las etiquetas del dataset.
- [x] Confirmación de los hechos del proyecto: intentos de entrenamiento y variantes.
- [x] Línea base real completa, sin copiar ni mostrar credenciales.
- [x] Documento de decisión con cuatro secciones, sensibilidad y números.
- [x] Evidencias reales conservadas con huellas; estado actualizado.
- [x] Revisión del documento de decisión.
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

**Actividad 30, core:** la
[decisión de personalización](../arquitectura/decision-personalizacion.md). El
formulario acepta un archivo (PDF, Word o ZIP) o un enlace; sirve el enlace al
archivo en `main` una vez publicado.
