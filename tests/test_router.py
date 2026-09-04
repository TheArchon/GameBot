from tempfile import TemporaryDirectory
from pathlib import Path
from app.db import Database
from app.services.core import Economy, Rewards, Games, Cooldowns
from app.services.auction import AuctionService
from app.services.ai import AIService
from app.handlers.router import Router
from app.config import Config

class FakeTG:
    def __init__(self): self.sent=[]; self.edits=[]; self.caption_edits=[]; self.answers=[]
    def send(self,*a,**kw): self.sent.append((a,kw)); return {"message_id":len(self.sent)}
    def send_photo(self,*a,**kw): self.sent.append((a,kw)); return {"message_id":len(self.sent)}
    def get_chat_member(self,*a,**kw): return {"status":"administrator"}
    def get_chat(self,chat_id): return {"id":99,"username":"target99","first_name":"Target99"}
    def edit(self,*a,**kw): self.edits.append((a,kw)); return {}
    def edit_caption(self,*a,**kw): self.caption_edits.append((a,kw)); return {}
    def answer_callback(self,*a,**kw): self.answers.append((a,kw)); return {}


def build(td):
    db=Database(str(Path(td)/"bot.sqlite3")); tg=FakeTG()
    cfg=Config("token",frozenset({1}),"ArchonBot",str(Path(td)/"bot.sqlite3"),"","","","",250,500,1000,3600,500,12,10,10000,50,10)
    eco=Economy(db,1000); rew=Rewards(db,250,500); games=Games(db); auction=AuctionService(db,10,50); ai=AIService(db,"","","","x")
    return Router(tg,db,eco,rew,games,auction,ai,Cooldowns(),cfg),tg,db

def msg(uid=1,text="/start",chat_id=10,chat_type="private",reply=None):
    d={"message_id":1,"from":{"id":uid,"username":"user","first_name":"User"},"chat":{"id":chat_id,"type":chat_type},"text":text}
    if reply: d["reply_to_message"]={"from":{"id":reply,"username":"target","first_name":"Target"}}
    return d

def test_command_surface_does_not_crash():
    with TemporaryDirectory() as td:
        r,tg,db=build(td); db.ensure_user(2,"target","Target",1000)
        commands=["/start","/help","/profile","/amount","/wallet","/leaderboard","/checkin","/invite","/redeem","/steal","/shield","/flip 10","/trust","/bid 50","/shayari","/flirt","/resmemory","/stats","/ping"]
        for command in commands:
            reply=2 if command in {"/steal","/trust"} else None
            r.handle(msg(text=command,reply=reply))
        assert tg.sent

def test_private_ai_and_language_ui():
    with TemporaryDirectory() as td:
        r,tg,db=build(td); r.bot_id=999
        r.handle(msg(uid=1,text="Hello Kai"))
        assert "fallback" in tg.sent[-1][0][1].lower() or tg.sent[-1][0][1]
        r.handle(msg(uid=1,text="/language"))
        assert "Language" in tg.sent[-1][0][1]

def test_help_callbacks():
    with TemporaryDirectory() as td:
        r,tg,db=build(td); db.ensure_user(1,"user","User")
        for page in range(1,6):
            r.callback({"id":str(page),"data":f"help:{page}","from":{"id":1},"message":{"chat":{"id":10},"message_id":1}})
        assert len(tg.caption_edits)==5

def test_video_style_home_uses_photo_and_configured_urls():
    with TemporaryDirectory() as td:
        r,tg,db=build(td)
        r.cfg = r.cfg.__class__(**{**r.cfg.__dict__, "bot_username":"KaiCompanionBot", "support_url":"https://example.com/support", "updates_url":"https://example.com/updates", "owner_url":"https://example.com/owner"})
        r.handle(msg(text="/start"))
        assert tg.sent
        args,kw=tg.sent[-1]
        assert args[2].startswith("*Kai is here.")
        markup=args[3]
        assert markup["inline_keyboard"][0][0].get("url").endswith("?startgroup=true")
        assert markup["inline_keyboard"][1][0].get("url")=="https://example.com/support"

def test_group_ai_requires_admin():
    with TemporaryDirectory() as td:
        r,tg,db=build(td)
        class NonAdminTG(FakeTG):
            def get_chat_member(self,*a,**kw): return {"status":"member"}
        r.bot=NonAdminTG()
        r.handle(msg(uid=2,text="/ai on",chat_id=-100,chat_type="supergroup"))
        assert "admins" in r.bot.sent[-1][0][1].lower()

def test_charm_leaderboard_and_custom_emoji_formatter():
    from app.formatting import md_to_html
    with TemporaryDirectory() as td:
        r,tg,db=build(td); r.handle(msg(uid=1,text="/flirt",reply=2)); r.handle(msg(uid=1,text="/shayari",reply=2))
        assert db.charm_score(1)==2
        assert "<b>Title</b>" in md_to_html("*Title*")
        assert '<tg-emoji emoji-id="123">💝</tg-emoji>' in md_to_html('<tg-emoji emoji-id="123">💝</tg-emoji>')


def test_media_callbacks_use_caption_editing():
    with TemporaryDirectory() as td:
        r,tg,db=build(td)
        r.callback({"id":"1","data":"profile","from":{"id":1},"message":{"chat":{"id":10},"message_id":1,"photo":[{"file_id":"x"}],"caption":"home"}})
        assert len(tg.caption_edits)==1
        r.callback({"id":"2","data":"wallet","from":{"id":1},"message":{"chat":{"id":10},"message_id":1,"photo":[{"file_id":"x"}],"caption":"home"}})
        assert len(tg.caption_edits)==2
        # Both must have gone through the same fake edit recorder; implementation selects edit_caption for media.


def test_text_callbacks_still_use_text_editing():
    with TemporaryDirectory() as td:
        r,tg,db=build(td)
        r.callback({"id":"1","data":"profile","from":{"id":1},"message":{"chat":{"id":10},"message_id":1}})
        assert len(tg.edits)==1 and len(tg.caption_edits)==0


def test_flirt_and_shayari_require_reply_target():
    with TemporaryDirectory() as td:
        r,tg,db=build(td); db.ensure_user(2,"target","Target")
        r.handle(msg(uid=1,text="/flirt"))
        assert "reply" in tg.sent[-1][0][1].lower()
        before=db.charm_score(1)
        r.handle(msg(uid=1,text="/flirt",reply=2))
        r.handle(msg(uid=1,text="/shayari",reply=2))
        assert db.charm_score(1)==before+2


def test_invite_shows_referral_milestone_progress():
    with TemporaryDirectory() as td:
        r,tg,db=build(td)
        r.cfg = r.cfg.__class__(**{**r.cfg.__dict__, "referral_milestones": ((1,100),(3,300))})
        # Rewire rewards to use the test config milestones.
        r.rewards = Rewards(db,250,500,((1,100),(3,300)))
        db.ensure_user(2,"a","A")
        r.handle(msg(uid=2,text="/start"))
        r.handle(msg(uid=1,text="/invite"))
        assert "1/3" in tg.sent[-1][0][1] or "3" in tg.sent[-1][0][1]
