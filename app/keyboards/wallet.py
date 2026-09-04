from __future__ import annotations

from app.locales.loader import load
from .common import kb, btn


def wallet_keyboard(language: str = "en") -> dict:
    b = load(language)["buttons"]
    return kb([
        [btn(b["profile"], "profile", "profile"), btn(b["leaderboard"], "leaderboard", "leaderboard")],
        [btn(b["home"], "home", "home")],
    ])


def leaderboard_keyboard(language: str = "en") -> dict:
    b = load(language)["buttons"]
    return kb([
        [btn(b["richest"], "lb:richest", "richest"), btn(b["charm"], "lb:charm", "charm")],
        [btn(b["chat_top"], "lb:chat", "chat_top"), btn(b["global_chat"], "lb:global", "global_chat")],
        [btn(b["home"], "home", "home")],
    ])
