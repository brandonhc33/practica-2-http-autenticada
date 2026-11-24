"""Registro versionado de prompts: qué texto exacto produjo cada respuesta."""

import difflib
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

RAIZ = Path(__file__).resolve().parents[2]
RUTA_PROMPTS = RAIZ / "datos" / "gobernanza" / "prompts_rag.json"
RUTA_ACTIVO = RAIZ / "datos" / "gobernanza" / "prompt_activo.json"
NOMBRE_PROMPT = "rag_ley_rep"


def huella_prompt(sistema: str, humano: str) -> str:
    """Cubre los dos mensajes: cambiar cualquiera produce otra versión."""
    return hashlib.sha256(f"{sistema}\n---\n{humano}".encode()).hexdigest()[:12]


@dataclass(frozen=True)
class VersionPrompt:
    nombre: str
    huella: str
    sistema: str
    humano: str
    autor: str
    fecha: str
    nota: str
    modelo_probado: str | None
    evidencia: str | None

    def plantilla(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", self.sistema), ("human", self.humano),
        ])


class RegistroDePrompts:
    """Conserva las versiones en orden; no reemplaza ni borra las anteriores."""

    def __init__(self, versiones: list[VersionPrompt] | None = None):
        self.versiones: list[VersionPrompt] = []
        for version in versiones or []:
            self._agregar(version)

    def _agregar(self, version: VersionPrompt) -> None:
        if huella_prompt(version.sistema, version.humano) != version.huella:
            raise ValueError(f"La huella {version.huella} no corresponde a su texto.")
        if any(v.huella == version.huella for v in self.versiones):
            raise ValueError(f"La versión {version.huella} ya está registrada.")
        self.versiones.append(version)

    def registrar(
        self, nombre: str, sistema: str, humano: str, autor: str, fecha: str, nota: str,
        modelo_probado: str | None = None, evidencia: str | None = None,
    ) -> VersionPrompt:
        version = VersionPrompt(
            nombre, huella_prompt(sistema, humano), sistema, humano, autor, fecha, nota,
            modelo_probado, evidencia,
        )
        self._agregar(version)
        return version

    def ultima(self, nombre: str) -> VersionPrompt | None:
        candidatas = [v for v in self.versiones if v.nombre == nombre]
        return candidatas[-1] if candidatas else None

    def buscar(self, huella: str) -> VersionPrompt:
        for version in self.versiones:
            if version.huella == huella:
                return version
        raise ValueError(f"No hay una versión registrada con la huella {huella}.")

    @classmethod
    def cargar(cls, ruta: Path = RUTA_PROMPTS) -> "RegistroDePrompts":
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return cls([VersionPrompt(**v) for v in datos["versiones"]])

    def guardar(self, ruta: Path = RUTA_PROMPTS) -> None:
        guardar_json(ruta, {"versiones": [asdict(v) for v in self.versiones]})


def guardar_json(ruta: Path, datos: dict[str, Any]) -> None:
    """Escribe en un temporal y reemplaza: una interrupción no deja un archivo a medias."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporal = tempfile.mkstemp(dir=ruta.parent, prefix=f".{ruta.name}-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
        os.chmod(temporal, 0o644)
        os.replace(temporal, ruta)
    except BaseException:
        Path(temporal).unlink(missing_ok=True)
        raise


def diff_prompts(anterior: VersionPrompt, nueva: VersionPrompt) -> list[str]:
    """Diferencia por líneas de los dos mensajes, como `git diff`."""
    return list(difflib.unified_diff(
        f"{anterior.sistema}\n---\n{anterior.humano}".splitlines(),
        f"{nueva.sistema}\n---\n{nueva.humano}".splitlines(),
        fromfile=anterior.huella, tofile=nueva.huella, lineterm="",
    ))


def leer_activo(ruta: Path = RUTA_ACTIVO) -> dict[str, Any]:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos.get("huella"), str):
        raise ValueError("El archivo de prompt activo no declara una huella.")
    return datos


def prompt_activo(
    ruta_prompts: Path = RUTA_PROMPTS, ruta_activo: Path = RUTA_ACTIVO,
) -> VersionPrompt:
    """Versión autorizada; si el puntero o el registro no cuadran, falla sin responder."""
    return RegistroDePrompts.cargar(ruta_prompts).buscar(leer_activo(ruta_activo)["huella"])
