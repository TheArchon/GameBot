from pathlib import Path
from tempfile import TemporaryDirectory
from app.db import Database
from app.services.core import Economy, Rewards, Games, Cooldowns
from app.services.auction import AuctionService

def make():
    td=TemporaryDirectory(); db=Database(str(Path(td.name)/"x.sqlite3")); eco=Economy(db,1000); rewards=Rewards(db,250,500,((1,100),(3,300))); games=Games(db); eco.ensure(1,"a","A"); eco.ensure(2,"b","B"); return td,db,eco,rewards,games

def test_checkin_once():
    td,db,eco,r,g=make()
    try:
        assert r.checkin(1)[0] is True
        assert r.checkin(1)[0] is False
    finally: td.cleanup()

def test_steal_protected_and_atomic():
    td,db,eco,r,g=make()
    try:
        before=eco.balance(1)+eco.balance(2)
        ok,_=eco.steal(1,2,Cooldowns(),1)
        assert ok and eco.balance(1)+eco.balance(2)==before
    finally: td.cleanup()

def test_trust_state():
    td,db,eco,r,g=make()
    try:
        gid=g.create_trust(-1,1,2)
        assert g.choose_trust(gid,1,"trust")[0]
        ok,msg=g.choose_trust(gid,2,"betray"); assert ok and "betrayal" in msg.lower()
    finally: td.cleanup()

def test_auction_settlement():
    td,db,eco,r,g=make(); a=AuctionService(db,10,50)
    try:
        aid,_=a.create(-1,1,"x",100); assert eco.balance(1)==1000
        a.bid(aid,2,150); assert eco.balance(1)==1000 and eco.balance(2)==850
        a.close(aid,1); assert eco.balance(1)==1150 and eco.balance(2)==850
    finally: td.cleanup()

def test_transfer_and_steal_floor():
    with TemporaryDirectory() as td:
        db=Database(str(Path(td)/"db.sqlite3")); eco=Economy(db,500); eco.ensure(1,"a","A"); eco.ensure(2,"b","B")
        ok,_=db.transfer(1,2,100); assert ok; assert eco.balance(1)==400 and eco.balance(2)==600
        ok,_=eco.steal(1,2,Cooldowns(),3600,501); assert not ok
        ok,_=eco.steal(1,2,Cooldowns(),3600,500); assert ok
        assert eco.balance(2)>=100

def test_trust_stake_settlement():
    with TemporaryDirectory() as td:
        db=Database(str(Path(td)/"db.sqlite3")); eco=Economy(db,500); eco.ensure(1,"a","A"); eco.ensure(2,"b","B")
        g=Games(db); gid=g.create_trust(10,1,2,50)
        assert eco.balance(1)==450 and eco.balance(2)==450
        assert g.choose_trust(gid,1,"trust")[0]
        assert g.choose_trust(gid,2,"trust")[0]
        assert eco.balance(1)==550 and eco.balance(2)==550

def test_trust_expiry_refunds_stakes():
    with TemporaryDirectory() as td:
        db=Database(str(Path(td)/"db.sqlite3")); eco=Economy(db,500); eco.ensure(1,"a","A"); eco.ensure(2,"b","B")
        g=Games(db); gid=g.create_trust(10,1,2,50)
        with db.connection() as c:
            c.execute("UPDATE trust_games SET expires_at=? WHERE id=?",("2000-01-01T00:00:00+00:00",gid)); c.commit()
        assert g.expire_trust_games()==1
        assert eco.balance(1)==500 and eco.balance(2)==500


def test_auction_without_bids_closes_cleanly():
    with TemporaryDirectory() as td:
        db=Database(str(Path(td)/"db.sqlite3")); eco=Economy(db,500); eco.ensure(1,"a","A")
        a=AuctionService(db,10,50); aid,_=a.create(10,1,"Golden Charm",100)
        row=a.close(aid,1)
        assert row["item"]=="Golden Charm" and eco.balance(1)==500


def test_steal_random_handles_tiny_protected_balance():
    with TemporaryDirectory() as td:
        db=Database(str(Path(td)/"db.sqlite3")); eco=Economy(db,100); eco.ensure(1,"a","A"); eco.ensure(2,"b","B")
        eco.debit(2, -9, "test")  # add 9 => 109 balance
        ok,text=eco.steal(1,2,Cooldowns(),1); assert ok
        assert eco.balance(2)==100

def test_referral_milestones_are_one_time():
    with TemporaryDirectory() as td:
        db=Database(str(Path(td)/"db.sqlite3")); eco=Economy(db,500); rew=Rewards(db,250,500,((1,100),(2,200))); eco.ensure(1,"inv","Inv"); eco.ensure(2,"a","A"); eco.ensure(3,"b","B")
        assert rew.refer(2,1)[0]; assert eco.balance(1)==1100
        assert rew.refer(3,1)[0]; assert eco.balance(1)==1800
        assert db.referral_count(1)==2 and db.referral_milestones_claimed(1)=={1,2}
