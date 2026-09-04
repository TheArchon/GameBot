from __future__ import annotations

from app.locales.loader import load
from .common import kb, btn


def trust_keyboard(game_id: int, language: str = "en") -> dict:
    b = load(language)["buttons"]
    return kb([[
        btn(b["trust"], f"trust:{game_id}:trust", "trust"),
        btn(b["betray"], f"trust:{game_id}:betray", "betray"),
    ]])
