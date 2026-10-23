"""Punto de entrada del banco: reúne los grupos de prompts disponibles."""

from .base import NombrePrompt, Prompt
from .educativos import PROMPTS_EDUCATIVOS
from .ley_rep import PROMPTS_LEY_REP

__all__ = ["BANCO_DE_PROMPTS", "NombrePrompt", "Prompt"]

BANCO_DE_PROMPTS: dict[NombrePrompt, Prompt] = {
    **PROMPTS_EDUCATIVOS,
    **PROMPTS_LEY_REP,
}
