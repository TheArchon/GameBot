from __future__ import annotations
from .common import target_id
from app.locales.loader import t

class AdminHandler:
    def _maintenance(self,cid,uid,args):
            if not self.owner(uid): self.bot.send(cid,t(self.db.user(uid)["language"],"messages.owner_required")); return
            if not args or args[0] not in {"on","off"}: self.bot.send(cid,t(self.db.user(uid)["language"],"messages.maintenance_usage")); return
            self.db.set_setting("maintenance",args[0]); self.bot.send(cid,t(self.db.user(uid)["language"],"messages.maintenance_state",state=args[0].upper()))
    def _adminstats(self,cid,uid):
            if not self.owner(uid): self.bot.send(cid,t(self.db.user(uid)["language"],"messages.owner_required")); return
            s=self.db.stats(); self.bot.send(cid,t(self.db.user(uid)["language"],"messages.admin_stats",users=s["users"],groups=s["groups"],balance=s["balance"]))
    def _addcoupon(self,cid,uid,args):
            if not self.owner(uid) or len(args)!=3: self.bot.send(cid,t(self.db.user(uid)["language"],"messages.addcoupon_usage")); return
            code,reward,uses=args
            with self.db.connection() as c:
                c.execute("INSERT INTO coupons(code,reward,max_uses,created_at) VALUES(?,?,?,?)",(code.upper(),int(reward),int(uses),__import__('app.db',fromlist=['now_iso']).now_iso())); c.commit()
            self.bot.send(cid,t(self.db.user(uid)["language"],"messages.coupon_created"))
    def _setbalance(self,cid,uid,args):
            if not self.owner(uid) or len(args)!=2: self.bot.send(cid,t(self.db.user(uid)["language"],"messages.balance_usage")); return
            target,amount=int(args[0]),int(args[1]); u=self.db.user(target)
            if not u: self.bot.send(cid,t(self.db.user(uid)["language"],"messages.user_not_found")); return
            delta=amount-int(u['balance']); self.db.add_balance(target,delta,"admin_setbalance","owner"); self.bot.send(cid,t(self.db.user(uid)["language"],"messages.balance_updated"))
    def _ban(self,cid,uid,args,ban):
            if not self.owner(uid) or not args: self.bot.send(cid,t(self.db.user(uid)["language"],"messages.ban_usage")); return
            with self.db.connection() as c: c.execute("UPDATE users SET is_banned=? WHERE id=?",(1 if ban else 0,int(args[0]))); c.commit()
            self.bot.send(cid,t(self.db.user(uid)["language"],"messages.user_banned" if ban else "messages.user_unbanned"))
    def _update(self,cid,uid):
            if not self.owner(uid):
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.update_access"))
                return
            self.bot.send(cid,t(self.db.user(uid)["language"],"messages.update_started"))
            try:
                result=update_and_validate()
            except UpdateError as exc:
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.update_failed",error=str(exc)[:1200]))
                return
            except Exception as exc:
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.update_failed_unexpected",error=str(exc)[:1200]))
                return
            if not result.changed:
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.update_current",branch=result.branch,commit=result.new_commit[:12]))
                return
            self.bot.send(cid,t(self.db.user(uid)["language"],"messages.update_success",old=result.old_commit[:12],new=result.new_commit[:12],branch=result.branch))
            restart_process()
    def _broadcast(self,cid,uid,args):
            if not self.owner(uid) or not args: self.bot.send(cid,t(self.db.user(uid)["language"],"messages.broadcast_usage")); return
            text=" ".join(args); sent=0
            with self.db.connection() as c:
                ids=[r[0] for r in c.execute("SELECT id FROM users WHERE is_banned=0").fetchall()]
            for target_id in ids:
                try: self.bot.send(target_id,text); sent+=1
                except Exception: pass
            self.bot.send(cid,t(self.db.user(uid)["language"],"messages.broadcast_done",sent=sent))
