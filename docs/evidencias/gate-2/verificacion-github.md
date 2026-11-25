# Publicación e instalación — Gate 2

**25-11-2026 (UTC).** Merge `30e5a3d0cbfae86c079e090b4095689fa64e9b3f` en `main`, sin
conflictos y con el mismo contenido que la rama local. En GitHub solo existe `main`.

Clon nuevo desde GitHub, sin `.env` ni clave, en un entorno creado con `python -m venv` y
`pip install -r requirements.txt`:

| Comprobación | Resultado |
| --- | --- |
| `python servicio_rag.py` | 11 comprobaciones correctas |
| `python -m pytest test_gate2.py -v` | 4 aprobadas |
| `python -m pytest tests -q` | 453 pruebas y 759 subpruebas aprobadas |
| Huellas de evidencias y datos | 12 de 12 coinciden |
| `git check-ignore .env` | Ignorado |
| `git status` después de ejecutar | Limpio |
