from __future__ import annotations
from app.locales.loader import load
from .common import user_from_message, random_choice
from .start import StartHandler
from .help import HelpHandler
from .general import GeneralHandler
from .economy import EconomyHandler
from .games import GamesHandler
from .ai import AiHandler
from .admin import AdminHandler
from .callbacks import CallbackHandler

FLIRT=["You have a dangerous talent for making ordinary chats interesting. 😉","If charm were currency, you would already be rich. ✨","I had a clever line ready… then you smiled. 😌"]
SHAYARI=["Kuch lafz dil se nikal jaate hain,\nKuch log dil mein utar jaate hain. ✨","Raat khamosh thi, baat khaas thi,\nBas tumhari ek muskaan paas thi. 🌙"]

class Router(StartHandler, HelpHandler, GeneralHandler, EconomyHandler, GamesHandler, AiHandler, AdminHandler, CallbackHandler):
    def __init__(self,bot,db,economy,rewards,games,auction,ai,cooldowns,config):
            self.bot,self.db,self.economy,self.rewards,self.games,self.auction,self.ai,self.cooldowns,self.cfg=bot,db,economy,rewards,games,auction,ai,cooldowns,config
            self.bot_id=None
    def ensure(self,m):
            uid,un,fn=user_from_message(m); self.economy.ensure(uid,un,fn); return uid,un,fn
    def parse(self,m):
            text=m.get("text","").strip(); parts=text.split()
            if not parts or not parts[0].startswith("/"): return "", parts
            cmd=parts[0].split("@")[0].lower()
            return cmd,parts[1:]
    def handle(self,m):
            if "text" not in m and "new_chat_members" not in m: return
            uid,un,fn=self.ensure(m); self._current_uid=uid; chat=m.get("chat",{}); cid=int(chat.get("id")); self.games.expire_trust_games(); self.auction.close_expired(); self.db.ensure_chat(cid, chat.get("title") or (f"{fn} chat" if chat.get("type")=="private" else ""))
            if m.get("new_chat_members"):
                self.db.log_event("bot_added",uid,cid,{"members":len(m["new_chat_members"])})
                return
            self.db.log_event("message",uid,cid,{"command":bool(m.get("text","").startswith("/"))})
            cmd,args=self.parse(m)
            if self.db.user(uid)["is_banned"]: self.bot.send(cid,load(self.db.user(uid)["language"])["messages"]["banned"]); return
            if self.maintenance() and not self.owner(uid) and cmd not in {"start","help"}: self.bot.send(cid,load(self.db.user(uid)["language"])["messages"]["maintenance"]); return
            try:
                if cmd=="/start":
                    self.handle_start(cid,uid,args)
                elif cmd in {"/help","/commands"}:
                    self.handle_help(cid,uid,1)
                elif cmd=="/profile": self.bot.send(cid,*self.profile_view(uid))
                elif cmd in {"/amount","/wallet"}: self._wallet(cid,uid)
                elif cmd=="/leaderboard": self._leaderboard(cid)
                elif cmd=="/checkin": self._checkin(cid,uid)
                elif cmd=="/invite": self._invite(cid,uid)
                elif cmd=="/send": self._send(m,cid,uid,args)
                elif cmd=="/redeem": self._redeem(cid,uid,args)
                elif cmd=="/steal": self._steal(m,cid,uid,args)
                elif cmd=="/shield": self._shield(cid,uid)
                elif cmd=="/flip": self._flip(cid,uid,args)
                elif cmd=="/trust": self._trust(m,cid,uid)
                elif cmd=="/bid": self._bid(m,cid,uid,args)
                elif cmd=="/flirt":
                    target=__import__("app.handlers.common",fromlist=["target_id"]).target_id(m)
                    if not target: self.bot.send(cid,load(self.db.user(uid)["language"])["messages"]["reply_flirt"])
                    else: self._charm(cid,uid,random_choice(FLIRT),target)
                elif cmd=="/shayari":
                    target=__import__("app.handlers.common",fromlist=["target_id"]).target_id(m)
                    if not target: self.bot.send(cid,load(self.db.user(uid)["language"])["messages"]["reply_shayari"])
                    else: self._charm(cid,uid,random_choice(SHAYARI),target)
                elif cmd in {"/resmemory","/resetmemory"}: self.db.clear_memory(uid,cid); self.bot.send(cid,load(self.db.user(uid)["language"])["messages"]["memory_cleared"])
                elif cmd=="/stats": self._stats(cid,uid)
                elif cmd=="/ai": self._ai_setting(m,cid,uid,args)
                elif cmd=="/maintenance": self._maintenance(cid,uid,args)
                elif cmd=="/adminstats": self._adminstats(cid,uid)
                elif cmd=="/addcoupon": self._addcoupon(cid,uid,args)
                elif cmd=="/setbalance": self._setbalance(cid,uid,args)
                elif cmd in {"/ban","/unban"}: self._ban(cid,uid,args,cmd=="/ban")
                elif cmd=="/broadcast": self._broadcast(cid,uid,args)
                elif cmd=="/update": self._update(cid,uid)
                elif cmd=="/language": self._language(cid,uid,args)
                elif cmd=="/ping": self.bot.send(cid,load(self.db.user(uid)["language"])["messages"]["ping"])
                elif cmd and not self._is_group_ai(chat,cid,uid): pass
                elif not cmd and chat.get("type") == "private": self._chat_ai(cid,uid,m.get("text","") )
                elif not cmd and self._is_group_ai(chat,cid,uid) and self._ai_triggered(m): self._chat_ai(cid,uid,m.get("text","") )
            except Exception as e:
                self.db.log_event("handler_error",uid,cid,{"command":cmd,"error":str(e)[:300]}); self.bot.send(cid,load(self.db.user(uid)["language"])["messages"]["error"])
    def maintenance(self): return self.db.get_setting("maintenance","off")=="on"
    def owner(self,uid): return uid in self.cfg.owner_ids
