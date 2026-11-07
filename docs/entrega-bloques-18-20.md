# Entrega de los bloques 18, 19 y 20

Fecha: 6 de noviembre de 2026, America/Santiago.

Esta entrega agrega un flujo de terminal para consultas de Ley REP con LangChain: una chain de tres pasos, clasificación con tres rutas y manejo de errores por paso. La API, el cliente propio y los módulos de costos no cambian. El diseño completo está en el [PRD 02](prd-02-orquestacion-langchain.md) y el recorrido técnico en la [arquitectura](arquitectura.md#flujo-orquestado-bloques-18-a-20).

## Qué se incorporó

- [`src/orquestacion/modelo.py`](../src/orquestacion/modelo.py): `crear_modelo()` con un solo intento y 30 segundos por llamada, `RegistroLlamadas` para anotar cada llamada en el registro de costos y `exigir_texto()`, que convierte una respuesta vacía en error.
- [`src/orquestacion/cadena_tres_pasos.py`](../src/orquestacion/cadena_tres_pasos.py): plantillas de los pasos interpretar, responder y simplificar, y `construir_cadena()`.
- [`src/orquestacion/enrutamiento.py`](../src/orquestacion/enrutamiento.py): clasificación, `buscar_fragmento()`, rutas de resumen y aclaración, `construir_ruta_segura()`, `procesar_consulta_segura()` y entrada por terminal.
- [`tests/orquestacion/`](../tests/orquestacion/): 33 pruebas sin red, en `test_cadena_tres_pasos.py`, `test_enrutamiento.py` y `test_orquestacion.py`.
- `langchain` y `langchain-google-genai` declarados en `pyproject.toml`, `uv.lock` y `requirements.txt`.

## Correspondencia con las actividades del curso

| Bloque | Actividad | Archivos en este proyecto |
| --- | --- | --- |
| 18 | Chain de al menos tres pasos encadenados. | `src/orquestacion/cadena_tres_pasos.py`, `tests/orquestacion/test_cadena_tres_pasos.py`, `requirements.txt`. |
| 19 | Enrutamiento condicional incorporado a la chain. | `src/orquestacion/enrutamiento.py`, `tests/orquestacion/test_enrutamiento.py`. |
| 20 | Verificación de la chain de extremo a extremo. | `src/orquestacion/enrutamiento.py`, `tests/orquestacion/test_orquestacion.py` y este documento. |

Los nombres del ejemplo de soporte del curso se adaptaron a Ley REP:

| Material del curso | En este proyecto |
| --- | --- |
| `cadena_queja`, `cadena_pregunta` | `cadena_normativa`, `cadena_resumen` y `cadena_aclaracion`. |
| `construir_cadena_queja_segura` | `construir_ruta_segura`, que sirve para las tres rutas. |
| `procesar_mensaje_seguro` | `procesar_consulta_segura`. |
| `.strip().lower()` | `limpiar_texto()`, que además quita la puntuación. |
| `test_cadena_queja_usa_fallback_ante_fallo_del_modelo` | `test_cadena_normativa_usa_fallback_ante_fallo_del_modelo`. |

Las diferencias con el material están en la [sección 4.2 del PRD](prd-02-orquestacion-langchain.md#42-diferencias-con-el-material-del-curso). Los cambios respecto del PRD están en su [sección 4.3](prd-02-orquestacion-langchain.md#43-cambios-durante-la-implementación).

## Checklist del Bloque 20

### Las cuatro piezas de B20.2

| Pieza | Qué se revisa | Cobertura |
| --- | --- | --- |
| Clasificación | Categoría normalizada. | `test_clasificacion_normaliza_antes_de_comparar`. |
| Clasificación | Texto vacío o ambiguo. | `test_consulta_vacia_no_llama_al_modelo` y `test_enrutamiento_usa_default_ante_categoria_desconocida`. El paso puede devolver cualquier palabra normalizada: quien absorbe una categoría inesperada es la ruta por defecto. |
| Bifurcación | Una prueba por condición y por la ruta por defecto. | `test_enrutamiento_va_a_cadena_normativa`, `test_enrutamiento_va_a_cadena_resumen`, `test_enrutamiento_usa_default_ante_categoria_desconocida` y `test_resumen_sin_articulo_va_a_aclaracion`. |
| Cada ruta | Prompt realmente distinto. | `test_cada_ruta_usa_un_prompt_distinto`, `test_ruta_resumen_recibe_solo_su_fragmento` y `test_ruta_aclaracion_no_recibe_fragmentos`. |
| Cada ruta | `with_fallbacks` propio. | `main()` envuelve las tres rutas con `construir_ruta_segura()`. La prueba con fallo usa la ruta normativa (`test_cadena_normativa_usa_fallback_ante_fallo_del_modelo`); resumen y aclaración no tienen una prueba de fallo propia. |
| Flujo completo | Un fallo no deja sin respuesta. | `test_procesar_consulta_segura_no_propaga_excepciones` y `test_ruta_usa_texto_de_respaldo_si_fallan_ambos_modelos`. |
| Flujo completo | Resultado entendible y camino normal intacto. | `test_camino_normal_no_usa_respaldo` y `test_main_imprime_respuesta_y_consumo`. |

### Las cuatro preguntas de B20.3

| Pregunta | Respuesta | Prueba |
| --- | --- | --- |
| ¿La clasificación tiene una prueba de normalización, además de las de enrutamiento? | Sí. | `test_clasificacion_normaliza_antes_de_comparar`. |
| ¿Cada ruta tiene su prueba de enrutamiento, incluida la ruta por defecto? | Sí. | Las pruebas de CA-03 a CA-06. |
| ¿Al menos una ruta tiene un `with_fallbacks` probado, y la prueba confirma que se ejecutó? | Sí. | `test_cadena_normativa_usa_fallback_ante_fallo_del_modelo` comprueba tres llamadas al modelo secundario. |
| ¿El `try/except` general tiene una prueba de un fallo fuera de las rutas? | Sí. | `test_procesar_consulta_segura_no_propaga_excepciones` falla en la clasificación. |

## Criterios de aceptación

| ID | Escenario | Estado | Evidencia |
| --- | --- | --- | --- |
| CA-01 | Chain con modelo falso de tres respuestas. | Cubierto. | `test_cadena_conecta_los_tres_pasos`. |
| CA-02 | Normalización de la categoría. | Cubierto. | `test_clasificacion_normaliza_antes_de_comparar`. |
| CA-03 | Categoría `normativa`. | Cubierto. | `test_enrutamiento_va_a_cadena_normativa`. |
| CA-04 | Categoría `resumen` con artículo válido. | Cubierto. | `test_enrutamiento_va_a_cadena_resumen`. |
| CA-05 | Categoría inventada. | Cubierto. | `test_enrutamiento_usa_default_ante_categoria_desconocida`. |
| CA-06 | `resumen` sin artículo o con uno inexistente. | Cubierto. | `test_resumen_sin_articulo_va_a_aclaracion`. |
| CA-07 | Falla el modelo principal. | Cubierto con fallos simulados. | `test_cadena_normativa_usa_fallback_ante_fallo_del_modelo`. |
| CA-08 | Fallan ambos modelos. | Cubierto con fallos simulados. | `test_ruta_usa_texto_de_respaldo_si_fallan_ambos_modelos`. |
| CA-09 | Falla la clasificación. | Cubierto con fallos simulados. | `test_procesar_consulta_segura_no_propaga_excepciones`. |
| CA-10 | Texto vacío o solo espacios. | Cubierto. | `test_consulta_vacia_no_llama_al_modelo`. |
| CA-11 | Una llamada exitosa y una fallida. | Cubierto. | `test_registro_cuenta_respuestas_y_fallos`. |
| CA-12 | Modelo con clave ficticia. | Cubierto. | `test_crear_modelo_limita_reintentos_y_tiempo`. |
| CA-13 | Suite completa con la red bloqueada. | Cubierto. | 199 pruebas: las 166 previas y 33 nuevas. |
| CA-14 | Corrida real de las tres rutas. | Cubierto, con observaciones en la ruta normativa. | [Corrida final](#corrida-final): cada ruta respondió con el modelo principal y el consumo apareció en stderr. |

## Comprobaciones

Resultado del 6 de noviembre de 2026, sobre el commit `c7e98e2`:

| Comando | Resultado |
| --- | --- |
| `uv run python -m pytest tests -q` | 199 pruebas y 422 subcasos correctos. |
| `uv run python -m tests` | 199 pruebas correctas, ejecutado además en un espacio de red aislado. |
| `uv run ruff check .` | Correcto. |
| `uv run basedpyright` | 0 errores y 0 advertencias. |

Las mismas comprobaciones se repitieron el 7 de noviembre, sin cambios en `src/` ni `tests/`, y su salida quedó guardada en [pruebas de la chain](evidencias/bloques-18-20/pruebas-cadena.txt) (6), [pruebas de enrutamiento](evidencias/bloques-18-20/pruebas-enrutamiento.txt) (11), [pruebas de orquestación](evidencias/bloques-18-20/pruebas-orquestacion.txt) (16), [suite completa](evidencias/bloques-18-20/suite-completa.txt) (199), [`ruff`](evidencias/bloques-18-20/ruff.txt) y [`basedpyright`](evidencias/bloques-18-20/basedpyright.txt).

## Corridas reales

Las corridas de las fases 1 a 3 no guardaron sus salidas completas, así que de ellas solo se conservan las cifras. La de la Fase 4 sí quedó guardada. Los costos usan las tarifas de referencia del repositorio, no la facturación real.

| Corrida | Modelo | Llamadas | Tokens | Costo USD |
| --- | --- | --- | --- | --- |
| Fase 1: chain, consulta de neumáticos | flash-lite | 3 | 12.823 | 0,0050943 |
| Fase 2: 6 clasificaciones y 3 rutas | flash-lite | 14 | 15.091 | 0,0059771 |
| Prueba del paso 3 reforzado | flash-lite | 2 | 1.407 | 0,0015133 |
| Fase 3: ruta normativa, neumáticos | flash | 3 | 17.832 | 0,02943 |
| Fase 4: corrida final, tres rutas | flash-lite | 8 | 14.137 | 0,0057833 |
| **Total** | | **30** | **61.290** | **0,047798** |

Consulta de neumáticos: "Importo neumáticos a Chile y los vendo a talleres. ¿Qué obligaciones me impone la Ley REP y quién fija las metas que debo cumplir?"

- **Fase 1:** 275, 11.886 y 662 tokens por paso. Duró 6,7 s en total.
- **Fase 2:** 6 de 6 clasificaciones correctas, y las 3 corridas fueron a su ruta (9 de 9). Duró 82 s, sin medición por llamada. Por ruta: normativa 12.795 tokens, resumen 643 y aclaración 436.
- **Fase 3:** 6,8 s, 14,1 s y 9,7 s por paso. Salida de 5.352 tokens, contra 567 de flash-lite, y 5,8 veces su costo.

## Corrida final

El PRD pide "una corrida final" y CA-14 pide las tres rutas por el comando real. Se hicieron las tres rutas, con 8 llamadas (4 + 2 + 2), por terminal y en la carpeta de trabajo, no en el clon limpio. Las dos primeras se ejecutaron el 6 de noviembre a las 22:22 y la tercera el 7 de noviembre a las 11:44.

| Ruta | Consulta | Llamadas | Tokens (entrada / salida) | Costo USD | Salida |
| --- | --- | --- | --- | --- | --- |
| Normativa | "Importo neumáticos a Chile y los vendo a talleres. ¿Qué obligaciones me impone la Ley REP y quién fija las metas que debo cumplir?" | 4 | 12.910 (12.425 / 485) | 0,00494 | [Texto](evidencias/bloques-18-20/salida-normativa.txt), [captura](evidencias/mis-capturas/bloque-20/04-corrida-normativa.png). |
| Resumen | "Resume el artículo 9" | 2 | 782 (641 / 141) | 0,0005448 | [Texto](evidencias/bloques-18-20/salida-resumen.txt), [captura](evidencias/mis-capturas/bloque-20/05-corrida-resumen.png). |
| Aclaración | "Tengo una duda sobre mi empresa." | 2 | 445 (370 / 75) | 0,0002985 | [Texto](evidencias/bloques-18-20/salida-aclaracion.txt), [captura](evidencias/mis-capturas/bloque-20/06-corrida-aclaracion.png). |

Las 8 llamadas usaron `gemini-3.5-flash-lite`, respondieron HTTP 200 y no hubo fallos: el fallback no actuó. Por paso, la ruta normativa usó 222 tokens en la clasificación, 279 en interpretar, 11.817 en responder y 592 en simplificar. El prompt de la terminal mostró 13 s para la ruta normativa y 8 s para la de aclaración; la duración de la de resumen no quedó visible.

Revisión de cada salida contra la copia local de la ley:

- **Normativa:** enumera las obligaciones de las letras a) a d) del artículo 9 y liga la letra b) a la entrada en vigencia del decreto supremo, como dice la ley. Tiene tres problemas:
  - **Registro:** dice "Inscribirse en el registro correspondiente, según el Artículo 9, letra a." y omite que es el registro del artículo 37. La salida del paso 2 no se imprime, así que no se puede saber si lo perdió el paso 3 o si ya faltaba antes.
  - **Metas:** atribuye la fijación de metas a "los Artículos 4 y 12". El artículo 12 lo respalda; el artículo 4 trata de instrumentos de prevención y valorización, no de metas.
  - **Faltantes:** no advierte qué falta para el caso, por ejemplo si el decreto de neumáticos ya rige o si el importador queda comprendido como productor. Además, la letra c) pierde que los plazos y condiciones vienen del "respectivo decreto supremo".
- **Resumen:** corresponde al artículo 9 y cierra con lo que el fragmento no permite concluir: los productos prioritarios y las metas dependen de decretos supremos.
- **Aclaración:** no afirma nada sobre la ley y hace tres preguntas para obtener antecedentes.

## Ensayo de instalación limpia

- **Fecha:** 6 de noviembre de 2026.
- **Forma:** clon local de la rama `bloques-18-20` en una carpeta temporal, porque la rama aún no está en GitHub. El clon contenía el commit `c7e98e2`, sin la documentación de esta fase.
- **Instalación con `uv sync --locked`:** 199 pruebas y 422 subcasos correctos, `ruff` correcto y `basedpyright` con 0 errores.
- **Instalación con `python3 -m venv` y `pip install -r requirements.txt`, como en B11.2:** Python 3.12.13, `pip check` sin conflictos y 199 pruebas correctas.
- **Sin clave:** el comando terminó con `Falta configurar GEMINI_API_KEY en el archivo .env.`
- **Seguridad:** `git status` sin cambios; `.env`, `.venv/` y `venv/` quedaron ignorados.
- **Hallazgos:** ninguno que requiera corrección.
- **Sin verificar:** la corrida real no se hizo desde el clon, así que el paso 5 de B11.2 (crear `.env` desde `.env.example` y ejecutar con la clave) no quedó probado en la carpeta limpia. Además, el ensayo usó la misma máquina y la misma caché de paquetes: es una aproximación, como advierte B11.2.

## Capturas

Capturas de terminal tomadas por el autor, copiadas a `docs/evidencias/mis-capturas/` sin modificar. El índice `mis-capturas/README.md` y su manifiesto corresponden a los bloques 13 y 14 y no se modificaron; por eso aquí se conserva el origen de cada copia.

| Captura | Qué demuestra | Original | SHA-256 |
| --- | --- | --- | --- |
| [Pruebas de la chain](evidencias/mis-capturas/bloque-18/01-pruebas-cadena.png) | 6 pruebas y 6 subcasos correctos. | `Screenshot_20261107_155358.png` | `ec1ab008387052c1…` |
| [Pruebas de enrutamiento](evidencias/mis-capturas/bloque-19/01-pruebas-enrutamiento.png) | 11 pruebas y 21 subcasos correctos, con una prueba por ruta y la de normalización. | `Screenshot_20261107_155412.png` | `8f8c701337b670a0…` |
| [Pruebas de orquestación](evidencias/mis-capturas/bloque-20/01-pruebas-orquestacion.png) | 16 pruebas y 6 subcasos correctos, con fallbacks, entrada segura y registros. | `Screenshot_20261107_155431.png` | `5d567957332b43b4…` |
| [Suite completa](evidencias/mis-capturas/bloque-20/02-suite-completa.png) | 199 pruebas y 422 subcasos correctos. | `Screenshot_20261107_155448.png` | `3f0053baff029460…` |
| [Calidad del código](evidencias/mis-capturas/bloque-20/03-calidad.png) | `ruff` correcto y `basedpyright` con 0 errores. | `Screenshot_20261107_155505.png` | `dd4a33c7b5159f20…` |
| [Corrida normativa](evidencias/mis-capturas/bloque-20/04-corrida-normativa.png) | Cuatro llamadas a flash-lite con HTTP 200, respuesta en viñetas y consumo de US$ 0,00494. | `Screenshot_20261106_222247.png` | `4eff4df136af6623…` |
| [Corrida de resumen](evidencias/mis-capturas/bloque-20/05-corrida-resumen.png) | Dos llamadas, resumen del artículo 9 y consumo de US$ 0,0005448. | `Screenshot_20261106_222313.png` | `d815a8fc13f56377…` |
| [Corrida de aclaración](evidencias/mis-capturas/bloque-20/06-corrida-aclaracion.png) | Dos llamadas, tres preguntas de aclaración y consumo de US$ 0,0002985. | `Screenshot_20261107_114458.png` | `7ab5e91fcf6f2f24…` |

## Límites

1. **Registros:** los registros incluyen el cuerpo de error del proveedor; no se ha verificado con errores reales si alguno repite la consulta.
2. **Modelo secundario:** `gemini-3.6-flash` tuvo tres HTTP 503 en nueve intentos y 16 s de latencia media en la [evaluación del Bloque 9](decision-arquitectura.md#alternativa-descartada-y-por-qué). Una sola corrida por LangChain no descarta que supere los 30 s. Costó 5,8 veces más que flash-lite, mientras el riesgo 3 del PRD solo menciona la tarifa. Esa cifra es de esta corrida; el Bloque 9 midió unas 15,9 veces con preguntas breves y sin contexto de la ley.
3. **Fallback sin fallo real:** nunca se activó con un fallo real de Gemini. Tampoco se vieron reales el `timeout`, un bloqueo del proveedor ni un HTTP 429. Todo eso está probado solo con fallos simulados.
4. **Paso 3 antes del refuerzo:** quitó "establecido en el artículo 37" y, en el artículo 33, dejó obligaciones como incondicionales ("Deben aceptar gratis...").
5. **Paso 3 después del refuerzo:** se probó solo con dos salidas reales del paso 2. Conserva el artículo 37 y liga el artículo 33 a los decretos, pero pierde "cuyas instalaciones tengan una determinada superficie", cambia "no podrá supeditarse" por "siempre que...no se supedite" y simplifica muy poco. La plantilla no se siguió ajustando con tan pocos casos.
6. **Citas sin validar:** la chain produce texto libre y nada verifica que un artículo citado respalde la afirmación. `flash` citó el artículo 3 N° 21 letra c) ("para su propio uso profesional"), que no aplica a quien vende a talleres. También dijo "la ley te considera productor" sin aclarar que el decreto determina a qué productores se aplica. El paso 2 escribió un título en inglés.
7. **Clasificación:** 9 aciertos no miden estabilidad, no se puede fijar la temperatura y no se probaron casos límite.
8. **Búsqueda de artículos:** una consulta como "los artículos 9 y artículo 10" se resuelve como artículo 10.
9. **Nivel `DEBUG`:** no se verificó con peticiones reales. Además, `main()` fija el nivel `INFO`, así que el comando de terminal no muestra la traza sin cambiar el código.
10. **Ruta normativa en la corrida final:** omitió el artículo 37, citó el artículo 4 como fuente de las metas y no advirtió lo que falta para el caso. Con una sola corrida no se puede saber en qué paso se perdió el artículo 37.
11. **Motivo de D-03 desactualizado:** en `google-genai` 2.34.0, `attempts=0` también es un solo intento. `StrOutputParser` entrega `TextAccessor`, subclase de `str`.
12. **Cuota:** una consulta normativa usa 4 llamadas, y 7 en el peor caso. El [riesgo 1 del PRD](prd-02-orquestacion-langchain.md#11-riesgos-y-limitaciones) explica cuántas consultas seguidas alcanzarían el primer HTTP 429 observado.

## Cómo repetir la verificación

Desde la raíz del repositorio:

```bash
uv sync --locked
uv run python -m pytest tests -v
uv run python -m pytest tests/orquestacion -v
uv run ruff check .
uv run basedpyright
```

Las pruebas no usan red ni consumen tokens. Este comando sí consulta a Gemini, requiere `GEMINI_API_KEY` y consume cuota: 4 llamadas en la ruta normativa y 2 en las otras.

```bash
uv run python -m src.orquestacion.enrutamiento "Resume el artículo 9"
```

La respuesta sale por stdout y el resumen de consumo por stderr.
