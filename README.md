# Práctica 2: consultas HTTP autenticadas con Gemini

Proyecto del Bloque 4 de Skillnest que permite consultar Gemini desde Python y mediante una API local protegida con un Bearer token.

La tarea incluye una función `obtener_dato_de_prueba(pregunta)` para comprobar que Gemini responde desde Python. Tanto el comando como la API devuelven el texto, los tokens consumidos y el costo estimado en USD y CLP de cada consulta, con símbolos de moneda y decimales sin notación exponencial. También incluye validaciones de entrada, manejo de errores y pruebas automatizadas.

La API también permite inspeccionar la respuesta JSON completa del proveedor mediante `POST /consultar/raw`.

## Tecnologías

- Python 3.12 y `uv` para gestionar el entorno y las dependencias.
- `requests` para realizar la petición HTTP autenticada a Gemini.
- `python-dotenv` para cargar las credenciales desde `.env`.
- FastAPI y Uvicorn para exponer la API local.
- `unittest` para ejecutar pruebas con la comunicación a Gemini simulada.

## 1. Instalar las herramientas

### uv y Python

Instala `uv` en Linux o macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

En Windows, desde PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Si la terminal no reconoce `uv`, ciérrala y vuelve a abrirla. Comprueba la instalación e instala Python:

```bash
uv --version
uv python install 3.12
```

El proyecto fija Python 3.12 en `.python-version`. Consulta la [instalación oficial de uv](https://docs.astral.sh/uv/getting-started/installation/) si necesitas otra forma de instalarlo.

### Cliente HTTP opcional

Para las pruebas manuales puedes usar [Yaak](https://yaak.app/) o [Postman](https://learning.postman.com/docs/getting-started/installation/install-app/). El repositorio incluye una colección para consultar Gemini y otra para probar la API local.

Necesitas conexión a Internet para instalar las dependencias y realizar consultas reales a Gemini.

## 2. Preparar el proyecto

Ejecuta los comandos desde la carpeta raíz del repositorio:

```bash
uv sync --locked
uv run python --version
```

`uv sync --locked` crea `.venv` e instala las dependencias con las versiones de `uv.lock`. Los comandos con `uv run` utilizan ese entorno automáticamente.

### Configurar las credenciales

Si todavía no tienes `.env`, créalo a partir del ejemplo. En Linux o macOS:

```bash
cp .env.example .env
```

En Windows, desde PowerShell:

```powershell
Copy-Item .env.example .env
```

Completa el archivo con tus credenciales:

```dotenv
GEMINI_API_KEY=tu_clave_de_google_ai_studio
API_BEARER_TOKEN=tu_token_de_la_api
```

| Variable | Para qué se usa |
| --- | --- |
| `GEMINI_API_KEY` | Autentica la petición que Python envía a Gemini. Obtén la clave en [Google AI Studio](https://aistudio.google.com/api-keys). |
| `API_BEARER_TOKEN` | Protege los endpoints de la API local. Tú generas este token. |
| `USD_CLP` | Opcional: pesos chilenos por dólar, con punto decimal. Si queda vacío, se consulta automáticamente el dólar observado. |

Para generar el token local:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copia el resultado a `API_BEARER_TOKEN`, sin el prefijo `Bearer`. Las credenciales reales van en `.env`, que está excluido de Git. `.env.example` contiene únicamente las variables vacías.

## 3. Prueba de la tarea desde Python

Ejecuta este comando para comprobar que Gemini responde:

```bash
uv run python -m src.agente_gemini
```

Si no pasas una pregunta, el módulo llama a `obtener_dato_de_prueba(pregunta)` con la pregunta por defecto:

> Estoy aprendiendo a programar en Python y quiero entender cómo se conecta una aplicación con una inteligencia artificial. ¿Puedes explicar qué es una API, cómo viaja una pregunta desde Python hasta Gemini y cómo vuelve la respuesta? Incluye una analogía cotidiana, explica para qué sirve una API key y menciona tres errores comunes al hacer la conexión con una forma de resolver cada uno. Responde en español, con secciones breves y en unas 200 palabras.

La salida es un JSON con `respuesta`, `uso` y `costo_estimado`. En `respuesta` aparece una explicación con una analogía, el recorrido de la consulta, el uso de la API key y tres errores con sus soluciones. El texto y el consumo se generan en cada ejecución y pueden variar.

La función está en [src/agente_gemini.py](src/agente_gemini.py). Carga `.env`, obtiene el modelo `flash-lite` del catálogo, realiza la consulta autenticada y devuelve un objeto `Resultado` con texto, tokens y costos. Al ejecutar el módulo, ese resultado se imprime como JSON en la terminal, con la misma estructura que `detalles` en la API.

Esta prueba requiere `GEMINI_API_KEY`. Puedes ejecutarla sin iniciar la API local y sin configurar `API_BEARER_TOKEN`.

Para pasar tu propia pregunta como parámetro, escríbela entre comillas después del nombre del módulo:

```bash
uv run python -m src.agente_gemini "Explica la diferencia entre una API y una página web con un ejemplo de cada una."
```

La pregunta entre comillas reemplaza la predeterminada para esa ejecución. Las comillas permiten enviar varias palabras como un solo argumento. Una pregunta vacía o compuesta solo por espacios se rechaza antes de consultar Gemini.

Para ver la ayuda del comando:

```bash
uv run python -m src.agente_gemini --help
```

También puedes importar la función desde otro módulo del proyecto:

```python
from src.agente_gemini import obtener_dato_de_prueba

resultado = obtener_dato_de_prueba(
    "Explica tres usos de la inteligencia artificial en la educación, "
    "con un ejemplo práctico y una limitación de cada uno."
)
print(resultado.respuesta)
print(resultado.uso)
if resultado.costo_estimado is not None:
    costos = resultado.costo_estimado.model_dump(mode="json")
    print("Costo estimado en USD:", costos["usd"]["total"])
    if costos["clp"] is not None:
        print("Costo estimado en CLP:", costos["clp"]["total"])
```

Si la consulta falla, el comando muestra un mensaje de error y termina con un código de salida distinto de cero.

## 4. Iniciar la API local

Con ambas credenciales configuradas, ejecuta:

```bash
uv run uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```

Mantén esa terminal abierta mientras realizas las peticiones. Si falta `API_BEARER_TOKEN`, el servidor avisa al arrancar y no inicia. Reinícialo después de cambiar ese token en `.env`.

Todos los endpoints requieren este encabezado:

```http
Authorization: Bearer <API_BEARER_TOKEN>
```

Sustituye `<API_BEARER_TOKEN>` por el valor de tu `.env`.

| Método | URL | Resultado esperado |
| --- | --- | --- |
| GET | `http://127.0.0.1:8000/health` | HTTP 200 con `detalles.estado` igual a `ok`. |
| POST | `http://127.0.0.1:8000/consultar` | HTTP 200 con texto, tokens y costo estimado dentro de `detalles`. |
| POST | `http://127.0.0.1:8000/consultar/raw` | HTTP 200 con el JSON completo de Gemini directamente en el cuerpo. |

Usa las rutas sin una barra final. Un token ausente o incorrecto devuelve HTTP 401. Las páginas `/docs` y `/redoc` están deshabilitadas.

### Solicitud de consulta

Envía este cuerpo JSON a `POST /consultar`, con `Content-Type: application/json` y el encabezado de autenticación:

```json
{
  "agente": "gemini",
  "modelo": "flash-lite",
  "mensaje": "Estoy aprendiendo a programar en Python y quiero entender cómo se conecta una aplicación con una inteligencia artificial. ¿Puedes explicar qué es una API, cómo viaja una pregunta desde Python hasta Gemini y cómo vuelve la respuesta? Incluye una analogía cotidiana, explica para qué sirve una API key y menciona tres errores comunes al hacer la conexión con una forma de resolver cada uno. Responde en español, con secciones breves y en unas 200 palabras."
}
```

Ejemplo de respuesta exitosa con consumo ilustrativo; el texto y los tokens reales dependen de Gemini:

```json
{
  "error": false,
  "codigo": 200,
  "mensaje": "Consulta realizada correctamente.",
  "detalles": {
    "respuesta": "Una API permite que dos aplicaciones se comuniquen...",
    "uso": {
      "entrada": 1000,
      "salida": 2000,
      "total": 3000,
      "entrada_cache": 0
    },
    "costo_estimado": {
      "modelo": "gemini-3.5-flash-lite",
      "usd": {
        "moneda": "USD",
        "entrada": "US$ 0.0003",
        "salida": "US$ 0.005",
        "total": "US$ 0.0053"
      },
      "clp": {
        "moneda": "CLP",
        "entrada": "$ 0.294495",
        "salida": "$ 4.90825",
        "total": "$ 5.202745"
      },
      "tipo_cambio": {
        "clp_por_usd": "981.65",
        "fecha": "2026-10-19",
        "fuente": "https://indicadores.cl/api/v1/dolar.json"
      },
      "tarifas_por_millon_usd": {
        "entrada": "US$ 0.30",
        "entrada_cache": "US$ 0.03",
        "salida": "US$ 2.50"
      },
      "tarifas_por_millon_clp": {
        "entrada": "$ 294.495",
        "entrada_cache": "$ 29.4495",
        "salida": "$ 2454.125"
      },
      "aviso_clp": null
    }
  }
}
```

Cada consulta es independiente; no se conserva un historial de conversación ni se acumulan los costos. `detalles.respuesta` contiene el texto generado, `detalles.uso` el consumo y `detalles.costo_estimado` los importes y las tarifas aplicadas.

### Inspeccionar la respuesta original de Gemini

Envía el mismo formato de solicitud a `POST /consultar/raw`, con `Content-Type: application/json` y el Bearer token de la API local:

```json
{
  "agente": "gemini",
  "modelo": "flash-lite",
  "mensaje": "Hola, responde con una frase breve."
}
```

Cuando Gemini responde HTTP 200, este endpoint devuelve su objeto JSON completo directamente en el cuerpo: puedes inspeccionar `choices`, `usage`, el modelo y cualquier otro metadato que incluya el proveedor. Se conservan los campos originales, los valores `null` y los espacios del texto. También se permiten respuestas sin texto generado para inspeccionar el motivo de finalización u otros campos disponibles.

La respuesta corresponde al endpoint compatible con OpenAI que usa este proyecto, definido en [src/agente_gemini.py](src/agente_gemini.py): `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`. Se conserva el contenido JSON; su formato de espacios y sangría puede cambiar al serializarlo.

Cada petición realiza una nueva consulta a Gemini. La respuesta exitosa de esta ruta contiene únicamente el JSON del proveedor: los costos calculados por la aplicación se obtienen mediante `/consultar`. La ruta raw realiza una sola llamada a Gemini y no consulta el tipo de cambio.

Los errores de autenticación, validación, configuración y comunicación conservan el contrato local `error`, `codigo`, `mensaje` y `detalles`. Por ejemplo, si Gemini devuelve HTTP 429, la API responde HTTP 502 con la causa, igual que en `/consultar`.

### Tokens y costo por consulta

El consumo se obtiene del objeto `usage` de Gemini. `entrada` corresponde a `prompt_tokens`, `total` a `total_tokens` y `salida` se calcula como `total - entrada`. Así se incluyen los tokens de razonamiento aunque el proveedor los omita de `completion_tokens`, sin sumarlos dos veces. Este cliente realiza consultas de texto sin herramientas. `entrada_cache` corresponde a `prompt_tokens_details.cached_tokens` y forma parte de `entrada`; si ese detalle no aparece, se utiliza cero.

Las tarifas están centralizadas por modelo en [src/costos.py](src/costos.py). Para `gemini-3.5-flash-lite` se usan las [tarifas oficiales estándar de pago](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite), verificadas el 19 de octubre de 2026, en USD por millón de tokens:

| Consumo | USD por 1.000.000 de tokens |
| --- | --- |
| Entrada sin caché | 0,30 |
| Entrada desde caché | 0,03 |
| Salida, incluido el razonamiento | 2,50 |

```text
costo_entrada = ((entrada - entrada_cache) × tarifa_entrada
                 + entrada_cache × tarifa_cache) / 1.000.000
costo_salida  = salida × tarifa_salida / 1.000.000
costo_total   = costo_entrada + costo_salida
```

Los cálculos usan `Decimal` y conservan todos los decimales significativos. Los importes se publican como **textos JSON con símbolo de moneda**, con un mínimo de dos decimales y sin notación exponencial; por ejemplo, `"US$ 0.0000003"`. Los códigos `USD` y `CLP` distinguen ambas monedas. Por ejemplo, 1.000 tokens de entrada y 2.000 de salida, sin caché, representan **US$ 0.0053**.

### Conversión de USD a CLP

Cada importe en CLP se calcula multiplicando su valor en USD por `tipo_cambio.clp_por_usd`, sin redondear a pesos enteros. Por defecto se obtiene el último dólar observado publicado en [indicadores.cl](https://indicadores.cl/api/), cuya fuente es el Banco Central de Chile. La respuesta incluye la fecha del dato y la fuente; cada proceso reutiliza la tasa durante un máximo de una hora. La consulta pública del dólar no recibe claves ni el mensaje enviado a Gemini.

`tarifas_por_millon_clp` contiene las tarifas de entrada, entrada desde caché y salida por **1.000.000 de tokens**, convertidas con el mismo tipo de cambio de los costos de la consulta: `tarifa_clp = tarifa_usd × clp_por_usd`. Se conservan los símbolos de moneda y todos los decimales significativos.

Puedes fijar tu propia tasa con la variable opcional `USD_CLP` en `.env`, sin símbolo de moneda y con punto decimal:

```dotenv
# Ejemplo de tasa manual, no una cotización vigente.
USD_CLP=950.50
```

Con una tasa manual no se consulta la fuente pública; `tipo_cambio.fuente` indica `USD_CLP (.env)` y `fecha` queda en `null`. Para volver a la consulta automática, deja `USD_CLP` vacío. Reinicia el servidor si cambias esta variable.

`aviso_clp: null` significa que la conversión a CLP se completó correctamente y no hay advertencias. Si la fuente del dólar falla o la tasa configurada es inválida, se conservan el texto, los tokens, el costo y las tarifas en USD; `clp`, `tipo_cambio` y `tarifas_por_millon_clp` quedan en `null`, y `aviso_clp` contiene un mensaje que explica cómo corregirlo.

El resultado es una estimación con precios de pago: no consulta la facturación de Google ni detecta si tu cuenta usa el nivel gratuito, créditos o descuentos. No incluye impuestos ni otros servicios. Revisa las tarifas antes de actualizarlas o habilitar otro modelo.

Si el consumo está ausente, incompleto o es inválido, `uso` y `costo_estimado` son `null` y se conserva el texto generado. Si el consumo es válido pero el modelo no tiene tarifas registradas, se devuelve `uso` y `costo_estimado` queda en `null`. Un importe cero se reserva para consumo cero reportado por el proveedor.

### Campos y validaciones

Los tres campos son obligatorios y deben ser cadenas de texto. No se aceptan campos adicionales ni valores vacíos o compuestos solo por espacios.

| Campo | Longitud | Validaciones |
| --- | --- | --- |
| `agente` | De 1 a 32 caracteres. | Debe existir en el catálogo. Solo acepta letras minúsculas, números, guiones y guiones bajos. |
| `modelo` | De 1 a 64 caracteres. | Debe pertenecer al agente elegido y cumplir el mismo formato que `agente`. |
| `mensaje` | De 1 a 4.000 caracteres. | Debe contener texto. Se conservan sus espacios y saltos de línea. |

Los límites son inclusivos y cuentan caracteres, no bytes. En la API, el texto se envía en `mensaje`; un campo llamado `pregunta` se rechaza con HTTP 422.

### Agente y modelo configurados

El catálogo de [src/catalogo.py](src/catalogo.py) contiene esta combinación:

| Agente en el JSON | Modelo en el JSON | Modelo del proveedor | Credencial |
| --- | --- | --- | --- |
| `gemini` | `flash-lite` | `gemini-3.5-flash-lite` | `GEMINI_API_KEY` |

El servidor resuelve el nombre del modelo del proveedor a partir de los códigos públicos. La petición a Gemini utiliza el endpoint definido en `src/agente_gemini.py` y envía la clave en `Authorization: Bearer ...`. El token local se valida en la API y no se envía a Google.

## 5. Probar con Yaak o Postman

### Consulta directa a Gemini

1. Importa [gemini.postman_collection.json](gemini.postman_collection.json).
2. Configura la variable local `GEMINI_API_KEY` con tu clave de Google AI Studio.
3. Revisa que la autenticación sea **Bearer Token** y use `{{GEMINI_API_KEY}}`.
4. Envía **Consultar Gemini** y comprueba HTTP 200. El texto generado se encuentra en `choices[0].message.content`.

Esta colección realiza la petición directamente al proveedor.

### Consulta mediante la API Python

1. Inicia el servidor y déjalo ejecutándose.
2. Importa [api.postman_collection.json](api.postman_collection.json). En Yaak puedes usar **Import Data**.
3. Configura `API_BEARER_TOKEN` en el cliente con el mismo valor de tu `.env`, sin el prefijo `Bearer`.
4. Revisa **Auth → Bearer Token**. Si el importador no conserva la autenticación, selecciónala y coloca el token en ese campo.
5. Envía **Estado de la API** y comprueba HTTP 200.
6. Envía **Consultar desde la API Python** y comprueba el texto en `detalles.respuesta`, los tokens en `detalles.uso` y el costo en `detalles.costo_estimado`.
7. Envía **Consultar respuesta raw de Gemini** para inspeccionar directamente el JSON completo del proveedor.
8. Envía **Autenticación - sin token** para comprobar HTTP 401.
9. Envía **Validación - campos faltantes** y **Validación - valores inválidos** para comprobar HTTP 422.

La colección usa `BASE_URL=http://127.0.0.1:8000`, `AGENTE=gemini` y `MODELO=flash-lite`. Los tokens de ambas colecciones están vacíos: los clientes HTTP no leen el `.env` del proyecto automáticamente.

En Postman, la colección de la API incluye comprobaciones del contrato común y de que `codigo` coincida con el estado HTTP. Las respuestas exitosas de `/consultar/raw` se comprueban como objetos JSON del proveedor.

## Contrato común de respuestas

Las respuestas de `/health`, `/consultar` y todos los errores de la API local contienen estos campos. Las respuestas HTTP 200 de `/consultar/raw` contienen directamente el JSON de Gemini:

| Campo | Tipo | Significado |
| --- | --- | --- |
| `error` | Booleano. | `false` cuando la operación se completa; `true` en errores HTTP 4xx y 5xx. |
| `codigo` | Entero. | Coincide con el estado HTTP de la respuesta. |
| `mensaje` | Texto. | Explicación breve en español. |
| `detalles` | Objeto. | Resultado o información para corregir el error. |

Por ejemplo, una petición sin token devuelve HTTP 401:

```json
{
  "error": true,
  "codigo": 401,
  "mensaje": "No se pudo autenticar la solicitud.",
  "detalles": {
    "causa": "Bearer token ausente o inválido.",
    "encabezado_requerido": "Authorization: Bearer <API_BEARER_TOKEN>"
  }
}
```

En los errores HTTP 422, `detalles.validaciones` identifica cada `campo` y sus `errores`. Un campo puede tener varios errores. También se incluyen `campos_permitidos` y un `ejemplo` de consulta válida. Un cuerpo ausente, un JSON mal formado o un valor que no sea un objeto se identifica como `campo: "cuerpo"`.

## Resolver problemas

| Resultado | Qué revisar |
| --- | --- |
| Falta `GEMINI_API_KEY` en la prueba Python | Completa la clave en `.env`. |
| El servidor no inicia por falta de token | Configura `API_BEARER_TOKEN` y vuelve a iniciarlo. |
| HTTP 401 de la API local | Envía el Bearer token y comprueba que coincida con el del servidor. |
| HTTP 404 de la API local | Revisa la ruta y evita la barra final. `detalles.ruta` indica la ruta solicitada. |
| HTTP 405 | Revisa el método HTTP. `detalles.metodos_permitidos` indica las opciones. |
| HTTP 422 | Revisa los campos y los mensajes de `detalles.validaciones`. |
| HTTP 503 de la API local | Configura la credencial indicada en `detalles.configuracion_requerida`. |
| HTTP 502 | La consulta a Gemini falló. `detalles.causa` explica el error del proveedor o de conexión. |
| HTTP 500 | Revisa los registros del servidor y vuelve a intentar la operación. |
| Error de conexión al servidor local | Comprueba que Uvicorn siga ejecutándose en el puerto 8000. |

Cuando el mensaje de la prueba Python o `detalles.causa` indique HTTP 400, 401 o 403 de Gemini, revisa la clave, los permisos y el contenido de la consulta. Un HTTP 404 del proveedor requiere revisar el modelo del catálogo; HTTP 429 indica un límite de cuota y HTTP 503, indisponibilidad temporal.

## Pruebas automatizadas

Ejecuta la suite:

```bash
uv run python -m tests -v
```

Las pruebas comprueban autenticación, configuración, validaciones, consultas, manejo de errores y costos. Cubren la salida del comando y del endpoint, caché, razonamiento, importes pequeños sin exponentes, conversión USD/CLP, tasa manual y fallas de la fuente del dólar. También comprueban que `/consultar/raw` conserve todo el JSON del proveedor, incluso sin texto generado, y que utilice una sola petición sin consultar el dólar. Simulan la comunicación con Gemini y el servicio de tipo de cambio, por lo que no requieren credenciales reales ni conexión a esos servicios una vez instaladas las dependencias.

Para revisar el código con las herramientas de desarrollo:

```bash
uv run ruff check src tests
uv run basedpyright
```

## Estructura del proyecto

```text
.
├── src/
│   ├── agente_gemini.py   # Cliente HTTP y prueba directa desde Python
│   ├── agentes.py         # Selección y ejecución del agente
│   ├── api.py             # Endpoints y autenticación local
│   ├── catalogo.py        # Agentes y modelos habilitados
│   ├── costos.py          # Tarifas por modelo y costos en USD y CLP
│   ├── esquemas.py        # Modelos de datos y validaciones
│   ├── respuestas.py      # Contrato de respuestas y manejo de errores
│   └── tipo_cambio.py     # Dólar observado y tasa manual opcional
├── tests/                 # Suite automatizada
├── docs/                  # Evidencias de las peticiones
├── api.postman_collection.json
├── gemini.postman_collection.json
├── .env.example
├── .python-version
├── pyproject.toml
├── requirements.txt
└── uv.lock
```

## Comprobaciones de la tarea

Para verificar lo implementado:

- Ejecuta la consulta directa desde el cliente HTTP con la colección de Gemini.
- Ejecuta `uv run python -m src.agente_gemini` y comprueba texto, tokens y costo estimado en el JSON de salida.
- Comprueba que `/health`, `/consultar` y `/consultar/raw` responden con un Bearer token válido.
- Comprueba HTTP 401 al omitir el token y HTTP 422 al enviar campos inválidos.
- Ejecuta la suite de pruebas automatizadas.

La carpeta [docs](docs/) contiene las evidencias de peticiones del proyecto, incluida la [captura del endpoint de consulta](docs/evidencia_endpoint_consultar.png).
