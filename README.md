# API en Python con autenticación Bearer

Proyecto del Bloque 4 de Skillnest para realizar consultas HTTP autenticadas a Gemini. Usa FastAPI para exponer una API local, `requests` para comunicarse con el proveedor, `.env` para cargar las credenciales y `uv` para gestionar Python y las dependencias.

Cada consulta recibe un agente, un modelo y un mensaje de texto. Todas las respuestas, incluidos los errores, comparten una estructura JSON con los campos `error`, `codigo`, `mensaje` y `detalles`.

## Instalar las herramientas

Para ejecutar el proyecto necesitas **uv y Python 3.12**. Para las pruebas manuales puedes usar **Yaak o Postman**; basta con instalar uno. Necesitas conexión a Internet para instalar las dependencias y consultar Gemini. Las pruebas automatizadas simulan al proveedor y no requieren conexión ni credenciales reales.

### 1. Instalar uv

En Linux o macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Si no tienes `curl`, instálalo antes. En Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y curl ca-certificates
```

En Windows, desde PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Cierra y vuelve a abrir la terminal para que reconozca el comando. Comprueba la instalación:

```bash
uv --version
```

Estos comandos corresponden al [instalador oficial de uv](https://docs.astral.sh/uv/getting-started/installation/).

### 2. Instalar Python 3.12

En cualquiera de los sistemas anteriores:

```bash
uv python install 3.12
```

El proyecto fija esta versión en `.python-version`. No necesitas instalar Python previamente: [uv puede descargarlo y gestionarlo](https://docs.astral.sh/uv/guides/install-python/).

### 3. Instalar un cliente HTTP para las pruebas manuales

Puedes descargar [Yaak](https://yaak.app/) o seguir la [instalación oficial de Postman](https://learning.postman.com/docs/getting-started/installation/install-app/). Ambos permiten importar la colección incluida en el proyecto.

En Linux con Snap disponible, puedes instalar Postman desde la terminal:

```bash
sudo snap install postman
```

El cliente HTTP es opcional para ejecutar el servidor y las pruebas automatizadas.

## Preparar el proyecto

Abre una terminal en la carpeta del proyecto e instala las dependencias:

```bash
uv sync --locked
```

Este comando crea `.venv` e instala las dependencias de ejecución y desarrollo con las versiones de `uv.lock`, incluidas FastAPI, Uvicorn, Requests, Ruff y Basedpyright. No necesitas instalarlas globalmente ni activar el entorno: los comandos con `uv run` lo usan automáticamente.

Comprueba la versión de Python del proyecto:

```bash
uv run python --version
```

### Configurar las credenciales

Si todavía no tienes `.env`, créalo a partir del archivo de ejemplo. En Linux o macOS:

```bash
cp .env.example .env
```

En Windows, desde PowerShell:

```powershell
Copy-Item .env.example .env
```

Abre `.env` en tu editor y completa estas variables:

```dotenv
GEMINI_API_KEY=tu_clave_de_google_ai_studio
API_BEARER_TOKEN=tu_token_de_la_api
```

Obtén la clave de Gemini en [Google AI Studio](https://aistudio.google.com/api-keys). Para generar el token propio de tu API:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copia el resultado a `API_BEARER_TOKEN`, sin el prefijo `Bearer`. Este token protege tu API local; `GEMINI_API_KEY` autentica las consultas que el servidor envía a Google. Son credenciales distintas.

Los archivos `.env` y `.venv/` están excluidos de Git. El archivo `.env.example` contiene las variables necesarias con sus valores vacíos.

## Iniciar la API

```bash
uv run uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```

Ambos endpoints requieren `Authorization: Bearer <API_BEARER_TOKEN>`:

| Método | URL | Resultado |
| --- | --- | --- |
| GET | `http://127.0.0.1:8000/health` | HTTP 200 con `detalles: {"estado": "ok"}`. |
| POST | `http://127.0.0.1:8000/consultar` | HTTP 200 con `detalles.respuesta`. |

Sin token o con uno incorrecto, devuelve HTTP 401. Si falta `API_BEARER_TOKEN`, el servidor avisa al arrancar y no inicia. Reinicia el servidor después de cambiar el token en `.env`.

Las rutas se usan tal como aparecen en la tabla, sin una barra final. Una ruta distinta devuelve HTTP 404 con el contrato común.

## Probar con Yaak o Postman

1. Inicia la API y déjala ejecutándose en su terminal. Abre Yaak o Postman e importa [api.postman_collection.json](api.postman_collection.json). En Yaak, usa **Import Data**.
2. Configura una variable local `API_BEARER_TOKEN` con el valor de tu `.env`, sin el prefijo `Bearer`. La colección no lee `.env` automáticamente.
3. Verifica **Auth → Bearer Token**. Si el importador no conserva la autenticación, selecciona Bearer y coloca el token en ese campo.
4. Envía **Estado de la API** y comprueba HTTP 200. Cambia el token para verificar HTTP 401.
5. Envía **Consultar desde la API Python** con el cuerpo JSON del ejemplo y comprueba el texto en `detalles.respuesta`.
6. Envía **Validación - campos faltantes** y **Validación - valores inválidos** para comprobar HTTP 422 y los errores por campo. **Autenticación - sin token** permite verificar HTTP 401.

En la sección [Solicitud y respuesta](#solicitud-y-respuesta) se detalla el formato de la consulta y sus validaciones.

La colección configura `BASE_URL` como `http://127.0.0.1:8000`, `AGENTE` como `gemini` y `MODELO` como `flash-lite`. El token versionado queda vacío. Las credenciales de Google se configuran en el servidor. En Postman, la colección comprueba automáticamente la estructura común y que `codigo` coincida con el estado HTTP.

## Campos de la solicitud

El cuerpo JSON usa nombres de campos en español. Los códigos de agente y modelo se escriben en minúsculas:

| Campo | Significado | Ejemplo |
| --- | --- | --- |
| `agente` | Servicio que atenderá la consulta. | `gemini` |
| `modelo` | Código de un modelo asociado a ese agente. | `flash-lite` |
| `mensaje` | Texto de la consulta. | `Hola, confirma que puedes responder.` |

## Agentes y modelos disponibles

La API tiene habilitadas las siguientes combinaciones en su catálogo:

| Proveedor | `agente` en el body | `modelo` en el body | Modelo del proveedor | Variable de credencial |
| --- | --- | --- | --- | --- |
| Google Gemini | `gemini` | `flash-lite` | `gemini-3.5-flash-lite` | `GEMINI_API_KEY` |

Para usar esta combinación, envía `"agente": "gemini"` y `"modelo": "flash-lite"` a `POST /consultar` y configura `GEMINI_API_KEY` en el `.env` del servidor. La petición también requiere el Bearer token de la API.

La asociación se define en [src/catalogo.py](src/catalogo.py). El cliente usa los códigos cortos de las columnas `agente` y `modelo`; el servidor resuelve el nombre real del modelo. Un agente desconocido o un modelo ajeno al agente devuelve HTTP 422. Al habilitar nuevas combinaciones en el catálogo, actualiza también esta tabla.

## Solicitud y respuesta

Envía este body JSON a `POST http://127.0.0.1:8000/consultar`:

```json
{
  "agente": "gemini",
  "modelo": "flash-lite",
  "mensaje": "Hola, ¿puedes confirmar que esta conexión funciona?"
}
```

Los tres campos son obligatorios y deben ser cadenas de texto. No se aceptan campos adicionales ni valores vacíos o compuestos solo por espacios. Cada petición es una consulta independiente; no se conserva un historial de conversación.

| Campo | Longitud permitida | Validaciones adicionales |
| --- | --- | --- |
| `agente` | De 1 a 32 caracteres. | Letras minúsculas, números, guiones o guiones bajos, sin espacios; debe existir en el catálogo. |
| `modelo` | De 1 a 64 caracteres. | Mismo formato que `agente`; debe pertenecer al agente elegido. |
| `mensaje` | De 1 a 4.000 caracteres. | Debe contener texto. Se conserva su contenido, incluidos espacios y saltos de línea. |

Los límites incluyen ambos extremos y cuentan caracteres, no bytes. Se definen en `LIMITES_CONSULTA` de [src/esquemas.py](src/esquemas.py).

Ejemplo de respuesta HTTP 200:

```json
{
  "error": false,
  "codigo": 200,
  "mensaje": "Consulta realizada correctamente.",
  "detalles": {
    "respuesta": "Sí, la conexión funciona."
  }
}
```

`detalles.respuesta` contiene únicamente el texto generado. La consulta enviada no se incluye en la respuesta para evitar duplicar su contenido, especialmente cuando el mensaje es largo.

### Contrato común de respuestas

| Campo | Tipo | Significado |
| --- | --- | --- |
| `error` | Booleano. | `false` si la operación se completó; `true` para errores HTTP 4xx y 5xx. |
| `codigo` | Entero. | Coincide con el estado HTTP real de la respuesta. |
| `mensaje` | Texto. | Explicación breve en español. |
| `detalles` | Objeto. | Datos de éxito, validaciones o información útil para corregir el error. |

Por ejemplo, si envías `{"pregunta": "Hola, ¿cómo estás?"}`, obtienes HTTP 422:

```json
{
  "error": true,
  "codigo": 422,
  "mensaje": "Revisa los campos de la solicitud.",
  "detalles": {
    "validaciones": [
      {"campo": "agente", "errores": ["El campo es obligatorio."]},
      {"campo": "modelo", "errores": ["El campo es obligatorio."]},
      {"campo": "mensaje", "errores": ["El campo es obligatorio."]},
      {
        "campo": "pregunta",
        "errores": ["El campo no está permitido. Envía el texto de la consulta en 'mensaje'."]
      }
    ],
    "campos_permitidos": ["agente", "modelo", "mensaje"],
    "ejemplo": {
      "agente": "gemini",
      "modelo": "flash-lite",
      "mensaje": "Hola, ¿en qué puedes ayudarme?"
    }
  }
}
```

Cada campo aparece una vez en `detalles.validaciones`, con uno o varios mensajes en `errores`. Los errores de agente o modelo también se asocian a su campo e indican las opciones disponibles. Un cuerpo ausente, un JSON mal formado o un valor que no sea un objeto se identifica como `campo: "cuerpo"`.

Por ejemplo, un `modelo` de 65 letras mayúsculas devuelve dos errores para ese campo:

```json
{
  "campo": "modelo",
  "errores": [
    "No puede superar los 64 caracteres.",
    "Usa solo letras minúsculas, números, guiones o guiones bajos, sin espacios."
  ]
}
```

Los manejadores globales están en [src/respuestas.py](src/respuestas.py), siguiendo el mecanismo de [manejadores de excepciones de FastAPI](https://fastapi.tiangolo.com/tutorial/handling-errors/#override-the-default-exception-handlers). Cubren validación, autenticación, errores del proveedor, rutas inexistentes, métodos no permitidos y excepciones inesperadas. Estas últimas devuelven HTTP 500 con una indicación para el cliente; la excepción completa se registra en el servidor. Para nuevos endpoints, usa `RespuestaAPI[TipoDeDetalles]` como modelo de respuesta y `ErrorAPI` para errores previstos.

## Agregar modelos o agentes

La coordinación y los clientes están separados:

| Módulo | Responsabilidad |
| --- | --- |
| [src/api.py](src/api.py) | Recibe las solicitudes HTTP y traduce los resultados y errores al contrato JSON de la API. |
| [src/agentes.py](src/agentes.py) | Comprueba la configuración, selecciona el cliente registrado, resuelve el modelo y devuelve el resultado. |
| [src/agente_gemini.py](src/agente_gemini.py) | Gestiona la credencial de Gemini, su petición HTTP y la extracción del texto generado. |
| [src/catalogo.py](src/catalogo.py) | Define los códigos públicos de agentes, sus variables de credenciales y los modelos disponibles. |

El flujo de una consulta es `api.py → agentes.py → agente_gemini.py`. Cada cliente recibe el nombre real del modelo y el mensaje, y devuelve el texto generado.

Para agregar un modelo de Gemini, registra otro código y su nombre real en `AGENTES["gemini"]["modelos"]` de [src/catalogo.py](src/catalogo.py).

Para agregar otro agente, registra su código, la variable de su clave y sus modelos en el catálogo. Implementa su cliente en un módulo `src/agente_<nombre>.py` y regístralo en `CLIENTES` de [src/agentes.py](src/agentes.py).

El cliente de Gemini adapta la solicitud al [formato de chat que acepta Google](https://ai.google.dev/gemini-api/docs/openai#rest). La colección `gemini.postman_collection.json` es una herramienta de diagnóstico para llamar directamente al proveedor y usa el formato propio de Google.

## Resolver problemas

| Resultado | Qué revisar |
| --- | --- |
| HTTP 401 | Revisa el Bearer token y que coincida con `API_BEARER_TOKEN`. |
| HTTP 404 | Revisa la URL; `detalles.ruta` muestra la ruta solicitada. |
| HTTP 405 | Usa el método correcto; `detalles.metodos_permitidos` indica las opciones. |
| HTTP 422 | Revisa `detalles.validaciones`: identifica cada campo y sus errores. También se incluye un ejemplo de consulta válida. |
| HTTP 503 | Configura en el servidor la variable indicada en `detalles.configuracion_requerida`, actualmente `GEMINI_API_KEY`. |
| HTTP 502 | La consulta a Gemini falló. `detalles.causa` explica el error. Un HTTP 503 de Gemini indica indisponibilidad temporal: espera y reintenta. |
| HTTP 500 | Reintenta más tarde y revisa los registros del servidor si el problema persiste. |
| Error de conexión | Revisa que el servidor esté en ejecución y que la URL sea correcta. |

## Verificar el proyecto

Las herramientas de desarrollo se instalan con `uv sync --locked`. La configuración compartida está en `pyproject.toml`:

- **Basedpyright** comprueba tipos en `src` y `tests`, con Python 3.12 y el entorno `.venv`. Se usa el modo `standard`; `recommended` añade comprobaciones más exigentes sobre tipos dinámicos y otras advertencias.
- **Ruff** revisa errores habituales, organización de imports y sintaxis moderna de Python. También mantiene un formato uniforme.

```bash
uv run basedpyright
uv run ruff check src tests
uv run ruff format --check src tests
```

Para aplicar correcciones automáticas de estilo y formato:

```bash
uv run ruff check src tests --fix
uv run ruff format src tests
```

El editor puede mostrar cada diagnóstico al pasar el cursor sobre el subrayado o abrir su panel de problemas. Si marca imports que funcionan en la terminal, comprueba que use el intérprete de este proyecto: `.venv/bin/python` en Linux/macOS o `.venv/Scripts/python.exe` en Windows. Después de cambiar el entorno o la configuración, reinicia el servidor de lenguaje o recarga el editor.

Estas comprobaciones analizan el código sin ejecutar las peticiones. Las pruebas verifican su comportamiento:

```bash
uv run python -m tests -v
```

El punto de entrada [tests/__main__.py](tests/__main__.py) usa el descubrimiento de `unittest` para ejecutar todos los archivos `test_*.py`. Al agregar uno nuevo, se incorpora automáticamente; cada prueba prepara y limpia su propio entorno y no depende del orden de ejecución.

El ejecutor muestra resultados correctos en verde, fallos y errores en rojo y pruebas omitidas o fallos esperados en amarillo. El resumen también tiene color. Los colores se activan en una terminal compatible; al redirigir la salida a un archivo se usa texto normal. Puedes desactivarlos definiendo la variable de entorno `NO_COLOR`.

Las pruebas se organizan por responsabilidad:

| Archivo | Cobertura |
| --- | --- |
| `tests/base.py` | Preparación común, simulación de Gemini y aserciones del contrato JSON. |
| `tests/test_autenticacion.py` | Bearer token y separación de credenciales locales y del proveedor. |
| `tests/test_consultas.py` | Estado de la API, consultas exitosas, selección de agentes y modelos y preservación del mensaje. |
| `tests/test_validaciones.py` | Campos, tipos, formato, longitudes y cuerpo JSON. |
| `tests/test_errores_http.py` | Rutas, métodos y errores internos. |
| `tests/test_gemini.py` | Timeout, indisponibilidad y respuestas inválidas del proveedor. |
| `tests/test_configuracion.py` | Variables requeridas y configuración al iniciar. |

Para ejecutar solo un grupo:

```bash
uv run python -m unittest tests.test_autenticacion -v
```

También sigue disponible el comando estándar `uv run python -m unittest discover -s tests -v`.

Las pruebas verifican el contrato común, autenticación, campos faltantes, tipos, formato, longitudes límite, errores múltiples por campo, JSON mal formado, asociación de agentes y modelos, preservación del mensaje y errores HTTP e inesperados. Simulan Gemini y se ejecutan sin claves reales ni conexión.

Las dependencias están en `pyproject.toml`, sus versiones en `uv.lock` y el listado de ejecución en `requirements.txt`. Si agregas dependencias, actualiza el listado con:

```bash
uv export --format requirements.txt --no-dev --no-hashes --no-header --output-file requirements.txt
```

Antes de subir cambios:

```bash
git check-ignore .env .venv/
git status
```
