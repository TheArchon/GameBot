from __future__ import annotations
from app.keyboards.games import trust_keyboard
from app.locales.loader import t, localize_result
from .common import target_id

class GamesHandler:
    def _flip(self,cid,uid,args):
            if not args or not args[0].isdigit(): self.bot.send(cid,t(self.db.user(uid)["language"],"messages.usage_flip",min=self.cfg.flip_min,max=self.cfg.flip_max)); return
            amount=int(args[0]);
            if not self.cfg.flip_min<=amount<=self.cfg.flip_max: self.bot.send(cid,t(self.db.user(uid)["language"],"messages.flip_range")); return
            ok,text=self.games.flip(uid,amount); self.bot.send(cid,localize_result(self.db.user(uid)["language"],text))
    def _trust(self,m,cid,uid):
            target=target_id(m)
            if not target: self.bot.send(cid,t(self.db.user(uid)["language"],"messages.trust_reply")); return
            amount=0
            parts=(m.get("text","").split())[1:]
            if parts:
                if not parts[0].isdigit(): self.bot.send(cid,t(self.db.user(uid)["language"],"messages.trust_usage")); return
                amount=int(parts[0])
            gid=self.games.create_trust(cid,uid,target,amount); self.bot.send(cid,t(self.db.user(uid)["language"],"messages.trust_start",id=gid),trust_keyboard(gid, self.db.user(uid)["language"]))
    def _bid(self,m,cid,uid,args):
            if not args:
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.bid_usage"))
                return
            if args[0].lower()=="close" and len(args)>1:
                a=self.auction.close(int(args[1]),uid)
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.bid_closed",id=a["id"],amount=a["current_bid"]))
                return
            if len(args)>=1 and args[0].isdigit() and len(args)>=2 and args[1].isdigit():
                old,old_user=self.auction.bid(int(args[0]),uid,int(args[1]))
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.bid_accepted",amount=int(args[1]),old=old))
                return
            if not self.owner(uid):
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.bid_owner"))
                return
            if not args[0].isdigit():
                self.bot.send(cid,t(self.db.user(uid)["language"],"messages.bid_usage"))
                return
            amount=int(args[0]); item=" ".join(args[1:]).strip() or "Kai’s active auction item"
            aid,ends=self.auction.create(cid,uid,item,amount)
            self.bot.send(cid,t(self.db.user(uid)["language"],"messages.auction_opened",id=aid,item=item,amount=amount,ends=ends))
