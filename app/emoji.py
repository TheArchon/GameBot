from __future__ import annotations

import os
import re
from typing import Mapping


# Button semantic keys -> environment variables. Leave IDs blank to keep Unicode fallbacks.
EMOJI_ENV = {
    "add_group": "5355051922862653659",
    "help": "5409119256107297715",
    "support": "5408910404732595664",
    "updates": "5409132617750555920",
    "owner": "5368509223632118184",
    "home": "5395475373368564257",
    "prev": "5443038326535759644",
    "next": "5217822164362739968",
    "page": "5445284980978621387",
    "profile": "5767205329708256993",
    "leaderboard": "5215480011322042129",
    "wallet": "6082481565894450113",
    "language": "5420323339723881652",
    "richest": "6078097130134706038",
    "charm": "5161208387957950108",
    "chat_top": "6289589175284928919",
    "global_chat": "6217662152547766453",
    "trust": "5978724583476301154",
    "betray": "6026367225466720832",
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
