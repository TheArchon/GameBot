from __future__ import annotations
from datetime import datetime, timedelta, timezone
from app.db import Database, now_iso

class AuctionService:
    def __init__(self,db:Database,duration_minutes:int,min_bid:int): self.db,self.duration,self.min_bid=db,duration_minutes,min_bid
    def create(self,chat_id,creator,item,amount):
        if amount<self.min_bid: raise ValueError(f"Minimum bid is {self.min_bid:,}.")
        with self.db.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            if not c.execute("SELECT 1 FROM users WHERE id=?",(creator,)).fetchone(): raise ValueError("User not found")
            ends=(datetime.now(timezone.utc)+timedelta(minutes=self.duration)).isoformat()
            cur=c.execute("INSERT INTO auctions(chat_id,creator_id,item,current_bid,current_bidder,ends_at,created_at) VALUES(?,?,?,?,?,?,?)",(chat_id,creator,item,amount,0,ends,now_iso()))
            c.commit(); return cur.lastrowid,ends
    def bid(self,auction_id,uid,amount):
        with self.db.connection() as c:
            c.execute("BEGIN IMMEDIATE"); a=c.execute("SELECT * FROM auctions WHERE id=?",(auction_id,)).fetchone()
            if not a or a["status"]!="open": raise ValueError("Auction is closed.")
            if int(a["creator_id"]) == int(uid): raise ValueError("The auction creator cannot bid on their own auction.")
            if datetime.fromisoformat(a["ends_at"])<=datetime.now(timezone.utc): raise ValueError("Auction has expired.")
            if amount<=a["current_bid"]: raise ValueError("Your bid must be higher than the current bid.")
            bal=c.execute("SELECT balance FROM users WHERE id=?",(uid,)).fetchone()[0]
            if bal<amount: raise ValueError("Insufficient balance.")
            old=a["current_bid"]; old_user=int(a["current_bidder"])
            if old_user:
                c.execute("UPDATE users SET balance=balance+? WHERE id=?",(old,old_user))
                c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(old_user,old,"auction_refund",f"auction:{auction_id}",now_iso()))
            c.execute("UPDATE users SET balance=balance-? WHERE id=?",(amount,uid))
            c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(uid,-amount,"auction_hold",f"auction:{auction_id}",now_iso()))
            c.execute("UPDATE auctions SET current_bid=?,current_bidder=? WHERE id=?",(amount,uid,auction_id)); c.commit(); return old,old_user
    def close(self,auction_id,actor):
        with self.db.connection() as c:
            c.execute("BEGIN IMMEDIATE"); a=c.execute("SELECT * FROM auctions WHERE id=?",(auction_id,)).fetchone()
            if not a or a["status"]!="open": raise ValueError("Auction is already closed.")
            if actor!=a["creator_id"]: raise PermissionError("Only the creator can close this auction.")
            if int(a["current_bidder"]):
                winner=int(a["current_bidder"]); amount=int(a["current_bid"]); creator=int(a["creator_id"]); t=now_iso()
                c.execute("UPDATE users SET balance=balance+? WHERE id=?",(amount,creator))
                c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(creator,amount,"auction_sale",f"auction:{auction_id}",t))
                c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(winner,0,"auction_win",f"auction:{auction_id}:{a['item']}",t))
            c.execute("UPDATE auctions SET status='closed' WHERE id=?",(auction_id,)); c.commit(); return a

    def close_expired(self) -> int:
        count=0
        with self.db.connection() as c:
            rows=c.execute("SELECT id,creator_id FROM auctions WHERE status='open' AND ends_at<=?",(now_iso(),)).fetchall()
        for row in rows:
            try: self.close(int(row[0]), int(row[1])); count += 1
            except Exception: pass
        return count
