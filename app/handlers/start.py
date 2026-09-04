from __future__ import annotations

from pathlib import Path
import os

from app.emoji import tg_emoji
from app.keyboards.home import home_keyboard
from app.locales.loader import load


class StartHandler:
    def image_path(self) -> str:
        image = self.cfg.start_image_path
        if os.path.isabs(image):
            return image
        # app/handlers/start.py -> project root is parents[2]
        return str(Path(__file__).resolve().parents[2] / image)

    def send_home(self, chat_id: int, uid: int | None = None) -> None:
        language = self.db.user(uid)["language"] if uid is not None and self.db.user(uid) else "en"
        data = load(language)
        heart = tg_emoji(self.cfg.emoji_heart, "💝")
        text = data["messages"]["start_caption"].format(heart=heart)
        markup = home_keyboard(
            self.cfg.bot_username,
            self.cfg.support_url,
            self.cfg.updates_url,
            self.cfg.owner_url,
            language,
        )
        self.bot.send_photo(chat_id, self.image_path(), text, markup)

    def _referral(self, uid: int, payload: str | None) -> None:
        if not payload or not payload.startswith("ref_"):
            return
        try:
            self.rewards.refer(uid, int(payload[4:]))
        except (TypeError, ValueError):
            return

    def handle_start(self, chat_id: int, uid: int, args: list[str]) -> None:
        self._referral(uid, args[0] if args else None)
        self.send_home(chat_id, uid)
