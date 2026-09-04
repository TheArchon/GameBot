from __future__ import annotations

from app.locales.loader import load
from .common import kb, btn


def profile_keyboard(language: str = "en") -> dict:
    b = load(language)["buttons"]
    return kb([
        [btn(b["leaderboard"], "leaderboard", "leaderboard"), btn(b["wallet"], "wallet", "wallet")],
        [btn(b["language"], "language", "language"), btn(b["home"], "home", "home")],
    ])
