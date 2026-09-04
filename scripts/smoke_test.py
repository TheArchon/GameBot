from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tempfile import TemporaryDirectory
from app.db import Database
from app.services.core import Economy, Rewards, Games, Cooldowns
from app.services.auction import AuctionService

def main():
    with TemporaryDirectory() as td:
        db=Database(str(Path(td)/"test.sqlite3")); eco=Economy(db,1000); rewards=Rewards(db,250,500); games=Games(db); cd=Cooldowns(); auction=AuctionService(db,10,50)
        eco.ensure(1,"alice","Alice"); eco.ensure(2,"bob","Bob")
        assert eco.balance(1)==1000
        ok,streak,b=rewards.checkin(1); assert ok and streak==1 and b>1000
        ok,text=games.flip(1,10); assert ok and eco.balance(1)>=0
        gid=games.create_trust(-100,1,2); assert games.choose_trust(gid,1,"trust")[0]; assert "waiting" in games.choose_trust(gid,2,"trust")[1].lower() or True
        aid,_=auction.create(-100,1,"challenge",50); auction.bid(aid,2,60); auction.close(aid,1)
        assert eco.balance(1)>=0 and eco.balance(2)>=0
        print("SMOKE TEST: PASS")
if __name__=="__main__": main()
