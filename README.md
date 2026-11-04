# Práctica 2: consultas HTTP autenticadas con Gemini

API local en Python para consultar Gemini con autenticación Bearer, validación de datos, manejo de errores HTTP, reintentos con backoff y cálculo de costos.

**Empieza por [main.py](main.py):** inicia la API desde la raíz del repositorio. Los endpoints están en [src/api/app.py](src/api/app.py) y el cliente HTTP en [src/clientes/gemini.py](src/clientes/gemini.py).

## Índice

- [Inicio rápido](#inicio-rápido)
- [Comandos útiles](#comandos-útiles)
- [Levantar y detener la API](#levantar-y-detener-la-api)
- [Probar la API con curl](#probar-la-api-con-curl)
- [Consultar Gemini desde terminal](#consultar-gemini-desde-terminal)
- [Evaluaciones y ensayos](#evaluaciones-y-ensayos)
- [Pruebas y calidad del código](#pruebas-y-calidad-del-código)
- [Estructura y recorrido de revisión](#estructura-y-recorrido-de-revisión)
- [Documentación y evidencias](#documentación-y-evidencias)

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
├── prompts/            → Banco, instrucciones y contexto documental
├── agentes.py          → Selección y ejecución del agente
└── catalogo.py         → Modelos disponibles
tests/                  → api/, clientes/, costos/, evaluacion/, prompts/ y scripts/
scripts/                → Evaluaciones, ensayos y herramientas auxiliares
docs/                   → Guía, arquitectura y evidencias
datos/                  → Documentos de Ley REP y casos de evaluación
```

Para evaluar el proyecto, comienza ejecutando `/health` y las pruebas. Luego sigue el flujo de código: [entrada](main.py) → [API y autenticación](src/api/app.py) → [selección del agente](src/agentes.py) → [cliente HTTP](src/clientes/gemini.py). Los [errores](src/clientes/errores.py) y los [reintentos](src/clientes/reintentos.py) se mantienen en módulos separados.

Las pruebas siguen las mismas áreas del código; `tests/conftest.py` bloquea la red para toda la suite. Las evaluaciones reales se ejecutan desde `scripts/` y sus resultados se conservan en `docs/evaluaciones/`.

## Documentación y evidencias

- [Guía completa: actividades del curso, comandos y referencia de la API](docs/guia-completa.md).
- [Arquitectura y recorrido de una petición](docs/arquitectura.md).
- [Comparación de modelos y decisión de arquitectura](docs/decision-arquitectura.md).
- [Banco de prompts y salida estructurada](docs/bloque-10-prompts.md).
- [Evaluación de respuestas de Ley REP: bloques 15–17](docs/evaluacion-respuestas.md).
- [Límites de las métricas y hallazgos de la revisión](docs/limites_metrica.md).
- [Entrega de bloques 13 y 14: pruebas, costos y backoff](docs/entrega-bloques-13-14.md).
- [Capturas y resultados de ejecución](docs/evidencias/mis-capturas/README.md).
- [Propuesta del proyecto final: asistente RAG para Ley REP](docs/guia-completa.md#proyecto-final-de-skillnest-asistente-rag-para-ley-rep).
