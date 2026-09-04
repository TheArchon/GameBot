from __future__ import annotations

import re
from typing import Iterable

from app.emoji import custom_emoji_ids


def kb(rows: Iterable[list[dict]]) -> dict:
    return {"inline_keyboard": list(rows)}


# A localized label may start with one or more Unicode emoji/symbol characters.
# When a Telegram custom emoji icon is configured we remove that visual prefix,
# because Bot API displays icon_custom_emoji_id separately to the left of the text.
_PREFIX = re.compile(r"^[\s\u2600-\u27BF\U0001F000-\U0001FAFF\u200d\ufe0f\u2640-\u2642\u2190-\u21ff\u2300-\u23ff\u25a0-\u25ff♙♨⌂]+")


def _button_payload(text: str, emoji_key: str | None = None) -> dict:
    payload: dict = {}
    if emoji_key:
        emoji_id = custom_emoji_ids().get(emoji_key, "").strip()
        if emoji_id:
            payload["text"] = _PREFIX.sub("", text).strip() or text
            payload["icon_custom_emoji_id"] = emoji_id
            return payload
    payload["text"] = text
    return payload


def btn(text: str, data: str, emoji_key: str | None = None) -> dict:
    payload = _button_payload(text, emoji_key)
    payload["callback_data"] = data
    return payload


def url_btn(text: str, url: str, emoji_key: str | None = None) -> dict:
    payload = _button_payload(text, emoji_key)
    payload["url"] = url
    return payload
