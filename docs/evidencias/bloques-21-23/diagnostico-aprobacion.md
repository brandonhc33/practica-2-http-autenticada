# Diagnóstico del rechazo inmediato de la aprobación

## Incidente real conservado

Después de los dos intentos del ensayo completo, el alumno ejecutó una consulta
con la sesión `rechazo-manual-23`. Su salida de terminal mostró:

- Dos lecturas de respuesta del modelo antes de pedir aprobación y una después.
- El aviso de aprobación, pero ninguna `n` introducida por el alumno.
- Entrega no aprobada, sin guardar ni enviar el informe.
- Duración total aproximada de **7 segundos**, no 300.
- Consumo: 3 llamadas, 2.997 tokens de entrada, 460 de salida, 3.457 en total y
  USD 0,0020491.

La decisión de las 20:35:25 UTC se conserva como `aprobado: false`, con identificador
`799c166654244f259bbaa10de686a172`. Se comprobó que no existe su informe. La traza
correspondiente es de las 20:35:27 UTC. Ambos eventos se agregaron a las copias
versionadas sin alterar los cuatro casos ni las tres decisiones anteriores.

**No fue el timeout de 300 segundos.** El código anterior devolvía `false` sin
explicar si recibió Enter vacío, EOF, una entrada no afirmativa, perdió la terminal
o capturó una excepción. Los datos existentes no permiten elegir entre esas causas.
No se presenta esta corrida como rechazo explícito.

## Cambio de diagnóstico

`esperar_aprobacion` conserva el contrato booleano y la política de fallo seguro,
pero ahora muestra en stderr el motivo y el tiempo de espera. Distingue:

- `s` y `n` explícitas.
- Una línea vacía y una respuesta distinta de `s` o `n`, sin mostrar su contenido.
- EOF, entrada no interactiva, tiempo agotado y cancelación.
- Errores de terminal, con su tipo y mensaje.

El aviso también aclara que hay que escribir una letra y pulsar Enter: no es un
menú seleccionable con flechas o ratón. No se ignoran líneas vacías ni se aprueba
por defecto, y no se cambia el booleano de las decisiones antiguas.

El motivo se muestra en la terminal; los JSONL siguen guardando el booleano. No se
ha atribuido retroactivamente un motivo a los eventos anteriores.

## Diagnóstico interactivo sin Gemini

Desde el worktree:

```bash
uv run python -m tests.orquestacion.ensayo_terminal
```

No requiere `.env` ni clave, bloquea la red y desactiva trazas externas durante el
diagnóstico. Usa el modelo falso de las pruebas para recorrer memoria →
`AgentExecutor` → lectura local → `entregar_informe` → entrada humana. Los registros
y los posibles archivos simulados solo existen en una carpeta temporal que se
elimina al terminar. Ninguna respuesta autoriza una entrega real.

Solicita primero `s` y luego `n`, con 60 segundos por aviso. Al final debe mostrar:

```text
Decisiones simuladas: [true, false]
```

Si termina antes de dejar escribir, la línea `Resultado de aprobación:` indicará
la condición que hizo cerrar el aviso. Se necesita esa salida del alumno antes
de repetir una consulta pagada. Que funcione con el falso no descarta un problema
específico del SDK de Gemini o de la terminal en otra ejecución.

## Verificación automática

La suite incluye pruebas con pseudoterminal POSIX y un proceso Python independiente:

1. El agente recibe `s` y `n` consecutivas: registra `[true, false]` sin timeout.
2. Recibe Enter vacío y después `n`: registra `[false, false]` y explica que la
   primera decisión fue una línea vacía. Esto reproduce **una causa posible** de
   rechazo inmediato, no demuestra que fuera la del alumno.

También se prueban los diagnósticos de EOF, timeout y error de terminal, la no
exposición de una respuesta privada y el rechazo si stderr está cerrado.

Comprobaciones ejecutadas:

```text
uv run python -m pytest tests -v
263 passed, 11 warnings, 481 subtests passed

uv run ruff check .
All checks passed!

uv run basedpyright
0 errors, 0 warnings, 0 notes

uv run python -m tests -v
Ran 263 tests
OK
```

Los avisos son las deprecaciones ya documentadas de la memoria. Las pruebas de
pseudoterminal se omiten en plataformas no POSIX. No se hicieron nuevas llamadas
reales a Gemini durante este diagnóstico.

Las copias de evidencia se contrastaron otra vez con los archivos de operación:
5 eventos de traza y 4 decisiones, idénticos a sus originales. Los bytes de los
eventos ya guardados en `4605dda` se conservan como prefijo; solo se agregó el
control posterior. Los enlaces de la documentación y `git diff --check` también
pasaron.
