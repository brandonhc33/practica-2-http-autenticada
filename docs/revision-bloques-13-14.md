# Revisión de los bloques 13 y 14

Fecha: 28 de octubre de 2026. Revisión de los seis PDF de Skillnest y del estado actual del proyecto, incluidos los cambios locales que ya existían.

> Revisión inicial, anterior a la implementación. Los pendientes de acumulación, pytest y ensayo real se resolvieron después; el estado final y sus evidencias están en [Entrega de los bloques 13 y 14](entrega-bloques-13-14.md). Las cifras y propuestas que siguen conservan el diagnóstico de partida.

**Resultado:** el bloque 13 está implementado en buena parte, pero al cliente general le falta el acumulado de costo por sesión y no encontré evidencia del ensayo real de HTTP 429. El bloque 14 ya tiene una base amplia de pruebas automatizadas con `unittest` y mocks; falta configurar `pytest` para alinearse con la actividad y probar el acumulador cuando se incorpore. Hay diferencias deliberadas entre el contrato del curso y el de este proyecto.

## 1. Qué enseña cada PDF

### Bloque 13: backoff y control de costo, operación por operación

Enseña a sustituir una espera fija por una espera que crece entre reintentos. El objetivo es dar margen al proveedor antes de volver a enviar una petición rechazada temporalmente.

Las piezas son:

- **Backoff exponencial:** duplicar la espera base después de cada fallo recuperable.
- **Techo:** limitar la parte exponencial para evitar esperas cada vez mayores.
- **Jitter:** agregar una variación aleatoria para separar los reintentos de distintos clientes.
- **Costo por operación:** estimar el importe con los tokens reportados por el proveedor y las tarifas del modelo.
- **Acumulado de sesión:** conservar la suma entre llamadas, en lugar de devolver únicamente el costo individual.

El ejemplo usa una tarifa referencial única y `usageMetadata.totalTokenCount`. También señala que deben adaptarse las tarifas y la lectura de metadatos al proveedor y al formato utilizados. Propone una variable global para la miniaplicación y una clase cuando se necesite separar sesiones.

### Bloque 13: provocar un rate limit a propósito

Es una práctica de integración manual: enviar consultas reales hasta observar un HTTP 429, revisar las esperas y el resultado final, y documentar el ensayo.

La evidencia solicitada incluye fecha, peticiones enviadas, primera aparición del 429, esperas observadas, costo conocido del ensayo y resultado final. Una prueba con respuestas simuladas demuestra la lógica del programa, pero no acredita haber realizado este ensayo real.

### Bloque 13: límites y costos incorporados al cliente

Reúne cuatro responsabilidades: `enviar_peticion`, `con_reintento`, `registrar_costo` y `consultar_modelo`. Su enseñanza principal es que cada responsabilidad tenga un lugar claro y que quien consulta el cliente reciba una interfaz sencilla.

El checklist de cierre pide backoff con techo y jitter, costo individual y acumulado, ensayo real documentado y un error final comprensible al agotar reintentos.

### Bloque 14: qué es una prueba unitaria

Enseña a ejecutar una pieza real de código con una entrada conocida y comprobar su salida o excepción mediante una aserción. Introduce `pytest` como ejecutor y `unittest.mock` para reemplazar la comunicación con el proveedor.

Un mock permite decidir que la API responda 401, 429 o 200 sin depender de Internet ni consumir tokens. La función del cliente sigue ejecutándose; solo se sustituye la dependencia externa. También hay que comprobar el camino exitoso, no únicamente los fallos.

### Bloque 14: checklist del cliente modular

Pide cubrir los escenarios de cada responsabilidad:

| Responsabilidad | Escenarios del material |
| --- | --- |
| Enviar la petición | 401/403, 429/5xx y devolución del JSON exitoso. |
| Reintentar | Recuperación de un error temporal, propagación de errores permanentes y agotamiento de intentos. |
| Registrar costo | Cálculo con tokens conocidos y suma al acumulado de sesión. |
| Consultar el modelo | Error final comprensible tras agotar intentos y propagación de errores permanentes. |

También pide simular las esperas y usar nombres de prueba que describan el escenario. El ejemplo final de siete pruebas es ilustrativo: contar siete pruebas no demuestra por sí solo que todos los casos estén cubiertos.

### Bloque 14: actividad core

Pide construir y ejecutar la suite completa con `pytest`, usar mocks para API y tiempo, aislar el estado entre pruebas y declarar la dependencia de pruebas para que otra persona pueda reproducir la ejecución.

La fixture que reinicia el costo global enseña **aislamiento**: el resultado de una prueba no debe depender de cuál se ejecutó antes. En este proyecto, `setUp`, `enterContext`, limpieza de cachés y objetos nuevos por prueba ya cumplen esa función para el estado existente.

## 2. Cómo se corresponden los ejemplos con este proyecto

No hace falta renombrar funciones ni reunir todo en un `cliente.py`. La correspondencia de responsabilidades es:

| Ejemplo del curso | Implementación actual |
| --- | --- |
| `enviar_peticion` | [`_enviar_peticion`](../src/agente_gemini.py), un intento HTTP. |
| `con_reintento` | [`con_reintento`](../src/reintentos.py), con `PoliticaReintento`. |
| `registrar_costo` | [`extraer_uso`](../src/agente_gemini.py) y [`calcular_costo_gemini`](../src/costos.py), para leer consumo y calcular el costo individual. Falta la parte de acumulación del cliente general. |
| `consultar_modelo` | [`consultar_gemini_raw` y `consultar_gemini`](../src/agente_gemini.py), con traducción del error en la [API](../src/api.py) y el CLI. |

El proyecto usa el endpoint de Gemini compatible con OpenAI. Por eso lee `usage.prompt_tokens`, `usage.completion_tokens` y `usage.total_tokens`; pegar literalmente el acceso a `usageMetadata.totalTokenCount` no serviría para este contrato.

### Estado del bloque 13

| Requisito | Estado | Evidencia y observaciones |
| --- | --- | --- |
| Clasificación de autenticación y errores temporales | Implementado con otro contrato | `_enviar_peticion` distingue `ErrorAutenticacion`, `ErrorPeticion`, `ErrorTemporalProveedor` y errores de lectura/respuesta. |
| Backoff exponencial | Implementado | `con_reintento` duplica la espera base. |
| Techo y jitter | Implementado | Base máxima de 8 segundos y jitter configurable de 0 a 0,25 segundos por defecto. El jitter se suma después del techo y de `Retry-After`. |
| Límite de intentos | Implementado | Tres intentos totales por defecto: primera petición y hasta dos reintentos. |
| Consideración de `Retry-After` y tiempo disponible | Implementado | Acepta segundos o fecha HTTP y no adelanta el reintento si la espera no cabe en el presupuesto. Son capacidades adicionales al ejemplo básico. |
| Uso y costo por consulta normal | Implementado | `extraer_uso`, `calcular_costo_gemini` y `Resultado` publican tokens y costo estimado. Usan `Decimal`, distinguen entrada, caché y salida, y contemplan conversión a CLP. |
| Acumulado de sesión del cliente general | Pendiente | No existe un registro compartido entre consultas normales. `test_costos_corresponden_a_cada_consulta` verifica el costo individual de dos respuestas, no su suma. |
| Ensayo real de HTTP 429 documentado | Sin evidencia encontrada | Las pruebas simulan 429. No encontré el registro del ensayo solicitado ni un error 429 registrado como resultado en las evidencias JSON revisadas. |
| Error final comprensible | Implementado con otro contrato | `ReintentosAgotados` conserva intentos y última causa; la API lo traduce a 503 o 504 según corresponda. No es el `RuntimeError` literal del ejemplo. |

El [comparador de modelos](../src/comparar_modelos.py) sí calcula `costo_observado_total_usd` y `costo_observado_total_clp` sobre sus mediciones. Ese resumen de una evaluación no constituye un acumulador reutilizable de la sesión del cliente general.

El modo `raw` conserva deliberadamente el JSON del proveedor y no calcula costos ni consulta el dólar. Esa distinción está documentada y probada.

### Estado del bloque 14

| Escenario | Pruebas actuales | Evaluación |
| --- | --- | --- |
| 401/403 no se reintentan | `test_estados_permanentes_no_se_reintentan_ni_exponen_el_cuerpo`, en [cliente resiliente](../tests/test_cliente_resiliente.py) | Cubierto mediante `ErrorAutenticacion`. |
| 429 y errores temporales se recuperan | `test_estados_temporales_se_recuperan_con_una_segunda_llamada`, en cliente resiliente | Cubre 429, 500, 502, 503 y 504. |
| Respuesta exitosa conserva JSON | `test_devuelve_todos_los_campos_del_proveedor_sin_transformarlos`, en [consultas raw](../tests/test_consultas_raw.py) | Cubierto por integración simulada. |
| Reintentar y esperar entre intentos | `test_recuperacion_respeta_backoff_jitter_y_presupuesto_restante`, en [reintentos](../tests/test_reintentos.py) | Cubierto con reloj, espera y aleatoriedad simulados. |
| Error permanente se propaga sin repetir | `test_errores_permanentes_y_cancelacion_se_propagan_sin_reintentar`, en reintentos | Comprueba también la identidad del error original. |
| Agotamiento de intentos | `test_agotamiento_conserva_ultima_causa_sin_esperar_despues_del_ultimo`, en reintentos | Cubierto con `ReintentosAgotados`; guarda el objeto original en `ultimo_error`. |
| Cálculo de costo conocido | [Pruebas de costos](../tests/test_costos.py), [consultas](../tests/test_consultas.py) y [comparador](../tests/test_comparar_modelos.py) | Cubierto. Incluye caché, razonamiento, consumo ausente y valores pequeños. |
| Suma al costo de sesión | No existe todavía el acumulador general | Pendiente. |
| Traducción del fallo final al consumidor | `test_gemini_no_disponible_devuelve_503_tras_tres_intentos`, en [Gemini](../tests/test_gemini.py), y pruebas del CLI en cliente resiliente | Cubierto en los puntos de entrada con el contrato propio. |
| Propagación del error permanente al consumidor | Pruebas de cliente resiliente y API | Cubierto en el recorrido actual. Puede añadirse una prueba unitaria directa de la fachada si se necesita mostrar explícitamente su contrato Python. |
| API y tiempo simulados | [Preparación compartida](../tests/base.py) y pruebas de reintentos | Implementado. También se simula el servicio del dólar. |
| Ejecución con `pytest` declarado como dependencia | No está en `pyproject.toml`, `uv.lock`, `requirements.txt` ni en el entorno revisado | Pendiente para la entrega que pide el curso. |

La suite mezcla pruebas unitarias y pruebas de integración local con servicios simulados. Una prueba con `TestClient` comprueba varias capas de la aplicación; no es una prueba unitaria aislada, aunque tampoco necesita llamar a Google.

## 3. Verificación ejecutada

Se ejecutaron las 129 pruebas de `tests/` mediante descubrimiento de `unittest`, usando el Python 3.12 del entorno del proyecto y bloqueando conexiones externas a nivel de sockets.

| Comprobación | Resultado |
| --- | --- |
| Suite completa | 129 pruebas correctas, 0 fallos, 0 errores y 0 omitidas. |
| Tiempo del ejecutor de pruebas | 0,941 segundos en esta ejecución. |
| Intentos de conexión externa interceptados | 0. |
| `ruff check src tests prompts` | Correcto. |
| `basedpyright` | 0 errores y 0 advertencias. |

De esas pruebas, 17 corresponden al módulo de reintentos, 14 al cliente resiliente y 9 a costos. El resto comprueba autenticación, API, contratos, prompts, configuración, evaluadores y otras partes del proyecto. El número total no sustituye el análisis de los escenarios pendientes.

El comando habitual ya documentado para repetir la suite es:

```bash
uv run python -m tests -v
```

Estas comprobaciones se hicieron sobre el código actual. No se ejecutó un ensayo real de rate limit ni se instalaron dependencias nuevas para esta revisión.

## 4. Cómo completar lo pendiente

### 4.1. Incorporar el registro de costo por sesión

Conservar el cálculo actual y añadir una responsabilidad de registro, por ejemplo en `src/registro_costos.py`. La sesión debe tener un alcance explícito: una ejecución de un ensayo o cliente; si se comparte una instancia en la API, su acumulado será del proceso, no automáticamente de cada usuario.

Un núcleo posible es el siguiente. Es código propuesto, todavía no incorporado al proyecto:

```python
from decimal import Decimal
from threading import Lock


class RegistroCostosSesion:
    def __init__(self) -> None:
        self._lock = Lock()
        self._total_usd = Decimal("0")
        self._respuestas_con_costo = 0
        self._respuestas_sin_costo = 0

    def registrar(self, costo_usd: Decimal | None) -> None:
        with self._lock:
            if costo_usd is None:
                self._respuestas_sin_costo += 1
            else:
                self._total_usd += costo_usd
                self._respuestas_con_costo += 1

    def resumen(self) -> dict[str, Decimal | int]:
        with self._lock:
            return {
                "costo_conocido_usd": self._total_usd,
                "respuestas_con_costo": self._respuestas_con_costo,
                "respuestas_sin_costo": self._respuestas_sin_costo,
            }
```

El bloqueo permite compartir una instancia entre hilos. No coordina procesos distintos ni conserva el estado después de reiniciar. La creación de una instancia nueva también evita que una prueba herede el total de otra.

La integración debe resolver estos puntos:

1. **Separar cálculo y registro.** `calcular_costo_gemini` puede ser llamado por evaluadores o utilidades; darle efectos de acumulación provocaría dobles registros al recalcular. El registro debe ser una llamada explícita en un único lugar del recorrido de cada respuesta.
2. **Registrar consumo antes de validar el contenido generado.** Una respuesta HTTP 200 con JSON del proveedor válido puede contener texto truncado o una salida que no cumple el esquema, pero ya haber consumido tokens. Actualmente `consultar_gemini` extrae y valida el texto antes de calcular costo; para un registro completo, ese orden debe ajustarse.
3. **Mantener separado el costo USD de la consulta al dólar.** Para cubrir también el recorrido `raw`, conviene extraer un cálculo puro en USD a partir de modelo y uso, y registrar después de recibir el JSON en `consultar_gemini_raw`, fuera del bucle de reintentos. El recorrido normal puede enriquecer ese cálculo con CLP. Así `raw` sigue devolviendo el JSON intacto y no necesita una consulta adicional de tipo de cambio.
4. **Compartir la misma instancia donde corresponda.** Pasarla explícitamente desde el ensayo/cliente y propagarla al recorrido raw. Si se habilita en la API, definir su creación y alcance en el ciclo de vida de la aplicación. No volver a registrar la misma respuesta desde la fachada ni desde el evaluador.
5. **Conservar lo desconocido.** La suma se debe llamar costo conocido o estimado, no factura total. Respuestas sin metadatos o modelos sin tarifa se cuentan por separado. Un timeout puede dejar consumo desconocido y requiere una anotación distinta de una respuesta recibida sin costo calculable.
6. **Presentar el resultado sin mezclar formatos.** Sumar los `Decimal` internos, no cadenas como `"US$ 0.0053"`. Mantener el JSON exitoso del CLI y usar sus canales de salida documentados para avisos.

Para demostrar el requisito del curso, dos consultas con el mismo costo configurado de `Decimal("0.0053")` deben dejar `Decimal("0.0106")` en el acumulado. Son valores de prueba basados en las tarifas del repositorio, no una cotización nueva.

Las pruebas necesarias del registro y su integración son: suma de dos respuestas, independencia entre sesiones, cero reportado frente a costo desconocido, recuperación 429→503→200 sin doble registro y contabilización del consumo recibido aunque después falle la validación del contenido. Los errores sin respuesta no deben inventar importes.

### 4.2. Configurar pytest sin reescribir la suite existente

`pytest` puede ejecutar clases derivadas de `unittest.TestCase`. Por eso no hace falta convertir las 129 pruebas ni cambiar su ubicación.

Los pasos propuestos son:

```bash
uv add --dev pytest
uv run python -m pytest tests -v
```

El primer comando declararía la dependencia de desarrollo y actualizaría el archivo de bloqueo. La configuración puede delimitar el descubrimiento a las pruebas automáticas:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

Si la entrega exige literalmente `requirements.txt` con pytest incluido, exportar también el grupo de desarrollo desde el lockfile, en lugar de escribir a mano versiones distintas:

```bash
uv export --frozen --group dev --no-hashes --no-emit-project --output-file requirements.txt
```

Esa exportación incluiría además las otras dependencias de desarrollo. Si se prefiere mantener un archivo exclusivo de ejecución, se puede generar `requirements-dev.txt` y documentar su instalación; esa variante debe corresponder con lo que acepte la entrega.

Una prueba directa de `calcular_costo_gemini` en este repositorio sí necesita sustituir `src.costos.obtener_tipo_cambio`, porque el cálculo actual puede consultar la red para convertir a CLP. La afirmación del PDF de que la función de costo no necesita mocks describe su ejemplo sencillo. Separar el cálculo puro USD evita esa dependencia en sus pruebas unitarias.

### 4.3. Documentar las diferencias de contrato

El curso usa `ValueError`, `TimeoutError` y `RuntimeError` como categorías didácticas. Este proyecto tiene clases específicas:

- `ErrorAutenticacion` para credenciales o permisos del proveedor.
- `ErrorTemporalProveedor` para fallos recuperables.
- `ReintentosAgotados` para el final de la política, con su última causa.
- Traducción a respuestas HTTP y mensajes del CLI en los puntos de entrada.

Es una diferencia de diseño, no evidencia de ausencia de manejo de errores. Sin embargo, una prueba copiada del PDF que espere literalmente `RuntimeError` no pasará con esas clases: no heredan de ese tipo. La entrega debe explicar las equivalencias. Si el evaluador exige las firmas y excepciones exactas del ejemplo, haría falta una capa de compatibilidad y sus pruebas.

Otra diferencia deliberada es la lista temporal: el material simplifica a todo estado 500 o superior; el proyecto reintenta 500, 502, 503 y 504, y trata 501/505 como permanentes. Ambos comportamientos están probados. No conviene cambiar esa decisión únicamente para hacer coincidir un ejemplo genérico.

### 4.4. Realizar y documentar el ensayo real

La práctica del bloque 13 es independiente de la suite automática. Para completarla, preparar un script manual de consultas breves con un número máximo de envíos y presupuesto definidos. Debe conservar la política actual y mostrar el resumen del registro de costos al terminar.

Registrar los envíos HTTP realmente realizados, no solo el número de consultas del bucle: una consulta puede generar varios intentos. Anotar cuándo aparece el primer 429, pausas, recuperación o agotamiento y costo conocido. Si una tanda no recibe 429, documentar ese resultado sin presentarlo como el ensayo de rate limit completado.

La evidencia podría quedar en `docs/ensayo-rate-limit.md` con fecha, modelo, límites configurados, consultas, intentos HTTP, primer 429, esperas y resultado. La suite con mocks seguiría comprobando los fallos sin repetir este consumo real.

## 5. Precisiones del material para aplicarlo bien

- **Tres intentos no son tres reintentos.** Con tres intentos totales hay como máximo dos esperas: con base 2, serían aproximadamente 2 y 4 segundos más jitter. Para observar también la espera de 8 segundos hacen falta al menos cuatro intentos.
- **El techo limita la base en los ejemplos.** El código suma jitter después; la pausa final puede superar ligeramente ese techo. El proyecto hace lo mismo y respeta además `Retry-After`.
- **Una operación fallida no demuestra consumo cero.** Un timeout puede ocurrir después de que el proveedor procese el POST; una salida inválida o truncada también puede tener tokens reportados. El README del proyecto ya reconoce el consumo desconocido de intentos sin respuesta.
- **La aleatoriedad puede controlarse en una prueba.** El PDF desaconseja comparar una espera aleatoria exacta. Aquí `uniform` se sustituye por un valor fijo, así que las comprobaciones exactas existentes son deterministas y útiles.
- **Se sustituye el nombre donde se utiliza.** Las rutas adecuadas aquí son `src.agente_gemini.requests.post`, `src.reintentos.sleep` y `src.reintentos.uniform`. El módulo importa `sleep` directamente, no utiliza `time.sleep`.
- **Los archivos de código y pruebas pueden estar en carpetas distintas.** La estructura `src/` y `tests/` del proyecto funciona con sus paquetes e importaciones. Tener todo junto es una simplificación de la actividad.
- **Backoff no garantiza recuperar cualquier cuota.** Gemini distingue límites por minuto y por día, entre otros; una espera breve no garantiza recuperar una cuota diaria agotada.
- **Los PDF tienen fragmentos recortados.** La inspección visual confirmó líneas de código y párrafos cortados por el borde derecho, especialmente en el cierre del bloque 13. No deben copiarse como si fueran archivos completos ejecutables.

## 6. Relación con el PRD existente

El [PRD 01 de control de consumo](prd-01-control-consumo-gemini.md) figura como propuesto y pendiente. Plantea espaciar envíos, limitar concurrencia y compartir pausas entre consultas del mismo modelo. Eso previene ráfagas antes de enviar, mientras el backoff actual reacciona después de ciertos fallos.

No encontré `src/limites.py` ni su controlador implementado. Es una ampliación útil, pero los seis PDF no exigen desarrollar todo ese PRD para terminar los bloques 13 y 14. El acumulado de costos tampoco equivale por sí solo a imponer un límite monetario de gasto.

## 7. Fuentes

Material del curso, leído íntegramente mediante extracción de texto y con inspección visual de las páginas relevantes:

1. [Bloque 13: backoff y costo por operación](</home/brandonhc/Downloads/b2b-accenture-especializacion-en-ia-2-octubre-2026_ Rate limits, backoff y registro de costo por operación (Bloque 13) _ Backoff y control de costo, operación por operación _ Skillnest.pdf>), 10 páginas.
2. [Bloque 13: ensayo de rate limit](</home/brandonhc/Downloads/b2b-accenture-especializacion-en-ia-2-octubre-2026_ Rate limits, backoff y registro de costo por operación (Bloque 13) _ Provocamos un rate limit a propósito, para aprender a manejarlo _ Skillnest.pdf>), 8 páginas.
3. [Bloque 13: cierre e integración](</home/brandonhc/Downloads/b2b-accenture-especializacion-en-ia-2-octubre-2026_ Rate limits, backoff y registro de costo por operación (Bloque 13) _ Límites de uso y registro de costo, ya incorporados al cliente _ Skillnest.pdf>), 11 páginas.
4. [Bloque 14: introducción a pruebas unitarias](</home/brandonhc/Downloads/b2b-accenture-especializacion-en-ia-2-octubre-2026_ Pruebas unitarias sobre el cliente modular (Bloque 14) _ Pruebas unitarias_ la prueba de que tu cliente funciona _ Skillnest.pdf>), 8 páginas.
5. [Bloque 14: checklist](</home/brandonhc/Downloads/b2b-accenture-especializacion-en-ia-2-octubre-2026_ Pruebas unitarias sobre el cliente modular (Bloque 14) _ Checklist de cliente modular_ qué se revisa _ Skillnest.pdf>), 8 páginas.
6. [Bloque 14: actividad core](</home/brandonhc/Downloads/b2b-accenture-especializacion-en-ia-2-octubre-2026_ Pruebas unitarias sobre el cliente modular (Bloque 14) _ Escribe tus pruebas unitarias y verifica que pasen [Actividad core] _ Skillnest.pdf>), 8 páginas.

Documentación primaria consultada:

- [Compatibilidad de pytest con unittest](https://docs.pytest.org/en/stable/how-to/unittest.html): permite ejecutar las clases existentes.
- [Dónde aplicar patch en unittest.mock](https://docs.python.org/3/library/unittest.mock.html#where-to-patch): explica el uso del nombre que consulta el módulo bajo prueba.
- [Dependencias de desarrollo en uv](https://docs.astral.sh/uv/concepts/projects/dependencies/#development-dependencies): documenta `uv add --dev pytest`.
- [Configuración de pytest](https://docs.pytest.org/en/stable/reference/customize.html#pyproject-toml): documenta la configuración mediante `pyproject.toml`.
- [Límites de Gemini](https://ai.google.dev/gemini-api/docs/rate-limits): distingue RPM, TPM y RPD y explica su alcance por proyecto.

La revisión añade únicamente este informe. La implementación y las dependencias propuestas en la sección 4 siguen pendientes.
