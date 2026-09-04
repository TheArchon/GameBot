from __future__ import annotations
import logging,time,traceback
from app.config import Config
from app.db import Database
from app.telegram import Telegram,TelegramError
from app.services.core import Cooldowns,Economy,Rewards,Games
from app.services.auction import AuctionService
from app.services.ai import AIService
from app.handlers.router import Router

logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log=logging.getLogger("archon")

def main():
    cfg=Config.from_env(); db=Database(cfg.database_path); tg=Telegram(cfg.bot_token)
    me=tg.get_me(); log.info("Starting @%s (%s)",me.get("username"),me.get("id"))
    try:
        tg.set_my_commands([
            {"command":"start","description":"Open Kai"},
            {"command":"help","description":"Help & commands"},
            {"command":"profile","description":"View your profile"},
            {"command":"wallet","description":"View your wallet"},
            {"command":"leaderboard","description":"Open leaderboards"},
            {"command":"checkin","description":"Daily check-in"},
            {"command":"invite","description":"Referral link"},
            {"command":"flirt","description":"Send a playful line"},
            {"command":"shayari","description":"Get a shayari"},
            {"command":"steal","description":"Steal virtual coins"},
            {"command":"send","description":"Send virtual coins"},
            {"command":"shield","description":"Activate protection"},
            {"command":"flip","description":"Flip for coins"},
            {"command":"trust","description":"Start Trust game"},
            {"command":"bid","description":"Open/place an auction bid"},
            {"command":"language","description":"Change language"},
        ])
    except TelegramError as e:
        log.warning("Could not register bot commands: %s", e)
    economy=Economy(db,cfg.start_balance); rewards=Rewards(db,cfg.daily_reward,cfg.referral_reward,cfg.referral_milestones); games=Games(db)
    auction=AuctionService(db,cfg.bid_duration_minutes,cfg.bid_min); ai=AIService(db,cfg.ai_api_url,cfg.ai_api_key,cfg.ai_model,cfg.ai_system_prompt)
    router=Router(tg,db,economy,rewards,games,auction,ai,Cooldowns(),cfg)
    router.bot_id=int(me.get("id",0))
    offset=None
    while True:
        try:
            updates=tg.get_updates(offset=offset,timeout=25)
            games.expire_trust_games()
            auction.close_expired()
            for u in updates:
                offset=int(u["update_id"])+1
                if "callback_query" in u: router.callback(u["callback_query"])
                elif "message" in u: router.handle(u["message"])
        except KeyboardInterrupt: log.info("Shutdown requested."); break
        except TelegramError as e: log.error("Telegram error: %s",e); time.sleep(3)
        except Exception: log.error("Unexpected polling error:\n%s",traceback.format_exc()); time.sleep(2)

if __name__=="__main__": main()
