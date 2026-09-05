from __future__ import annotations

from app.keyboards.common import kb, btn
from app.keyboards.games import trust_keyboard
from app.keyboards.home import home_keyboard
from app.keyboards.wallet import wallet_keyboard
from app.locales.loader import SUPPORTED, load, localize_result


class CallbackHandler:
    def _edit(self, chat_id: int, message_id: int, message: dict, text: str, markup: dict | None = None) -> None:
        # Home/Profile/Wallet/Leaderboard callbacks originate from the photo start card.
        # Telegram requires editMessageCaption for media messages and editMessageText for text messages.
        if message.get("photo") or "caption" in message:
            self.bot.edit_caption(chat_id, message_id, text, markup)
        else:
            self.bot.edit(chat_id, message_id, text, markup)

    def callback(self, q: dict) -> None:
        callback_id = q.get("id")
        data = q.get("data", "")
        message = q.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        uid = q.get("from", {}).get("id")

        try:
            if uid is None or chat_id is None or message_id is None:
                raise ValueError("Malformed callback query")

            uid = int(uid)
            self.economy.ensure(uid, q.get("from", {}).get("username") or "", q.get("from", {}).get("first_name") or "User")
            language = self.db.user(uid)["language"]
            locale = load(language)

            if data.startswith("help:"):
                page = int(data.split(":", 1)[1])
                text, markup = self.help_page(page, language)
                self.bot.edit_caption(chat_id, message_id, text, markup)
            elif data == "home":
                self.bot.edit_caption(
                    chat_id,
                    message_id,
                    locale["messages"]["home_short"],
                    home_keyboard(self.cfg.bot_username, self.cfg.support_url, self.cfg.updates_url, self.cfg.owner_url, language),
                )
            elif data == "profile":
                text, markup = self.profile_view(uid)
                self._edit(chat_id, message_id, message, text, markup)
            elif data == "language":
                text, markup = self.language_view(uid)
                self._edit(chat_id, message_id, message, text, markup)
            elif data.startswith("lang:"):
                lang = data.split(":", 1)[1]
                if lang not in SUPPORTED:
                    raise ValueError("Unsupported language")
                with self.db.connection() as c:
                    c.execute(
                        "UPDATE users SET language=?,updated_at=? WHERE id=?",
                        (lang, __import__("app.db", fromlist=["now_iso"]).now_iso(), uid),
                    )
                    c.commit()
                self.bot.answer_callback(callback_id, load(lang)["messages"]["language_updated"])
                text, markup = self.profile_view(uid)
                self._edit(chat_id, message_id, message, text, markup)
            elif data == "wallet":
                lang = self.db.user(uid)["language"]
                msg = load(lang)["messages"]["wallet_template"].format(
                    balance=self.economy.balance(uid),
                    stolen=self.db.stolen_total(uid),
                )
                self._edit(chat_id, message_id, message, msg, wallet_keyboard(lang))
            elif data == "leaderboard":
                self._show_leaderboards(chat_id, message_id, "richest", message)
            elif data.startswith("lb:"):
                self._show_leaderboards(chat_id, message_id, data.split(":", 1)[1], message)
            elif data.startswith("trust:"):
                _, game_id, choice = data.split(":")
                ok, text = self.games.choose_trust(int(game_id), uid, choice)
                text = localize_result(language, text)
                self.bot.answer_callback(callback_id, text, not ok)
                settled = ok and ("Both" in text or "betrayal" in text or "betrayer" in text)
                self.bot.edit(chat_id, message_id, f"🤝 *Trust Game #{game_id}*\n\n{text}", kb([]) if settled else trust_keyboard(int(game_id), language))
            elif data == "add":
                self.bot.answer_callback(callback_id, locale["messages"]["add_hint"])
            elif data in {"support", "updates", "owner"}:
                self.bot.edit_caption(
                    chat_id,
                    message_id,
                    locale["messages"][data],
                    kb([[btn(locale["buttons"]["home"], "home", "home")]]),
                )
            elif data == "noop":
                self.bot.answer_callback(callback_id, locale["messages"]["help_callback"])
            else:
                self.bot.answer_callback(callback_id, locale["messages"]["unavailable"])
        except Exception:
            fallback = load("en")["messages"]["unable"]
            try:
                self.bot.answer_callback(callback_id, fallback, True)
            except Exception:
                pass
