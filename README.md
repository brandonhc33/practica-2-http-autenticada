# Práctica 2: consultas HTTP autenticadas con Gemini

API local en Python para consultar Gemini con autenticación Bearer, validación de datos, manejo de errores HTTP, reintentos con backoff y cálculo de costos.

**Empieza por [main.py](main.py):** inicia la API desde la raíz del repositorio. Los endpoints están en [src/api/app.py](src/api/app.py) y el cliente HTTP en [src/clientes/gemini.py](src/clientes/gemini.py).

## Índice

1. [Inicio rápido](#inicio-rápido)
2. [Actividades por bloque](#actividades-por-bloque)
3. [Comandos útiles](#comandos-útiles)
4. [Levantar y detener la API](#levantar-y-detener-la-api)
5. [Probar la API con curl](#probar-la-api-con-curl)
6. [Consultar Gemini desde terminal](#consultar-gemini-desde-terminal)
7. [Orquestar consultas de Ley REP](#orquestar-consultas-de-ley-rep)
8. [Agente con memoria y supervisión](#agente-con-memoria-y-supervisión)
9. [Consultas RAG de Ley REP](#consultas-rag-de-ley-rep)
10. [Personalización del clasificador de rutas](#personalización-del-clasificador-de-rutas)
11. [Observabilidad y gobernanza del RAG](#observabilidad-y-gobernanza-del-rag)
12. [Evaluaciones y ensayos](#evaluaciones-y-ensayos)
13. [Pruebas y calidad del código](#pruebas-y-calidad-del-código)
14. [Estructura y recorrido de revisión](#estructura-y-recorrido-de-revisión)
15. [Guías de estudio](#guías-de-estudio)
16. [Documentación y evidencias](#documentación-y-evidencias)

## Inicio rápido

Necesitas Python 3.12 y `uv`. Si no los tienes, sigue la [instalación](docs/guias/guia-completa.md#instalación).

1. Desde la raíz del repositorio, instala las dependencias:

   ```bash
   uv sync --locked
   ```

2. Si aún no existe `.env`, copia `.env.example` a `.env` (`cp .env.example .env` en Linux/macOS o `Copy-Item .env.example .env` en PowerShell). Completa:

   ```dotenv
   GEMINI_API_KEY=tu_clave_de_google_ai_studio
   API_BEARER_TOKEN=tu_token_local
   ```

   Puedes generar el token con `uv run python -c "import secrets; print(secrets.token_urlsafe(32))"`. [Detalles de configuración](docs/guias/guia-completa.md#configuración).

3. Inicia la API:

   ```bash
   uv run python main.py
   ```

   Escucha en `http://127.0.0.1:8000`. Para desarrollo, añade `--reload`; consulta las opciones con `uv run python main.py --help`.

4. En otra terminal, comprueba la autenticación reemplazando `tu_token_local` por el valor de `.env`:

   ```bash
   curl -H "Authorization: Bearer tu_token_local" http://127.0.0.1:8000/health
   ```

   Debe responder HTTP 200. Sin token o con uno incorrecto responde HTTP 401. Esta comprobación no consulta Gemini. Para enviar preguntas, usa la [guía de peticiones](docs/guias/guia-completa.md#consulta-mediante-la-api-python) o importa [la colección de Postman](api.postman_collection.json).

## Actividades por bloque

Cada fila lleva a la explicación de la actividad y a su entrega o evidencia. El detalle completo está en las [actividades de la guía](docs/guias/guia-completa.md#actividades-del-curso).

| Bloque | Actividad | Dónde revisarla |
| --- | --- | --- |
| 4 | Consulta HTTP autenticada | [Desde Python](docs/guias/guia-completa.md#consultar-gemini-desde-python) y [API local](docs/guias/guia-completa.md#iniciar-la-api-local). |
| 8 | Arquitectura de la aplicación | [Explicación](docs/arquitectura/vision-general.md) y [diagrama](docs/arquitectura/diagramas/flujo-api.png). |
| 9 | Elección de modelo | [Decisión de arquitectura](docs/arquitectura/seleccion-modelo.md). |
| 10 | Prompts con salida JSON | [Guía de prompts](docs/estudio/bloque-10-prompts.md) y [uso del banco](docs/guias/guia-completa.md#banco-de-prompts-y-salida-estructurada-bloque-10). |
| 12 | Cliente con reintentos | [Política de reintentos](docs/guias/guia-completa.md#cliente-con-reintentos-bloque-12). |
| 13 y 14 | Costos, backoff y pruebas unitarias | [Entrega](docs/entregas/bloques-13-14.md) y [capturas](docs/evidencias/mis-capturas/README.md). |
| 15 a 17 | Evaluación de respuestas de Ley REP | [Evaluación y resultados](docs/evaluaciones/respuestas-ley-rep.md). |
| 18 a 20 | Chain, enrutamiento y manejo de errores | [Uso](docs/guias/guia-completa.md#orquestación-con-langchain-bloques-18-a-20), [entrega](docs/entregas/bloques-18-20.md) y [preguntas y respuestas](docs/estudio/bloques-18-20.md). |
| 21 | Agente con herramientas de lectura | [Uso](#agente-con-memoria-y-supervisión) y [entrega y evidencias](docs/entregas/bloques-21-23.md). |
| 22 | Argumentos estructurados y memoria por sesión | [Guía de uso](docs/guias/guia-completa.md#agente-con-herramientas-memoria-y-supervisión-bloques-21-a-23). |
| 23 | Supervisión humana y límites de autonomía | [Límites](docs/arquitectura/limites-autonomia-agente.md) y [estado de validación](docs/entregas/bloques-21-23.md#condiciones-para-marcar-la-entrega-como-cerrada). |
| 24 y 25 | Indexación y persistencia en Chroma | [Uso del RAG](#consultas-rag-de-ley-rep) y [comparación de cortes](docs/evidencias/bloques-24-28/comparacion-chunking.md). |
| 26 y 27 | Recuperación con citas y evaluación | [Recorrido de ejecución](docs/entregas/bloques-24-28.md#recorrido-de-ejecución) y [casos etiquetados](datos/evaluacion/recuperacion_rag.json). |
| 28 | Latencia y costo del flujo RAG | [Actividad core, checklist y estado de evidencias reales](docs/entregas/bloques-24-28.md). |
| 29 | Dataset validado para personalizar un modelo | [Uso](#personalización-del-clasificador-de-rutas), [entrega](docs/entregas/bloques-29-30.md) y [validación](docs/evidencias/bloques-29-30/dataset-validacion.txt). |
| 30 | Decisión fundamentada de personalización | [Documento de decisión](docs/arquitectura/decision-personalizacion.md) y [recorrido y estado](docs/entregas/bloques-29-30.md#recorrido-de-ejecución). |
| 31 | Registros con traza, consumo y filtro de inyección | [Uso](#observabilidad-y-gobernanza-del-rag), [entrega](docs/entregas/bloques-31-32.md) y [salida](docs/evidencias/bloques-31-32/logging-ensayo.txt). |
| 32 | Versiones de prompt, supervisión y matriz de riesgos | [Matriz](docs/arquitectura/matriz-riesgos.md) y [recorrido y estado](docs/entregas/bloques-31-32.md#recorrido-de-ejecución). |

## Comandos útiles

Ejecuta estos comandos desde la raíz del repositorio, después de configurar `.env`.

| Objetivo | Comando |
| --- | --- |
| Instalar dependencias | `uv sync --locked` |
| Iniciar la API | `uv run python main.py` |
| Iniciar con recarga automática | `uv run python main.py --reload` |
| Usar otro puerto | `uv run python main.py --port 8001` |
| Iniciar directamente con Uvicorn | `uv run uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload` |
| Ver opciones de inicio | `uv run python main.py --help` |
| Consultar Gemini | `uv run python -m src.clientes.gemini "¿Qué es una API?"` |
| Orquestar una consulta de Ley REP | `uv run python -m src.orquestacion.enrutamiento "Resume el artículo 9"` |
| Comparar chunking sin API | `uv run python -m scripts.indexar_corpus --comparar` |
| Verificar el índice RAG sin API | `uv run python -m scripts.indexar_corpus --verificar` |
| Validar el dataset de tuning sin API | `uv run python -m scripts.dataset_tuning` |
| Ejecutar pruebas | `uv run python -m pytest tests -v` |
| Revisar estilo | `uv run ruff check .` |
| Revisar tipos | `uv run basedpyright` |

### Levantar y detener la API

Inicio habitual, disponible en `http://127.0.0.1:8000`:

```bash
uv run python main.py
```

Durante el desarrollo, recarga el servidor cuando cambie el código:

```bash
uv run python main.py --reload
```

Para elegir dirección y puerto:

```bash
uv run python main.py --host 127.0.0.1 --port 8001 --reload
```

También puedes iniciar directamente con Uvicorn usando la nueva ruta del módulo:

```bash
uv run uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Ejecuta una sola de estas alternativas. Deja esa terminal abierta y usa otra para las peticiones. Detén el servidor con **Ctrl+C**. Si eliges otro puerto, cámbialo también en las URLs de las peticiones.

### Probar la API con curl

Los siguientes ejemplos usan Bash. Reemplaza `tu_token_local` por el `API_BEARER_TOKEN` de `.env`.

Comprobar disponibilidad con autenticación, sin consultar Gemini:

```bash
curl -i -H "Authorization: Bearer tu_token_local" http://127.0.0.1:8000/health
```

Comprobar el rechazo de una petición sin token (HTTP 401):

```bash
curl -i http://127.0.0.1:8000/health
```

Enviar una pregunta a Gemini a través de la API local:

```bash
curl -X POST http://127.0.0.1:8000/consultar \
  -H "Authorization: Bearer tu_token_local" \
  -H "Content-Type: application/json" \
  -d '{"agente":"gemini","modelo":"flash-lite","mensaje":"¿Qué es una API?"}'
```

La consulta requiere `GEMINI_API_KEY` y consume cuota. Para obtener el JSON original del proveedor, usa el mismo comando con `/consultar/raw`. Las rutas se escriben sin barra final; `/docs` y `/redoc` están deshabilitadas.

### Consultar Gemini desde terminal

Estos comandos consultan directamente al proveedor; requieren `GEMINI_API_KEY` y consumen cuota. No necesitas levantar la API local.

| Objetivo | Comando |
| --- | --- |
| Usar la pregunta de prueba | `uv run python -m src.clientes.gemini` |
| Enviar tu pregunta | `uv run python -m src.clientes.gemini "¿Qué es una API?"` |
| Elegir modelo | `uv run python -m src.clientes.gemini --modelo flash "¿Qué es una API?"` |
| Ver la respuesta original | `uv run python -m src.clientes.gemini --raw "Hola"` |
| Aplicar un prompt estructurado | `uv run python -m src.clientes.gemini --prompt explicar_concepto "¿Qué es una API?"` |
| Limitar intentos y tiempo | `uv run python -m src.clientes.gemini --intentos 1 --presupuesto-segundos 30 "Hola"` |
| Ver todas las opciones | `uv run python -m src.clientes.gemini --help` |

### Orquestar consultas de Ley REP

Flujo de terminal con LangChain de los bloques 18 a 20. Clasifica la consulta y elige una ruta: una pregunta normativa pasa por una chain de tres pasos, un resumen usa el artículo nombrado y cualquier otro caso pide aclaración. Requiere `GEMINI_API_KEY` y consume cuota; no necesitas levantar la API local.

```bash
uv run python -m src.orquestacion.enrutamiento "Resume el artículo 9"
```

La respuesta sale por stdout y el consumo por stderr. Una consulta normativa usa 4 llamadas y las otras rutas 2. Si Gemini falla, el flujo prueba con el modelo secundario y después entrega un texto de respaldo. Consulta la [guía de uso](docs/guias/guia-completa.md#orquestación-con-langchain-bloques-18-a-20).

### Agente con memoria y supervisión

Entrada adicional de los bloques 21 a 23: el modelo elige herramientas para leer la
ley y recuerda los turnos de una sesión dentro del mismo proceso. Requiere
`GEMINI_API_KEY` y consume cuota; no reemplaza la API ni el flujo anterior.

Si ejecutas desde un worktree, el `.env` ignorado de tu carpeta original no se
copia automáticamente. Puedes cargarlo para ese comando con
`uv run --env-file /ruta/a/tu/.env python -m ...`, sin copiar ni compartir la clave.

```bash
uv run python -m src.orquestacion.agente_con_herramientas --sesion cliente-1 \
  "¿Qué establece el artículo primero transitorio de la Ley REP?" \
  "¿Y qué dice el artículo transitorio siguiente?"
```

Una entrega de informe solo guarda un archivo local después de mostrar su contenido
y recibir `s` de una persona en una terminal interactiva. Nunca envía informes a
destinatarios reales. Las trazas, decisiones e informes quedan en `output/agente/`,
ignorado por Git. Para revisar repeticiones, sin llamar a Gemini:

```bash
uv run python -m src.orquestacion.supervision
```

Consulta la [guía](docs/guias/guia-completa.md#agente-con-herramientas-memoria-y-supervisión-bloques-21-a-23),
los [límites](docs/arquitectura/limites-autonomia-agente.md) y el
[estado de validación y evidencias](docs/entregas/bloques-21-23.md).

### Consultas RAG de Ley REP

Entrada de terminal de los bloques 24–28: índice Chroma persistente de la copia
local de 2016, recuperación semántica y respuesta con fuentes numeradas. No
reemplaza la API ni el agente anterior. La implementación se puede probar sin red;
las [mediciones reales de la actividad 28](docs/entregas/bloques-24-28.md) ya están
registradas y la ampliación está publicada en `main`. El envío a la plataforma
sigue pendiente.

Preparación local, sin cuota:

```bash
uv run python -m scripts.indexar_corpus --comparar
```

Indexar una vez y consultar **sí consume cuota** y requiere `GEMINI_API_KEY`:

```bash
uv run python -m scripts.indexar_corpus --confirmar-consumo \
  --salida output/rag/indexacion-01.json

uv run python -m scripts.registro_rag \
  "¿Qué productos prioritarios enumera la ley?" \
  --salida output/rag/consulta-01.jsonl --confirmar-consumo
```

El índice queda en `vectorstore/` y las consultas completas en `output/rag/`,
ambos ignorados por Git. Las salidas deben ser nuevas; no se sobrescriben. No
introducir datos privados. El programa comprueba números de cita, no el respaldo
semántico de cada afirmación. Los tokens de embeddings no informados permanecen
desconocidos; no se presenta el costo de generación como costo total.

Consulta los comandos de [evaluación y actividad 28](docs/entregas/bloques-24-28.md#recorrido-de-ejecución)
y la [guía de estudio](docs/estudio/bloques-24-28.md).

### Personalización del clasificador de rutas

Entrada de terminal de los bloques 29 y 30. Prepara y valida un dataset para
personalizar el clasificador de rutas del bloque 19 y aplica un método para
decidir si conviene entrenarlo. **No entrena ningún modelo:** la API para
desarrolladores de Gemini no admite PEFT, y el comando lo comprueba sin red.

Sin cuota ni clave:

```bash
uv run python -m scripts.dataset_tuning --comprobar-validador --comprobar-api
uv run python -m scripts.linea_base_rutas --solo-regla-local
uv run python -m scripts.decision_personalizacion
```

Medir el clasificador actual **sí consume cuota**: 24 llamadas a
`gemini-3.5-flash-lite`.

```bash
uv run python -m scripts.linea_base_rutas --confirmar-consumo \
  --salida output/personalizacion/linea-base-01.json
```

Las salidas quedan en `output/personalizacion/`, ignorado por Git. Consulta el
[recorrido y el estado de la entrega](docs/entregas/bloques-29-30.md) y la
[guía de estudio](docs/estudio/bloques-29-30.md).

### Observabilidad y gobernanza del RAG

Entrada de terminal de los bloques 31 y 32. Responde con el RAG dejando eventos JSON
con `trace_id`, sin la pregunta ni la respuesta; descarta fragmentos con instrucciones
sospechosas y no entrega texto sin citas. Activar otra versión del prompt requiere una
decisión humana.

Sin cuota ni clave:

```bash
uv run python -m scripts.logging_rag
uv run python -m scripts.registro_prompts
uv run python -m scripts.grafo_supervision demo
uv run python -m scripts.matriz_riesgos
```

Una consulta real **sí consume cuota** y necesita el índice en `vectorstore/`:

```bash
uv run python -m scripts.logging_rag --confirmar-consumo \
  --registro output/observabilidad/eventos-01.jsonl \
  --consultar "¿Qué es un productor de un producto prioritario?"
```

El filtro reconoce frases conocidas y una cita existente no prueba que la respuesta sea
fiel. Consulta el [recorrido y el estado](docs/entregas/bloques-31-32.md), la
[matriz de riesgos](docs/arquitectura/matriz-riesgos.md) y la
[guía de estudio](docs/estudio/bloques-31-32.md).

### Evaluaciones y ensayos

Comparar modelos y evaluar prompts realiza consultas reales a Gemini. El ensayo con `--simulado` no usa red ni consume tokens. Elige un archivo de salida nuevo en cada ejecución para conservar las evidencias anteriores.

| Objetivo | Comando |
| --- | --- |
| Listar modelos accesibles, sin generar texto | `uv run python -m scripts.comparar_modelos --listar-modelos` |
| Comparar costo y latencia | `uv run python -m scripts.comparar_modelos --repeticiones 3 --salida docs/evaluaciones/gemini-nueva-ejecucion.json` |
| Evaluar consistencia de prompts | `uv run python -m scripts.evaluar_prompts --salida docs/evaluaciones/prompts-nueva-ejecucion.json` |
| Simular HTTP 429 y backoff | `uv run python -m scripts.ensayo_rate_limit --simulado --salida docs/evidencias/ensayo-nuevo.json` |

Para el ensayo contra el proveedor, consulta los [límites y comandos del ensayo real](docs/guias/guia-completa.md#ensayo-real-de-http-429).

### Pruebas y calidad del código

| Objetivo | Comando |
| --- | --- |
| Ejecutar toda la suite sin conexiones externas | `uv run python -m pytest tests -v` |
| Ejecutar solo las pruebas de la API | `uv run python -m pytest tests/api -v` |
| Ejecutar solo las pruebas del cliente HTTP | `uv run python -m pytest tests/clientes -v` |
| Ejecutar solo las pruebas de costos | `uv run python -m pytest tests/costos -v` |
| Ejecutar solo las pruebas de orquestación | `uv run python -m pytest tests/orquestacion -v` |
| Ejecutar solo las pruebas del RAG | `uv run python -m pytest tests/rag -v` |
| Ejecutar solo las pruebas de personalización | `uv run python -m pytest tests/personalizacion -v` |
| Ejecutar solo las pruebas de observabilidad y gobernanza | `uv run python -m pytest tests/observabilidad tests/gobernanza -v` |
| Ejecutar solo las pruebas de prompts | `uv run python -m pytest tests/prompts -v` |
| Ejecutar solo las pruebas de scripts | `uv run python -m pytest tests/scripts -v` |
| Usar el ejecutor alternativo de unittest | `uv run python -m tests -v` |
| Revisar estilo y errores de código | `uv run ruff check .` |
| Revisar tipos | `uv run basedpyright` |

## Estructura y recorrido de revisión

```text
main.py                 → Inicio de la API
src/
├── api/                → Endpoints, autenticación y esquemas
├── clientes/           → Gemini, errores, reintentos y salida JSON
├── evaluacion/         → Pipeline de texto y métricas léxicas
├── costos/             → Cálculo, registro de sesión y tipo de cambio
├── orquestacion/       → Chain, rutas y fallbacks con LangChain
├── rag/                → Índice Chroma, recuperación, citas, mediciones y servicio auditable
├── personalizacion/    → Dataset de tuning, línea base y método de decisión
├── observabilidad/     → Eventos JSON, trazas y filtro de inyección
├── gobernanza/         → Versiones de prompt, supervisión y riesgos
├── prompts/            → Banco, instrucciones y contexto documental
├── agentes.py          → Selección y ejecución del agente
└── catalogo.py         → Modelos disponibles
tests/                  → api/, clientes/, costos/, evaluacion/, orquestacion/, rag/, personalizacion/, observabilidad/, gobernanza/, prompts/ y scripts/
scripts/                → Evaluaciones, ensayos y herramientas auxiliares
docs/                   → Guía, arquitectura y evidencias
datos/                  → Ley REP, casos de evaluación, dataset de personalización, prompts y riesgos
```

Para evaluar el proyecto, comienza ejecutando `/health` y las pruebas. Luego sigue el flujo de código: [entrada](main.py) → [API y autenticación](src/api/app.py) → [selección del agente](src/agentes.py) → [cliente HTTP](src/clientes/gemini.py). Los [errores](src/clientes/errores.py) y los [reintentos](src/clientes/reintentos.py) se mantienen en módulos separados.

Las pruebas siguen las mismas áreas del código; `tests/conftest.py` bloquea la red para toda la suite. Las evaluaciones reales se ejecutan desde `scripts/` y sus resultados se conservan en `docs/evaluaciones/`.

## Guías de estudio

Las explicaciones conceptuales, la relación con las actividades y las preguntas
de repaso están separadas de la documentación de uso:

- [Glosario: términos, para qué sirven, ejemplos cotidianos y diagramas](docs/estudio/glosario.md#cómo-usar-este-glosario).
  Si el vocabulario es nuevo, empieza por sus diez conceptos iniciales y consulta
  el resto por tema mientras lees las guías.
- [Empieza aquí: mapa del módulo 2 desde el bloque 18](docs/estudio/modulo-2-desde-bloque-18.md).
  Conecta las etapas, compara una misma consulta en router, agente y RAG, y propone
  un orden de lectura con ejercicios sin Gemini.
- [Bloque 10: prompts y salida JSON](docs/estudio/bloque-10-prompts.md).
- [Bloques 18 a 20: chains, enrutamiento y manejo de errores](docs/estudio/bloques-18-20.md).
- [Bloques 21 a 23: herramientas, memoria y supervisión humana](docs/estudio/bloques-21-23.md).
- [Bloques 24 a 28: RAG, recuperación con citas, evaluación, latencia y costo](docs/estudio/bloques-24-28.md).
- [Bloques 29 y 30: RAG, fine-tuning, PEFT y cómo decidir si personalizar](docs/estudio/bloques-29-30.md).
- [Bloques 31 y 32: registros, inyección de prompt, supervisión y riesgos](docs/estudio/bloques-31-32.md).

## Documentación y evidencias

La documentación está organizada por propósito y conectada por bloques en el
[índice de `docs/`](docs/README.md).

- [Guía de uso, comandos y referencia de la API](docs/guias/guia-completa.md).
- [Arquitectura, modelos y límites](docs/arquitectura/vision-general.md).
- [Evaluación de respuestas y límites de métricas](docs/evaluaciones/respuestas-ley-rep.md).
- [Planes y decisiones: PRD 04 del RAG](docs/planes/prd-04-rag-ley-rep.md),
  [PRD 05 de personalización](docs/planes/prd-05-personalizacion-ley-rep.md) y
  [PRD 07 de observabilidad y gobernanza](docs/planes/prd-07-observabilidad-gobernanza.md).
- [Entrega 13–14](docs/entregas/bloques-13-14.md), [18–20](docs/entregas/bloques-18-20.md),
  [21–23](docs/entregas/bloques-21-23.md), [24–28 con evidencias reales](docs/entregas/bloques-24-28.md),
  [29–30](docs/entregas/bloques-29-30.md) y [31–32](docs/entregas/bloques-31-32.md).
- [Capturas de terminal conservadas](docs/evidencias/mis-capturas/README.md).
- [Proyecto final: asistente RAG para Ley REP](docs/guias/guia-completa.md#proyecto-final-de-skillnest-asistente-rag-para-ley-rep).
