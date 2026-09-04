from __future__ import annotations

from app.locales.loader import load
from .common import kb, btn


def help_keyboard(page: int, language: str = "en", total: int = 5) -> dict:
    page = max(1, min(total, int(page)))
    b = load(language)["buttons"]
    row: list[dict] = []
    if page > 1:
        row.append(btn(b["prev"], f"help:{page - 1}", "prev"))
    row.append(btn(b["page"].format(page=page), "noop", "page"))
    if page < total:
        row.append(btn(b["next"], f"help:{page + 1}", "next"))
    return kb([row, [btn(b["home"], "home", "home")]])
