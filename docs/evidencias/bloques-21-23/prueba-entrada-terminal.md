# Prueba de entrada interactiva sin Gemini

El alumno ejecutó esta prueba en su terminal y compartió la salida en la
conversación. No hubo llamadas a Gemini, entrega de informes ni registro de
aprobaciones de una entrega. El agente no respondió por él.

```python
import time
from src.orquestacion.supervision import esperar_aprobacion

for tecla in ("s", "n"):
    inicio = time.monotonic()
    resultado = esperar_aprobacion(
        f"Prueba local sin Gemini: escribe {tecla} y pulsa Enter",
        60,
    )
    segundos = time.monotonic() - inicio
    print(f"Resultado: {resultado}; espera: {segundos:.1f} s", flush=True)
```

Salida compartida:

```text
Prueba local sin Gemini: escribe s y pulsa Enter
¿Aprobar esta entrega simulada? [s/N] (límite: 60 s)
s
Resultado: True; espera: 4.5 s
Prueba local sin Gemini: escribe n y pulsa Enter
¿Aprobar esta entrega simulada? [s/N] (límite: 60 s)
n
Resultado: False; espera: 1.9 s
```

La función leyó dos respuestas consecutivas sin agotar el tiempo. No se reprodujo
el problema de entrada que el alumno reportó durante el segundo intento con Gemini.
Esta prueba no explica por sí sola aquel incidente ni sustituye el rechazo
explícito de un informe dentro del agente.
