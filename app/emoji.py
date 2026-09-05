from __future__ import annotations

import os
import re
from typing import Mapping


# Button semantic keys -> environment variables. Leave IDs blank to keep Unicode fallbacks.
EMOJI_ENV = {
    "add_group": "EMOJI_ADD_GROUP",
    "help": "EMOJI_HELP",
    "support": "EMOJI_SUPPORT",
    "updates": "EMOJI_UPDATES",
    "owner": "EMOJI_OWNER",
    "home": "EMOJI_HOME",
    "prev": "EMOJI_PREV",
    "next": "EMOJI_NEXT",
    "page": "EMOJI_PAGE",
    "profile": "EMOJI_PROFILE",
    "leaderboard": "EMOJI_LEADERBOARD",
    "wallet": "EMOJI_WALLET",
    "language": "EMOJI_LANGUAGE",
    "richest": "EMOJI_RICHEST",
    "charm": "EMOJI_CHARM",
    "chat_top": "EMOJI_CHAT_TOP",
    "global_chat": "EMOJI_GLOBAL_CHAT",
    "trust": "EMOJI_TRUST",
    "betray": "EMOJI_BETRAY",
    "heart": "EMOJI_HEART",
}

def tg_emoji(emoji_id: str, fallback: str) -> str:
    """Render a Telegram custom emoji when an ID is configured, else use fallback."""
    emoji_id = str(emoji_id or "").strip()
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>' if emoji_id else fallback

def custom_emoji_ids() -> dict[str, str]:
    return {key: os.getenv(env, "").strip() for key, env in EMOJI_ENV.items()}

def emoji_for(key: str, fallback: str, ids: Mapping[str, str] | None = None) -> str:
    """Return configured custom emoji HTML for a semantic key, with Unicode fallback."""
    mapping = ids if ids is not None else custom_emoji_ids()
    return tg_emoji(mapping.get(key, ""), fallback)

def _fallback_emoji(text: str) -> str:
    # Keep the existing localized button text as the fallback. Telegram will render
    # the configured custom emoji in front of the label; no locale file is modified.
    return text

def render_message_emojis(text: str) -> str:
    """Replace message emoji placeholders with Telegram custom emojis."""
    if not text:
        return text

    ids = custom_emoji_ids()

    replacements = {
        "heart": "💝",
    }

    for key, fallback in replacements.items():
        token = f"[[emoji:{key}]]"
        if token in text:
            text = text.replace(
                token,
                emoji_for(key, fallback, ids),
            )

    return text
