# Evidencias de terminal: bloques 13 y 14

Capturas realizadas por Brandon Hernández el 28 de octubre de 2026. Se copiaron sin modificar su contenido ni resolución desde `/home/brandonhc/Pictures/Screenshots/evidencias/`. Los nombres nuevos indican el bloque y el orden de lectura. El [manifiesto](manifest.json) conserva los nombres originales, dimensiones y SHA-256 de cada copia.

## Bloque 13: backoff, límite de uso y costo acumulado

| Orden | Captura | Qué demuestra |
| --- | --- | --- |
| 1 | [Ensayo simulado](bloque-13/01-ensayo-simulado.png) | Respuesta inicial 200, secuencia 429→503→200, esperas simuladas de 1,125 y 2,125 segundos y acumulado de prueba US$ 0.0106. |
| 2 | [Ensayo real: comando e inicio](bloque-13/02-ensayo-real-inicio.png) | Comando con `--real`, modelo Flash-Lite, límites del ensayo y primeras respuestas con costo acumulado. |
| 3 | [Ensayo real: 429 y resultado](bloque-13/03-ensayo-real-resultado.png) | Tres intentos con HTTP 429 en la consulta 16, pausas de 1,172 y 2,008 segundos y cierre controlado con el resumen de consumo. |

Registros originales generados durante estas ejecuciones:

- [JSON del ensayo simulado](ensayo-simulado-01.json).
- [JSON del ensayo real](ensayo-real-01.json).

### Resultado del ensayo real

- Fecha local: 28 de octubre de 2026, de 22:13:34 a 22:14:19, America/Santiago.
- Modelo: `gemini-3.5-flash-lite`.
- Consultas: 16; 15 completadas y una fallida tras agotar sus tres intentos.
- Primer HTTP 429: primer intento de la consulta 16, envío número 16.
- Envíos HTTP: 18; los envíos 16, 17 y 18 recibieron HTTP 429.
- Esperas registradas: 1,172 y 2,008 segundos.
- Duración observada: 44,529 segundos.
- Consumo reportado: 171 tokens de entrada y 15 de salida; total 186.
- Costo conocido estimado: US$ 0.0000888.
- Intentos sin uso reportado: 3; su consumo se conserva como desconocido.

La consulta 16 no se recuperó dentro de los intentos permitidos. El JSON conserva `ReintentosAgotados` y su mensaje, mientras la captura muestra el cierre de la consulta y el acumulado de las 15 respuestas anteriores. Esto demuestra el manejo del agotamiento de reintentos. `primer_429_observado` indica que el ensayo encontró el error buscado; no significa que esa consulta haya terminado con éxito.

## Bloque 14: pruebas automatizadas del cliente modular

| Orden | Captura | Qué demuestra |
| --- | --- | --- |
| 1 | [Suite completa](bloque-14/01-suite-completa.png) | Ejecución de `pytest tests -q`: 152 pruebas y 389 subcasos correctos en 1,08 segundos. |
| 2 | [Checklist: comando y primeras pruebas](bloque-14/02-checklist-inicio.png) | Selección de los tres módulos del checklist, entorno de pytest y pruebas de transporte, fachada y reintentos. |
| 3 | [Checklist: continuación y resultado](bloque-14/03-checklist-resumen.png) | Pruebas de costo, aislamiento y ausencia de duplicados; resumen de 36 pruebas y 38 subcasos correctos en 0,32 segundos. |

Las dos capturas del checklist pertenecen a una misma ejecución y se complementan: la primera muestra el comando y la segunda el resultado completo.

## Estructura

```text
mis-capturas/
├── README.md
├── manifest.json
├── ensayo-real-01.json
├── ensayo-simulado-01.json
├── bloque-13/
│   ├── 01-ensayo-simulado.png
│   ├── 02-ensayo-real-inicio.png
│   └── 03-ensayo-real-resultado.png
└── bloque-14/
    ├── 01-suite-completa.png
    ├── 02-checklist-inicio.png
    └── 03-checklist-resumen.png
```

La [guía de entrega](../../entrega-bloques-13-14.md) usa estas capturas de terminal como evidencias principales y conserva la ejecución anterior como evidencia complementaria.
