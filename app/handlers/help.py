from __future__ import annotations

from app.keyboards.help import help_keyboard
from app.locales.loader import load
from app.emoji import render_help_page_emojis


class HelpHandler:
    HELP_PAGES = 5

    def help_page(self, page: int, language: str = "en") -> tuple[str, dict]:
        page = max(1, min(self.HELP_PAGES, int(page)))
        data = load(language)
        section = data["help"][str(page)]
        text = (
            f"[[help_title]]*Help Center  {page}/{self.HELP_PAGES}*\n\n"
            f"[[help_heading]]{section['title']}\n\n"
            f"{section['body']}"
        )
        text = render_help_page_emojis(text, page)
        return text, help_keyboard(page, language, self.HELP_PAGES)

    def handle_help(self, chat_id: int, uid: int, page: int = 1) -> None:
        language = self.db.user(uid)["language"]
        text, markup = self.help_page(page, language)
        self.bot.send_photo(chat_id, self.image_path(), text, markup, parse_mode="HTML")
