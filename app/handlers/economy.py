from __future__ import annotations
from app.keyboards.wallet import leaderboard_keyboard
from app.locales.loader import t, localize_result, load
from .common import target_id

class EconomyHandler:
    def _send(self,m,cid,uid,args):
            target=target_id(m)
            parts=list(args)
            if not target:
                for i,part in enumerate(parts[:2]):
                    if part.startswith("@") and len(part)>1:
                        row=self.db.user_by_username(part)
                        if row:
                            target=int(row["id"])
                        else:
                            try:
                                info=self.bot.get_chat(part)
                                target=int(info["id"]) if info.get("type") == "private" else None
                                if target is None: raise ValueError("Target is not a user")
                                self.economy.ensure(target, info.get("username") or "", info.get("first_name") or info.get("title") or "User")
                            except Exception:
                                target=None
                        parts.pop(i)
                        break
                    if part.lstrip("@").isdigit():
                        target=int(part.lstrip("@"))
                        parts.pop(i)
                        break
            if not target or len(parts)!=1 or not parts[0].isdigit():
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.usage_send")); return
            amount=int(parts[0]); ok,text=self.db.transfer(uid,target,amount); self.bot.send(cid,localize_result(self.db.user(uid)["language"],text))
    def _charm(self,cid,uid,text,target=None):
            with self.db.connection() as c:
                c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(uid,1,"charm","flirt_or_shayari",__import__("app.db",fromlist=["now_iso"]).now_iso())); c.commit()
            self.bot.send(cid,text,reply_to=target)
    def _leaderboard_rows(self, kind, chat_id=None):
            with self.db.connection() as c:
                if kind == "charm":
                    return c.execute("""SELECT u.id,u.first_name,u.username,
                        COALESCE(SUM(CASE WHEN t.kind='charm' THEN t.amount ELSE 0 END),0) score
                        FROM users u LEFT JOIN transactions t ON t.user_id=u.id
                        WHERE u.is_banned=0 GROUP BY u.id ORDER BY score DESC,u.id ASC LIMIT 10""").fetchall()
                if kind == "chat":
                    if chat_id is None:
                        return []
                    return c.execute("""SELECT u.id,u.first_name,u.username,COUNT(e.id) score
                        FROM users u LEFT JOIN events e ON e.actor_id=u.id AND e.chat_id=? AND e.event_type='message'
                        WHERE u.is_banned=0 GROUP BY u.id ORDER BY score DESC,u.id ASC LIMIT 10""", (chat_id,)).fetchall()
                if kind == "global":
                    return c.execute("""SELECT u.id,u.first_name,u.username,COUNT(e.id) score
                        FROM users u LEFT JOIN events e ON e.actor_id=u.id AND e.event_type='message'
                        WHERE u.is_banned=0 GROUP BY u.id ORDER BY score DESC,u.id ASC LIMIT 10""").fetchall()
                return c.execute("SELECT id,username,first_name,balance score FROM users WHERE is_banned=0 ORDER BY balance DESC,id ASC LIMIT 10").fetchall()
    def _show_leaderboards(self,cid,mid,kind,message=None):
            kind = kind if kind in {"richest","charm","chat","global"} else "richest"
            data=load(self.db.user(self._current_uid)["language"]); titles={"richest":data["buttons"]["richest"],"charm":data["buttons"]["charm"],"chat":data["buttons"]["chat_top"],"global":data["buttons"]["global_chat"]}
            rows=self._leaderboard_rows(kind,cid)
            lines=[f"🏆 *{data['messages']['leaderboard_title']} — {titles[kind]}*",""]
            if not rows:
                lines.append(data["messages"]["leaderboard_empty"])
            else:
                for i,r in enumerate(rows,1):
                    name=r['first_name'] or ("@"+r['username'] if r['username'] else "User")
                    lines.append(f"*{i}.* {name} — `{int(r['score']):,}`")
            markup=leaderboard_keyboard(self.db.user(self._current_uid)["language"])
            text="\n".join(lines)
            if message and (message.get("photo") or "caption" in message):
                self.bot.edit_caption(cid,mid,text,markup)
            else:
                self.bot.edit(cid,mid,text,markup)
    def _leaderboard_text(self,cid):
            rows=self._leaderboard_rows("richest",cid)
            if not rows:
                return "🏆 *"+load(self.db.user(self._current_uid)["language"])["messages"]["leaderboard_title"]+"*\n\n"+load(self.db.user(self._current_uid)["language"])["messages"]["leaderboard_no_users"]
            return "🏆 *Leaderboard*\n\n"+"\n".join(f"*{i}.* {r['first_name'] or r['username'] or 'User'} — `{int(r['score']):,}`" for i,r in enumerate(rows,1))
    def _leaderboard(self,cid):
            self.bot.send(cid,self._leaderboard_text(cid),leaderboard_keyboard(self.db.user(self._current_uid)["language"]))
    def _steal(self,m,cid,uid,args):
            target=target_id(m); requested=None
            if args:
                if args[0].isdigit(): requested=int(args[0])
                elif args[0].startswith("@"):
                    u=self.db.user_by_username(args[0])
                    if u:
                        target=int(u["id"])
                    else:
                        try:
                            info=self.bot.get_chat(args[0]); target=int(info["id"]) if info.get("type") == "private" else None
                            if target is None: raise ValueError("Target is not a user")
                            self.economy.ensure(target, info.get("username") or "", info.get("first_name") or info.get("title") or "User")
                        except Exception:
                            target=None
                    if len(args)>1 and args[1].isdigit(): requested=int(args[1])
            if not target and args and args[0].lstrip("@").isdigit(): target=int(args[0].lstrip("@"))
            if not target: self.bot.send(cid,t(self.db.user(uid)["language"],"messages.usage_steal")); return
            ok,text=self.economy.steal(uid,target,self.cooldowns,self.cfg.steal_cooldown,requested); self.bot.send(cid,localize_result(self.db.user(uid)["language"],text))
    def _shield(self,cid,uid):
            from datetime import datetime,timedelta,timezone
            now=datetime.now(timezone.utc)
            with self.db.connection() as c:
                c.execute("BEGIN IMMEDIATE")
                row=c.execute("SELECT balance,shield_until FROM users WHERE id=?",(uid,)).fetchone()
                if not row or int(row["balance"])<self.cfg.shield_cost:
                    self.bot.send(cid,t(self.db.user(uid)["language"],"messages.shield_cost",cost=self.cfg.shield_cost)); return
                current=None
                if row["shield_until"]:
                    try:
                        current=datetime.fromisoformat(row["shield_until"])
                    except ValueError:
                        current=None
                base=max(now,current) if current else now
                until=(base+timedelta(hours=self.cfg.shield_hours)).isoformat()
                stamp=__import__('app.db',fromlist=['now_iso']).now_iso()
                updated=c.execute("UPDATE users SET balance=balance-?,shield_until=?,updated_at=? WHERE id=? AND balance>=?",(self.cfg.shield_cost,until,stamp,uid,self.cfg.shield_cost))
                if updated.rowcount!=1:
                    c.rollback(); self.bot.send(cid,t(self.db.user(uid)["language"],"messages.shield_failed")); return
                c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(uid,-self.cfg.shield_cost,"shield","purchase",stamp)); c.commit()
            self.bot.send(cid,t(self.db.user(uid)["language"],"messages.shield_activated",until=until[:19].replace("T"," ")))
