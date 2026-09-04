from __future__ import annotations

from app.locales.loader import load
from .common import kb, btn


def language_keyboard(current: str = "en") -> dict:
    data = load(current)
    b = data["buttons"]
    rows: list[list[dict]] = []
    row: list[dict] = []
    for code, name in data["languages"].items():
        row.append(btn(("✓ " if code == current else "") + name, f"lang:{code}", "language"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([btn(b["home"], "home", "home")])
    return kb(rows)
