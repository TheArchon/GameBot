from __future__ import annotations

from app.keyboards.language import language_keyboard
from app.keyboards.profile import profile_keyboard
from app.keyboards.wallet import wallet_keyboard
from app.locales.loader import SUPPORTED, load, t


class GeneralHandler:
    def profile_view(self, uid: int) -> tuple[str, dict]:
        row = self.db.user(uid)
        language = row["language"]
        data = load(language)
        name = row["first_name"] or row["username"] or "User"
        shield = data["messages"]["shield_active"] if row["shield_until"] else data["messages"]["shield_inactive"]
        text = data["messages"]["profile_template"].format(
            name=name,
            balance=int(row["balance"]),
            streak=int(row["streak"]),
            shield=shield,
            language=language.upper(),
        )
        return text, profile_keyboard(language)

    def language_view(self, uid: int) -> tuple[str, dict]:
        language = self.db.user(uid)["language"]
        data = load(language)
        return data["messages"]["language_title"], language_keyboard(language)

    def _wallet(self, cid: int, uid: int) -> None:
        language = self.db.user(uid)["language"]
        data = load(language)
        balance = self.economy.balance(uid)
        stolen = self.db.stolen_total(uid)
        text = data["messages"]["wallet_template"].format(balance=balance, stolen=stolen)
        self.bot.send(cid, text, wallet_keyboard(language))

    def _stats(self, cid: int, uid: int) -> None:
        if not self.owner(uid):
            self.bot.send(cid, t(self.db.user(uid)["language"], "messages.stats_owner"))
            return
        st = self.db.stats()
        self.bot.send(cid, t(self.db.user(uid)["language"], "messages.stats", users=st["users"], groups=st["groups"], balance=st["balance"]))

    def _checkin(self, cid: int, uid: int) -> None:
        ok, streak, balance = self.rewards.checkin(uid)
        self.bot.send(cid, t(self.db.user(uid)["language"], "messages.checkin", status=t(self.db.user(uid)["language"], "messages.checkin_claimed" if ok else "messages.checkin_already"), streak=streak, balance=balance))

    def _invite(self, cid: int, uid: int) -> None:
        username = self.cfg.bot_username or "YourBotUsername"
        lang = self.db.user(uid)["language"]
        count = self.db.referral_count(uid)
        claimed = self.db.referral_milestones_claimed(uid)
        lines = [f"🎟️ *{load(lang)['messages']['invite_title']}*", "", f"`https://t.me/{username}?start=ref_{uid}`", "", load(lang)['messages']['invite_reward'].format(reward=self.cfg.referral_reward)]
        if self.cfg.referral_milestones:
            lines += ["", load(lang)['messages']['invite_milestones']]
            for milestone, bonus in self.cfg.referral_milestones:
                if count >= milestone:
                    status = load(lang)['messages']['milestone_claimed'] if milestone in claimed else load(lang)['messages']['milestone_ready']
                    lines.append(f"• {milestone} → *{bonus:,}* — {status}")
                else:
                    remaining = milestone - count
                    lines.append(load(lang)['messages']['milestone_progress'].format(current=count, target=milestone, remaining=remaining, reward=bonus))
        self.bot.send(cid, "\n".join(lines))

    def _redeem(self, cid: int, uid: int, args: list[str]) -> None:
        if not args:
            self.bot.send(cid, t(self.db.user(uid)["language"], "messages.usage_redeem"))
            return
        _, text = self.rewards.coupon(uid, args[0])
        self.bot.send(cid, text)

    def _language(self, cid: int, uid: int, args: list[str]) -> None:
        if not args:
            self.bot.send(cid, *self.language_view(uid))
            return
        lang = args[0].lower()
        if lang not in SUPPORTED:
            self.bot.send(cid, t(self.db.user(uid)["language"], "messages.language_available"))
            return
        with self.db.connection() as c:
            c.execute(
                "UPDATE users SET language=?,updated_at=? WHERE id=?",
                (lang, __import__("app.db", fromlist=["now_iso"]).now_iso(), uid),
            )
            c.commit()
        self.bot.send(cid, load(lang)["messages"]["language_updated"])
