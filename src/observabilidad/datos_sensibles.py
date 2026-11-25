"""Señales de datos personales o claves. Ayudan a revisar; no prueban que no existan."""

import re

PATRONES_SENSIBLES = {
    "correo": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "rut": re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b"),
    "telefono": re.compile(r"(?<!\d)(?:\+?56[\s-]?)?9[\s-]?\d{4}[\s-]?\d{4}(?!\d)"),
    "clave": re.compile(r"AIza[0-9A-Za-z_-]{20,}|(?i:bearer\s+[\w.-]{20,})"),
}


def detectar_datos_sensibles(texto: str) -> dict[str, int]:
    """Cuenta señales por tipo, sin devolver los valores encontrados."""
    conteos = {tipo: len(patron.findall(texto)) for tipo, patron in PATRONES_SENSIBLES.items()}
    return {tipo: n for tipo, n in conteos.items() if n}


def ocultar_datos_sensibles(texto: str) -> tuple[str, int]:
    """Reemplaza cada dato reconocido antes de enviarlo al proveedor o guardarlo."""
    total = 0
    for tipo, patron in PATRONES_SENSIBLES.items():
        texto, n = patron.subn(f"[{tipo} oculto]", texto)
        total += n
    return texto, total
