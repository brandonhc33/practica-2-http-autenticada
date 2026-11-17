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
   - [Consultas RAG de Ley REP](#consultas-rag-de-ley-rep)
9. [Evaluaciones y ensayos](#evaluaciones-y-ensayos)
10. [Pruebas y calidad del código](#pruebas-y-calidad-del-código)
11. [Estructura y recorrido de revisión](#estructura-y-recorrido-de-revisión)
12. [Guías de estudio](#guías-de-estudio)
13. [Documentación y evidencias](#documentación-y-evidencias)

## Inicio rápido

Necesitas Python 3.12 y `uv`. Si no los tienes, sigue la [instalación](docs/guia-completa.md#instalación).

1. Desde la raíz del repositorio, instala las dependencias:

   ```bash
   uv sync --locked
   ```

2. Si aún no existe `.env`, copia `.env.example` a `.env` (`cp .env.example .env` en Linux/macOS o `Copy-Item .env.example .env` en PowerShell). Completa:

   ```dotenv
   GEMINI_API_KEY=tu_clave_de_google_ai_studio
   API_BEARER_TOKEN=tu_token_local
   ```

   Puedes generar el token con `uv run python -c "import secrets; print(secrets.token_urlsafe(32))"`. [Detalles de configuración](docs/guia-completa.md#configuración).

3. Inicia la API:

   ```bash
   uv run python main.py
   ```

   Escucha en `http://127.0.0.1:8000`. Para desarrollo, añade `--reload`; consulta las opciones con `uv run python main.py --help`.

4. En otra terminal, comprueba la autenticación reemplazando `tu_token_local` por el valor de `.env`:

   ```bash
   curl -H "Authorization: Bearer tu_token_local" http://127.0.0.1:8000/health
   ```

   Debe responder HTTP 200. Sin token o con uno incorrecto responde HTTP 401. Esta comprobación no consulta Gemini. Para enviar preguntas, usa la [guía de peticiones](docs/guia-completa.md#consulta-mediante-la-api-python) o importa [la colección de Postman](api.postman_collection.json).

## Actividades por bloque

Cada fila lleva a la explicación de la actividad y a su entrega o evidencia. El detalle completo está en las [actividades de la guía](docs/guia-completa.md#actividades-del-curso).

| Bloque | Actividad | Dónde revisarla |
| --- | --- | --- |
| 4 | Consulta HTTP autenticada | [Desde Python](docs/guia-completa.md#consultar-gemini-desde-python) y [API local](docs/guia-completa.md#iniciar-la-api-local). |
| 8 | Arquitectura de la aplicación | [Explicación](docs/arquitectura.md) y [diagrama](docs/diagrama_arquitectura.png). |
| 9 | Elección de modelo | [Decisión de arquitectura](docs/decision-arquitectura.md). |
| 10 | Prompts con salida JSON | [Guía de prompts](docs/bloque-10-prompts.md) y [uso del banco](docs/guia-completa.md#banco-de-prompts-y-salida-estructurada-bloque-10). |
| 12 | Cliente con reintentos | [Política de reintentos](docs/guia-completa.md#cliente-con-reintentos-bloque-12). |
| 13 y 14 | Costos, backoff y pruebas unitarias | [Entrega](docs/entrega-bloques-13-14.md) y [capturas](docs/evidencias/mis-capturas/README.md). |
| 15 a 17 | Evaluación de respuestas de Ley REP | [Evaluación y resultados](docs/evaluacion-respuestas.md). |
| 18 a 20 | Chain, enrutamiento y manejo de errores | [Uso](docs/guia-completa.md#orquestación-con-langchain-bloques-18-a-20), [entrega](docs/entrega-bloques-18-20.md) y [preguntas y respuestas](docs/preguntas-bloques-18-20.md). |
| 21 | Agente con herramientas de lectura | [Uso](#agente-con-memoria-y-supervisión) y [entrega y evidencias](docs/entrega-bloques-21-23.md). |
| 22 | Argumentos estructurados y memoria por sesión | [Guía de uso](docs/guia-completa.md#agente-con-herramientas-memoria-y-supervisión-bloques-21-a-23). |
| 23 | Supervisión humana y límites de autonomía | [Límites](docs/limites-autonomia-agente.md) y [estado de validación](docs/entrega-bloques-21-23.md#condiciones-para-marcar-la-entrega-como-cerrada). |
| 24 y 25 | Indexación y persistencia en Chroma | [Uso del RAG](#consultas-rag-de-ley-rep) y [comparación de cortes](docs/evidencias/bloques-24-28/comparacion-chunking.md). |
| 26 y 27 | Recuperación con citas y evaluación | [Recorrido de ejecución](docs/entrega-bloques-24-28.md#recorrido-de-ejecución) y [casos etiquetados](datos/evaluacion/recuperacion_rag.json). |
| 28 | Latencia y costo del flujo RAG | [Actividad core, checklist y estado de evidencias reales](docs/entrega-bloques-24-28.md). |

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

La respuesta sale por stdout y el consumo por stderr. Una consulta normativa usa 4 llamadas y las otras rutas 2. Si Gemini falla, el flujo prueba con el modelo secundario y después entrega un texto de respaldo. Consulta la [guía de uso](docs/guia-completa.md#orquestación-con-langchain-bloques-18-a-20).

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

Consulta la [guía](docs/guia-completa.md#agente-con-herramientas-memoria-y-supervisión-bloques-21-a-23),
los [límites](docs/limites-autonomia-agente.md) y el
[estado de validación y evidencias](docs/entrega-bloques-21-23.md).

### Consultas RAG de Ley REP

Entrada de terminal de los bloques 24–28: índice Chroma persistente de la copia
local de 2016, recuperación semántica y respuesta con fuentes numeradas. No
reemplaza la API ni el agente anterior. La implementación se puede probar sin red;
el [cierre de la actividad 28](docs/entrega-bloques-24-28.md) requiere evidencias
reales todavía pendientes.

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

Consulta los comandos de [evaluación y actividad 28](docs/entrega-bloques-24-28.md#recorrido-de-ejecución)
y la [guía de estudio](docs/preguntas-bloques-24-28.md).

### Evaluaciones y ensayos

Comparar modelos y evaluar prompts realiza consultas reales a Gemini. El ensayo con `--simulado` no usa red ni consume tokens. Elige un archivo de salida nuevo en cada ejecución para conservar las evidencias anteriores.

| Objetivo | Comando |
| --- | --- |
| Listar modelos accesibles, sin generar texto | `uv run python -m scripts.comparar_modelos --listar-modelos` |
| Comparar costo y latencia | `uv run python -m scripts.comparar_modelos --repeticiones 3 --salida docs/evaluaciones/gemini-nueva-ejecucion.json` |
| Evaluar consistencia de prompts | `uv run python -m scripts.evaluar_prompts --salida docs/evaluaciones/prompts-nueva-ejecucion.json` |
| Simular HTTP 429 y backoff | `uv run python -m scripts.ensayo_rate_limit --simulado --salida docs/evidencias/ensayo-nuevo.json` |

Para el ensayo contra el proveedor, consulta los [límites y comandos del ensayo real](docs/guia-completa.md#ensayo-real-de-http-429).

### Pruebas y calidad del código

| Objetivo | Comando |
| --- | --- |
| Ejecutar toda la suite sin conexiones externas | `uv run python -m pytest tests -v` |
| Ejecutar solo las pruebas de la API | `uv run python -m pytest tests/api -v` |
| Ejecutar solo las pruebas del cliente HTTP | `uv run python -m pytest tests/clientes -v` |
| Ejecutar solo las pruebas de costos | `uv run python -m pytest tests/costos -v` |
| Ejecutar solo las pruebas de orquestación | `uv run python -m pytest tests/orquestacion -v` |
| Ejecutar solo las pruebas del RAG | `uv run python -m pytest tests/rag -v` |
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
├── rag/                → Índice Chroma, recuperación, citas y mediciones
├── prompts/            → Banco, instrucciones y contexto documental
├── agentes.py          → Selección y ejecución del agente
└── catalogo.py         → Modelos disponibles
tests/                  → api/, clientes/, costos/, evaluacion/, orquestacion/, rag/, prompts/ y scripts/
scripts/                → Evaluaciones, ensayos y herramientas auxiliares
docs/                   → Guía, arquitectura y evidencias
datos/                  → Documentos de Ley REP y casos de evaluación
```

Para evaluar el proyecto, comienza ejecutando `/health` y las pruebas. Luego sigue el flujo de código: [entrada](main.py) → [API y autenticación](src/api/app.py) → [selección del agente](src/agentes.py) → [cliente HTTP](src/clientes/gemini.py). Los [errores](src/clientes/errores.py) y los [reintentos](src/clientes/reintentos.py) se mantienen en módulos separados.

Las pruebas siguen las mismas áreas del código; `tests/conftest.py` bloquea la red para toda la suite. Las evaluaciones reales se ejecutan desde `scripts/` y sus resultados se conservan en `docs/evaluaciones/`.

## Guías de estudio

Las explicaciones conceptuales, la relación con las actividades y las preguntas
de repaso están separadas de la documentación de uso:

- [Bloques 18 a 20: chains, enrutamiento y manejo de errores](docs/preguntas-bloques-18-20.md).
- [Bloques 21 a 23: herramientas, memoria y supervisión humana](docs/preguntas-bloques-21-23.md).
- [Bloques 24 a 28: RAG, recuperación con citas, evaluación, latencia y costo](docs/preguntas-bloques-24-28.md).

## Documentación y evidencias

- [Guía completa: actividades del curso, comandos y referencia de la API](docs/guia-completa.md).
- [Arquitectura y recorrido de una petición](docs/arquitectura.md).
- [Comparación de modelos y decisión de arquitectura](docs/decision-arquitectura.md).
- [Banco de prompts y salida estructurada](docs/bloque-10-prompts.md).
- [Evaluación de respuestas de Ley REP: bloques 15–17](docs/evaluacion-respuestas.md).
- [Límites de las métricas y hallazgos de la revisión](docs/limites_metrica.md).
- [Entrega de bloques 13 y 14: pruebas, costos y backoff](docs/entrega-bloques-13-14.md).
- [PRD 02: orquestación de consultas con LangChain](docs/prd-02-orquestacion-langchain.md).
- [Entrega de bloques 18 a 20: resultados y límites de la orquestación](docs/entrega-bloques-18-20.md).
- [Agente de Ley REP: entrega y evidencias de los bloques 21 a 23](docs/entrega-bloques-21-23.md).
- [Límites de autonomía y supervisión humana](docs/limites-autonomia-agente.md).
- [PRD 04: plan y decisiones del RAG de Ley REP](docs/prd-04-rag-ley-rep.md).
- [Bloques 24 a 28: entrega y evidencias pendientes de la actividad core 28](docs/entrega-bloques-24-28.md).
- [Capturas y resultados de ejecución](docs/evidencias/mis-capturas/README.md).
- [Propuesta del proyecto final: asistente RAG para Ley REP](docs/guia-completa.md#proyecto-final-de-skillnest-asistente-rag-para-ley-rep).
