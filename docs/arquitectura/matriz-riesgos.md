# Matriz de riesgos del asistente Ley REP

Actividad 32. Datos: [`matriz_riesgos.json`](../../datos/gobernanza/matriz_riesgos.json).
Cálculo y validación: [`scripts/matriz_riesgos.py`](../../scripts/matriz_riesgos.py).

**Estado:** estimaciones propuestas con asistencia de IA a partir de hechos del
repositorio y revisadas el 24-11-2026. La revisión mantuvo siete filas y subió la
probabilidad de «norma desactualizada» de 3 a 4: pasó de ALTO a CRITICO.

**Sistema evaluado:** RAG por terminal, agente supervisado y medición local, con una
sola norma indexada. Puntaje = probabilidad × impacto, de 1 a 5 cada uno. Cortes del
curso: CRITICO desde 15, ALTO desde 9, MEDIO desde 4.

| Riesgo | P | I | Puntaje | Categoría | Mitigación construida | Supervisión |
| --- | --- | --- | --- | --- | --- | --- |
| La respuesta cita un artículo que existe, pero cambia lo que dice | 4 | 4 | 16 | CRITICO | Citas obligatorias y existentes (B31); prompt que pide usar solo el contexto (B26) | Aprobar cada informe antes de entregarlo (B23) |
| Se presenta como vigente una norma modificada, anulada o que no está en el corpus | 4 | 4 | 16 | CRITICO | El prompt distingue la copia de una comprobación de vigencia (B26); abstención medida (B28) | Aprobar cada informe antes de entregarlo (B23) |
| Una consulta con datos personales queda guardada o se publica como evidencia | 3 | 5 | 15 | CRITICO | Eventos sin contenido (B31); salidas ignoradas por Git (B28); detección de datos sensibles (B32) | Aprobar cada registro real antes de copiarlo a las evidencias públicas (B32) |
| Un cambio de prompt sin revisar altera todas las respuestas | 3 | 4 | 12 | ALTO | Versiones con huella, nota y diff (B32); huella en cada traza (B31) | Aprobar la activación de cada versión (B32) |
| Un fragmento indexado contiene una orden para el modelo | 2 | 4 | 8 | MEDIO | Filtro de patrones (B31); índice comparado con el corpus (B25) | No requerida |
| El proveedor corta las llamadas por límite de frecuencia o no responde | 4 | 2 | 8 | MEDIO | Errores controlados (B31); continuación sin repetir (B30) | No requerida |
| El modelo de embeddings cambia o se retira y el índice deja de ser comparable | 2 | 3 | 6 | MEDIO | Manifiesto que rechaza otro modelo (B25) | No requerida |
| La clave de Gemini termina en el repositorio o en un registro | 1 | 5 | 5 | MEDIO | `.env` ignorado (B4); eventos con solo el tipo de error (B31) | No requerida |

## De dónde sale cada estimación

| Riesgo | Hecho que la respalda |
| --- | --- |
| Cita sin respaldo | Ocurrió: en los bloques 18 a 20 un paso quitó condiciones del artículo 33, y en el 21 la respuesta agregó «previamente» a una condición del artículo 34. |
| Datos personales | Las trazas del B23 y las mediciones del B28 guardan la consulta completa en archivos locales, y el repositorio es público. |
| Cambio de prompt | El prompt vivía como texto en el código. En los bloques 18 a 20 un cambio de redacción mejoró unas condiciones y perdió otras. |
| Norma desactualizada | El índice tiene una copia de 2016. Una sentencia de agosto de 2026 anuló el decreto de aceites y el sistema no lo sabe. Con más normas habrá más textos que pueden cambiar. |
| Inyección en un fragmento | El corpus es texto oficial con huella verificada. Sube si se agregan fuentes que otras personas puedan editar. En una [prueba](../evidencias/bloques-31-32/orden-escondida-resultado.md) el filtro no vio una orden y el modelo no la obedeció. |
| Límite de cuota | Ocurrió: la medición del B30 se detuvo en la consulta 17. |
| Embeddings | El índice depende de un modelo externo; mezclar vectores de dos modelos no da error por sí solo. |
| Clave expuesta | El repositorio es público, pero `.env` está ignorado y los errores del proveedor no se guardan. |

## Cómo leerla

- **Las ocho filas están al límite:** un punto más o menos en P o I cambia su
  categoría. La lección obtiene lo mismo con sus cinco ejemplos, porque los cortes
  están cerca. La categoría es una aproximación; conviene que otra persona revise
  las estimaciones.
- **Inyección es MEDIO y no CRITICO,** a diferencia del ejemplo de la lección: allí
  se indexan textos de usuarios; aquí, una sola ley oficial. Se vuelve a estimar al
  agregar fuentes.
- **La supervisión del B23 no cubre todo.** Se aplica al informe del agente. Una
  respuesta RAG directa solo tiene controles automáticos.
- **La aprobación de evidencias es un procedimiento:** no impide copiar a mano.

## Cuándo se actualiza

Al agregar una norma o una fuente, cambiar de modelo, exponer el RAG por la API o
después de un incidente. `uv run python -m scripts.matriz_riesgos` falla si una fila
ALTA o CRITICA queda sin supervisión o si una mitigación apunta a un archivo inexistente.
