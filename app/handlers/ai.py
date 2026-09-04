from __future__ import annotations
from .common import target_id
from app.locales.loader import t

class AiHandler:
    def _ai_setting(self,m,cid,uid,args):
            if m.get("chat",{}).get("type") not in {"group","supergroup"}:
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.group_ai_only")); return
            if not args or args[0].lower() not in {"on","off"}:
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.ai_usage")); return
            if not self._is_admin(cid,uid):
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.group_admins")); return
            state=args[0].lower()
            self.db.set_setting(f"chat_ai:{cid}",state)
            self.bot.send(cid,t(self.db.user(uid)["language"],"messages.group_ai_state",state=state.upper()))
    def _is_admin(self,cid,uid):
            try:
                member=self.bot.get_chat_member(cid,uid)
                return member.get("status") in {"creator","administrator"}
            except Exception:
                return self.owner(uid)
    def _is_group_ai(self,chat,cid,uid): return chat.get("type") in {"group","supergroup"} and self.db.get_setting(f"chat_ai:{cid}","on")=="on"
    def _ai_triggered(self,m):
            r=m.get("reply_to_message") or {}
            if r.get("from",{}).get("id") == getattr(self,"bot_id",None): return True
            text=(m.get("text") or "").lower()
            username=(self.cfg.bot_username or "").lower().lstrip("@")
            return bool(username and ("@"+username) in text)
    def _chat_ai(self,cid,uid,text): self.bot.send(cid,self.ai.reply(uid,cid,text))
