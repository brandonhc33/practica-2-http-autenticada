# Matriz de riesgos del asistente Ley REP

Actividad 32. Datos: [`matriz_riesgos.json`](../../datos/gobernanza/matriz_riesgos.json).
Cálculo y validación: [`scripts/matriz_riesgos.py`](../../scripts/matriz_riesgos.py).

**Estado:** estimaciones propuestas con asistencia de IA a partir de hechos del
repositorio. Las ocho primeras se revisaron el 24-11-2026: se subió la probabilidad de
«norma desactualizada» de 3 a 4. La versión 2, para el Gate 2, conserva esos puntajes,
actualiza los controles y agrega «tabla mal transcrita», también revisada.

**Sistema evaluado:** servicio RAG con la Ley 20.920 y el DS 12/2020, agente supervisado y
medición local. Puntaje = probabilidad × impacto, de 1 a 5 cada uno. Cortes del curso:
CRITICO desde 15, ALTO desde 9, MEDIO desde 4. BS1 es el Gate 2.

| Riesgo | P | I | Puntaje | Categoría | Al límite | Mitigación construida | Supervisión |
| --- | --- | --- | --- | --- | --- | --- | --- |
| La respuesta cita un artículo que existe, pero cambia lo que dice | 4 | 4 | 16 | CRITICO | Sí | Citas obligatorias y existentes; si no, se abstiene (B31); Prompt que pide usar solo el contexto (B26); La fuente nombra norma y artículo (BS1) | Pausar con interrupt() la entrega de cada respuesta a un cliente, con el texto completo de sus fuentes |
| Se presenta como vigente una norma modificada, anulada o que no está en el corpus | 4 | 4 | 16 | CRITICO | Sí | El prompt distingue la copia de una comprobación de vigencia (B26); Abstención medida fuera del corpus (B28); El índice solo abre si coincide con las normas aprobadas; una norma se puede retirar (BS1) | Pausar con interrupt() la activación y el retiro de cada norma, y la entrega de cada respuesta |
| Una consulta con datos personales queda guardada o se publica como evidencia | 3 | 5 | 15 | CRITICO | Sí | Eventos con lista cerrada de campos, sin contenido (B31); Salidas locales ignoradas por Git (B28); Detección de correos, RUT, teléfonos y claves antes de publicar (B32); Ocultar correos, RUT, teléfonos y claves antes de enviar la consulta al proveedor (BS1) | Aprobar con interrupt() cada registro real antes de copiarlo a las evidencias públicas |
| Un cambio de prompt sin revisar altera todas las respuestas | 3 | 4 | 12 | ALTO | Sí | Versiones con huella, nota y diff (B32); La huella del prompt queda en cada traza (B31) | Aprobar la activación de cada versión con interrupt() |
| Una meta se responde con un número equivocado porque la tabla se transcribió o se cortó mal | 2 | 5 | 10 | ALTO | Sí | Transcripción en un archivo aparte, con página, huella y dos lecturas (BS1); Pruebas: ninguna fila cortada y ninguna meta baja de un año al siguiente (BS1) | Contrastar las tablas con la publicación antes de aprobar la norma con interrupt() |
| Un fragmento indexado contiene una orden para el modelo | 2 | 4 | 8 | MEDIO | Sí | Filtro de patrones antes del prompt (B31); Índice comparado con el corpus al abrirlo (B25) | No requerida |
| El proveedor corta las llamadas por límite de frecuencia o no responde | 4 | 2 | 8 | MEDIO | Sí | Errores controlados y estado explícito (B31); Continuación con pausa y sin repetir (B30) | No requerida |
| El modelo de embeddings cambia o se retira y el índice deja de ser comparable | 2 | 3 | 6 | MEDIO | Sí | Manifiesto que rechaza otro modelo o dimensión (B25) | No requerida |
| La clave de Gemini termina en el repositorio o en un registro | 1 | 5 | 5 | MEDIO | Sí | .env ignorado por Git (B4); Los eventos guardan solo el tipo de error (B31) | No requerida |

## De dónde sale cada estimación

| Riesgo | Hecho que la respalda |
| --- | --- |
| Cita sin respaldo | Ocurrió: en los bloques 18 a 20 un paso quitó condiciones del artículo 33, y en el 21 la respuesta agregó «previamente» a una condición del artículo 34. |
| Datos personales | Las trazas del B23 y las mediciones del B28 guardan la consulta completa en archivos locales, y el repositorio es público. |
| Cambio de prompt | El prompt vivía como texto en el código. En los bloques 18 a 20 un cambio de redacción mejoró unas condiciones y perdió otras. |
| Norma desactualizada | El índice tiene la copia de 2016 de la ley y la publicación de 2021 del DS 12. Una sentencia de agosto de 2026 anuló el decreto de aceites y una interpretación del DS 12 está en revisión: el sistema no lo sabe. |
| Tabla mal transcrita | Las cuatro tablas del DS 12 son imágenes. Dos lecturas con asistencia de IA coincidieron; el OCR confirmó solo parte. |
| Inyección en un fragmento | El corpus es texto oficial con huella verificada. Sube si se agregan fuentes que otras personas puedan editar. En una [prueba](../evidencias/bloques-31-32/orden-escondida-resultado.md) el filtro no vio una orden y el modelo no la obedeció. |
| Límite de cuota | Ocurrió: la medición del B30 se detuvo en la consulta 17. |
| Embeddings | El índice depende de un modelo externo; mezclar vectores de dos modelos no da error por sí solo. |
| Clave expuesta | El repositorio es público, pero `.env` está ignorado y los errores del proveedor no se guardan. |

## Cómo leerla

- **Las nueve filas están al límite:** un punto más o menos en P o I cambia su
  categoría. La lección obtiene lo mismo con sus cinco ejemplos, porque los cortes
  están cerca. La categoría es una aproximación; conviene que otra persona revise
  las estimaciones.
- **Inyección es MEDIO y no CRITICO,** a diferencia del ejemplo de la lección: allí
  se indexan textos de usuarios; aquí, dos normas oficiales que se aprueban antes de
  indexarlas. Se vuelve a estimar al agregar fuentes.
- **La acción de mayor riesgo es entregar una respuesta a un cliente.** El Gate 2 la pausa
  con `interrupt()` y muestra el texto completo de las fuentes. Antes solo se aprobaban los
  informes del agente (B23). Consultar en la terminal entrega un borrador, sin pausa.
- **La aprobación de evidencias es un procedimiento:** no impide copiar a mano.

## Cuándo se actualiza

Al agregar una norma o una fuente, cambiar de modelo, exponer el RAG por la API o
después de un incidente. `uv run python -m scripts.matriz_riesgos` falla si una fila
ALTA o CRITICA queda sin supervisión o si una mitigación apunta a un archivo inexistente.
