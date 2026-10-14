# Primera petición HTTP autenticada

Actividad del Bloque 4 de Skillnest. Una consulta a Gemini usando `requests`, una clave en `.env` y un entorno propio con `uv`.

## Preparar el proyecto

Necesitas Python 3.12 y [uv](https://docs.astral.sh/uv/getting-started/installation/).

Desde la carpeta del proyecto:

```bash
uv sync --locked
cp .env.example .env
```

En PowerShell, la copia se hace con `Copy-Item .env.example .env`.

Abre `.env` y completa `GEMINI_API_KEY` con tu clave de [Google AI Studio](https://aistudio.google.com/api-keys). Puedes dejar el modelo que viene configurado:

```dotenv
GEMINI_API_KEY=tu_clave_real
GEMINI_MODEL=gemini-3.5-flash-lite
```

`.env` y `.venv/` están excluidos de Git. `.env.example` se sube sin la clave.

## Hacer una consulta

```bash
uv run python src/peticion_gemini.py "¿Qué es una variable de entorno? Responde brevemente."
```

Si ejecutas `uv run python src/peticion_gemini.py` sin pregunta, el programa te la pide en la terminal. Cada ejecución hace una consulta independiente. Se necesita conexión a Internet.

La clave se lee desde `.env` y se envía en el encabezado `x-goog-api-key`. La terminal muestra el código HTTP, el modelo y el texto generado. No hace falta activar `.venv`: `uv run` usa el entorno del proyecto.

## Guardar la evidencia

```bash
uv run python src/peticion_gemini.py "Hola, confirma en una frase que puedes responder esta consulta." --guardar-evidencia
```

Si la petición devuelve HTTP 200 y texto generado, se guarda `docs/evidencia_peticion_autenticada.json`. Incluye la fecha UTC, el método, el endpoint, el código HTTP, la pregunta y la respuesta. No guarda la clave ni los encabezados. Repetir este comando reemplaza esa evidencia.

Para guardar una segunda consulta en otro archivo:

```bash
uv run python src/peticion_gemini.py "¿Para qué sirve un archivo .gitignore? Responde en una frase." --guardar-evidencia docs/evidencia_segunda_peticion.json
```

## Probar con Yaak o Postman

1. Importa `gemini.postman_collection.json`. En Yaak, usa **Import Data** y selecciona el archivo.
2. Configura en el cliente una variable local `GEMINI_API_KEY` con el valor de tu `.env`. La colección del repositorio deja ese valor vacío y no lee `.env` automáticamente.
3. Abre **Consultar Gemini**, revisa el cuerpo y envía la petición.
4. Confirma HTTP 200 y texto dentro de `candidates[0].content.parts`.

La colección trae el método POST, la URL y los encabezados preparados. Guarda la clave solo en el entorno local del cliente; conserva vacía la variable del archivo versionado.

## Si falla

| Mensaje | Qué revisar |
| --- | --- |
| Falta `GEMINI_API_KEY` | Crea `.env` y completa la variable con ese nombre exacto. |
| HTTP 400, 401 o 403 | Revisa la clave, los permisos y el contenido de la petición. |
| HTTP 404 | Revisa el nombre del modelo en `GEMINI_MODEL`. |
| HTTP 429 | Revisa la cuota y los límites de tu cuenta en Google AI Studio. |
| Error de conexión o de espera | Revisa Internet y vuelve a intentar. |

Si falla la petición o no devuelve texto, el programa termina con error y no guarda evidencia nueva.

## Dependencias y entrega

Las dependencias están en `pyproject.toml` y sus versiones en `uv.lock`. También se incluye `requirements.txt` para mantener el formato solicitado por el curso. Si agregas dependencias con `uv add`, actualízalo con:

```bash
uv export --format requirements.txt --no-dev --no-hashes --no-header --output-file requirements.txt
```

Antes de subir cambios, puedes confirmar que los archivos locales están ignorados:

```bash
git check-ignore .env .venv/
git status
```

Para entregar, comparte el enlace del repositorio de GitHub con los commits y la evidencia ya subidos.
