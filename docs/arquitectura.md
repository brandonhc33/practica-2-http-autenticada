# Arquitectura de la miniaplicación

Actividad práctica del Bloque 8: recorrido de una pregunta desde el usuario hasta la respuesta, con credenciales, manejo de errores, consumo de tokens y costo estimado.

La [decisión de arquitectura del Bloque 9](decision-arquitectura.md) utiliza este diagrama y documenta la comparación de modelos con mediciones reales de costo y latencia.

![Diagrama de arquitectura de POST /consultar](diagrama_arquitectura.png)

El diagrama representa el flujo base entregado en el Bloque 8. El Bloque 10 agrega la selección opcional de prompts, las instrucciones de sistema y la validación del contenido JSON, descritas en esta nota y en la [guía de prompts](bloque-10-prompts.md). El archivo [editable de draw.io](diagrama_arquitectura.drawio) permite modificar las cajas, los textos y las conexiones. Para abrirlo, usa **Archivo → Abrir desde → Dispositivo** en diagrams.net.

## Correspondencia con la actividad

La consigna parte de tres funciones llamadas `armar_peticion`, `enviar_peticion` y `extraer_texto`. Las primeras dos responsabilidades se reúnen aquí en `consultar_gemini_raw()`; desde el Bloque 10, `extraer_texto()` existe como función independiente. Las tres cajas numeradas del diagrama identifican los tramos originales:

| Responsabilidad del curso | Implementación en este repositorio |
| --- | --- |
| `armar_peticion` | Primer tramo de `consultar_gemini_raw()`: lee `GEMINI_API_KEY` y arma los encabezados y el cuerpo. |
| `enviar_peticion` | Segundo tramo de `consultar_gemini_raw()`: hace `requests.post()`, comprueba el estado HTTP y decodifica el JSON. |
| `extraer_texto` | `extraer_texto()`, invocada por `consultar_gemini()`, lee `choices[0].message.content`, valida el texto y elimina espacios en los extremos. |

El proyecto utiliza el endpoint compatible con OpenAI de Gemini. Por eso el dato de consumo se llama **`usage`**, en lugar de **`usageMetadata`**, que es el nombre utilizado en la consigna. El diagrama muestra el campo que procesa el código real.

## Recorrido de la consulta

1. El usuario envía a `POST /consultar` un JSON con `agente`, `modelo` y `mensaje`, opcionalmente `prompt`, junto con el Bearer token de la API local.
2. `validar_bearer()` autentica y `Consulta` valida los datos. `consultar()` llama a `ejecutar_consulta()` con `consultar_agente`.
3. `consultar_agente()` resuelve el modelo del catálogo y ejecuta `consultar_gemini(modelo, mensaje)`, pasando también `prompt` si fue seleccionado.
4. `consultar_gemini_raw()` prepara y envía la petición a Gemini. Si se eligió un prompt, agrega un mensaje `system` y un `response_format` con el JSON Schema del banco. La credencial del proveedor se utiliza en `Authorization: Bearer <GEMINI_API_KEY>`.
5. Con el JSON recibido, `consultar_gemini()` usa `extraer_texto()`. Con un prompt exige finalización `stop` y llama a `parsear_respuesta_json()`, que interpreta el contenido y lo valida estrictamente con Pydantic. Después llama a `extraer_uso(datos.get("usage"))`.
6. `calcular_costo_gemini()` utiliza el consumo y las tarifas registradas para calcular USD. Luego intenta obtener el tipo de cambio y convertir a CLP.
7. `consultar_gemini()` devuelve `Resultado(respuesta, uso, costo_estimado)` y la API lo publica dentro de `RespuestaAPI.detalles`.

`.env` se carga al iniciar la API mediante `load_dotenv()`, dentro de `lifespan()`. `API_BEARER_TOKEN` autentica al cliente ante la API local; `GEMINI_API_KEY` autentica la petición saliente ante Gemini. El diagrama identifica las variables sin incluir sus valores.

## Manejo de errores

| Lugar | Alcance y comportamiento |
| --- | --- |
| `consultar_gemini_raw()` | El `try` comprende `requests.post()`, la comprobación del estado y `respuesta.json()`. Captura `requests.exceptions.JSONDecodeError`, `Timeout` y `RequestException`, en ese orden, y los transforma en `ValueError`. Los estados distintos de 200 también generan `ValueError`, que se propaga. |
| `consultar_gemini_raw()` y `consultar_gemini()` | Fuera del `try` HTTP se verifica que el JSON sea un objeto y que el texto generado sea válido, respectivamente. Una respuesta inválida genera `ValueError`. |
| `ejecutar_consulta()` | El `try` envuelve la llamada a `cliente(consulta)`, incluyendo selección del modelo, consulta y procesamiento. `except AgenteNoConfigurado` genera HTTP 503; `except ValueError` genera HTTP 502. |
| `extraer_uso()` | El `try` envuelve `UsoTokens.model_validate()`. `except ValidationError` devuelve `None`. También se rechaza el consumo incompleto o incoherente. |
| `calcular_costo_gemini()` | El `try` envuelve la obtención del tipo de cambio y la conversión. `except ValueError` conserva los costos en USD y publica `aviso_clp`; los campos de conversión quedan en `None`. |
| `obtener_tipo_cambio()` | Si existe `USD_CLP`, intenta convertirlo a `Decimal` y construir `TipoCambio`. Captura `InvalidOperation` y `ValidationError`, y genera `ValueError`. |
| `consultar_dolar()` | El `try` comprende la consulta pública, la lectura del JSON y la validación del tipo de cambio. Captura `RequestException` y `ValueError`, y genera un `ValueError` explicativo. |

Las validaciones de entrada producen HTTP 401 o 422. Los manejadores registrados en `src/respuestas.py` mantienen el contrato JSON de error; una excepción no prevista produce HTTP 500.

Con un prompt, una salida truncada o que no cumple su esquema genera `ValueError` y la API responde HTTP 502. `Resultado.respuesta` admite texto libre u objeto validado según la selección. El modo raw permite observar incluso contenido inválido sin transformarlo.

Si faltan metadatos válidos, `uso` y `costo_estimado` quedan en `null`. Si hay consumo válido pero no existen tarifas para el modelo, solo `costo_estimado` queda en `null`. En ambos casos se conserva el texto generado.

## Alcance y entrega

La imagen muestra el flujo base de `POST /consultar`; la selección opcional de prompts se describe arriba. La ruta `POST /consultar/raw` devuelve el JSON del proveedor sin extraer texto ni calcular costos. La entrada por terminal reutiliza el cliente Gemini; el diagrama se centra en la entrada HTTP de la miniaplicación.

Los archivos de entrega son `docs/diagrama_arquitectura.png` y su fuente editable `docs/diagrama_arquitectura.drawio`. Esta nota documenta cómo se adaptó la consigna al proyecto.

Para registrar y publicar únicamente esta documentación, desde la raíz del repositorio:

```bash
git add docs/diagrama_arquitectura.png docs/diagrama_arquitectura.drawio docs/arquitectura.md
git commit -m "agrega diagrama de arquitectura de la miniaplicación"
git push
```

Las funciones y los datos representados se contrastaron con `src/api.py`, `src/agentes.py`, `src/agente_gemini.py`, `src/catalogo.py`, `src/costos.py`, `src/tipo_cambio.py`, `src/esquemas.py` y `src/respuestas.py`.
