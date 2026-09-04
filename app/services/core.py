from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import Database, now_iso


class Cooldowns:
    def __init__(self): self._until: dict[tuple[int,str], datetime] = {}
    def remaining(self, uid: int, key: str) -> int:
        end = self._until.get((uid,key)); now = datetime.now(timezone.utc)
        return max(0, int((end-now).total_seconds())) if end else 0
    def set(self, uid: int, key: str, seconds: int) -> None:
        self._until[(uid,key)] = datetime.now(timezone.utc) + timedelta(seconds=seconds)


class Economy:
    def __init__(self, db: Database, start_balance: int): self.db, self.start_balance = db, start_balance
    def ensure(self, uid: int, username: str, first_name: str): return self.db.ensure_user(uid, username, first_name, self.start_balance)
    def balance(self, uid: int) -> int: return int(self.db.user(uid)["balance"])
    def credit(self, uid: int, amount: int, kind: str, note: str = "") -> int: return self.db.add_balance(uid, amount, kind, note)
    def debit(self, uid: int, amount: int, kind: str, note: str = "") -> int: return self.db.add_balance(uid, -amount, kind, note)

    def steal(self, thief: int, target: int, cooldowns: Cooldowns, cooldown: int, requested: int | None = None) -> tuple[bool,str]:
        if thief == target: return False, "You cannot steal from yourself."
        left = cooldowns.remaining(thief, "steal")
        if left: return False, f"Steal is on cooldown. Try again in {left}s."
        with self.db.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            a = c.execute("SELECT * FROM users WHERE id=?", (thief,)).fetchone()
            b = c.execute("SELECT * FROM users WHERE id=?", (target,)).fetchone()
            if not a or not b: return False, "Both users must have an account with the bot."
            if b["is_banned"]: return False, "That user is unavailable."
            if b["shield_until"] and datetime.fromisoformat(b["shield_until"]) > datetime.now(timezone.utc): return False, "🛡️ Their shield is active."
            available = int(b["balance"])
            if available <= 100: return False, "That user cannot be stolen below the 100-coin protection floor."
            max_steal = available - 100
            if requested is not None:
                if requested <= 0: return False, "Steal amount must be greater than zero."
                if requested > max_steal: return False, f"You can steal at most *{max_steal:,}* coins from this user."
                amount = requested
            else:
                low = min(max_steal, max(1, available // 10))
                high = min(max_steal, max(low, max_steal // 4, 1))
                amount = random.randint(low, high)
            c.execute("UPDATE users SET balance=balance+?,updated_at=? WHERE id=?", (amount,now_iso(),thief))
            c.execute("UPDATE users SET balance=balance-?,updated_at=? WHERE id=?", (amount,now_iso(),target))
            t=now_iso()
            c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(thief,amount,"steal",f"from:{target}",t))
            c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(target,-amount,"stolen",f"by:{thief}",t))
            c.commit()
        cooldowns.set(thief,"steal",cooldown)
        return True, f"💰 You successfully stole *{amount:,}* coins."


class Rewards:
    def __init__(self, db: Database, daily: int, referral: int, milestones: tuple[tuple[int,int], ...] = ()):
        self.db, self.daily, self.referral, self.milestones = db, daily, referral, tuple(sorted(milestones))
    def checkin(self, uid: int) -> tuple[bool,int,int]:
        with self.db.connection() as c:
            c.execute("BEGIN IMMEDIATE"); row=c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
            today=datetime.now(timezone.utc).date().isoformat()
            if row["last_checkin"] == today: return False, int(row["streak"]), int(row["balance"])
            yesterday=(datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat()
            streak=int(row["streak"])+1 if row["last_checkin"]==yesterday else 1
            bonus=self.daily + min(streak*10,500)
            c.execute("UPDATE users SET balance=balance+?,streak=?,last_checkin=?,updated_at=? WHERE id=?",(bonus,streak,today,now_iso(),uid))
            c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(uid,bonus,"checkin",f"streak:{streak}",now_iso())); c.commit()
            return True,streak,int(row["balance"])+bonus

    def refer(self, new_uid: int, inviter: int) -> tuple[bool,str]:
        if new_uid==inviter: return False,"You cannot refer yourself."
        with self.db.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            n=c.execute("SELECT referred_by FROM users WHERE id=?",(new_uid,)).fetchone()
            inv=c.execute("SELECT id FROM users WHERE id=?",(inviter,)).fetchone()
            if not n or not inv: return False,"User account not found."
            if n[0] is not None: return False,"This account already has a referrer."
            c.execute("UPDATE users SET referred_by=?,updated_at=? WHERE id=?",(inviter,now_iso(),new_uid))
            c.execute("INSERT OR IGNORE INTO referrals(user_id,inviter_id,rewarded,created_at) VALUES(?,?,0,?)",(new_uid,inviter,now_iso()))
            c.execute("UPDATE users SET balance=balance+?,updated_at=? WHERE id=?",(self.referral,now_iso(),inviter))
            c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(inviter,self.referral,"referral",f"user:{new_uid}",now_iso()))
            c.execute("UPDATE referrals SET rewarded=1 WHERE user_id=?",(new_uid,))
            referral_count=int(c.execute("SELECT COUNT(*) FROM referrals WHERE inviter_id=? AND rewarded=1",(inviter,)).fetchone()[0])
            milestone_awards=[]
            for milestone, bonus in self.milestones:
                if referral_count >= milestone:
                    claimed=c.execute("SELECT 1 FROM referral_milestone_rewards WHERE user_id=? AND milestone=?",(inviter,milestone)).fetchone()
                    if not claimed:
                        c.execute("INSERT INTO referral_milestone_rewards(user_id,milestone,reward,created_at) VALUES(?,?,?,?)",(inviter,milestone,bonus,now_iso()))
                        c.execute("UPDATE users SET balance=balance+?,updated_at=? WHERE id=?",(bonus,now_iso(),inviter))
                        c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(inviter,bonus,"referral_milestone",f"milestone:{milestone}",now_iso()))
                        milestone_awards.append((milestone,bonus))
            c.commit()
        extra = "".join(f" Milestone {m} reached: *{b:,}* bonus." for m,b in milestone_awards)
        return True,f"Referral bonus *{self.referral:,}* coins added to the inviter.{extra}"

    def coupon(self, uid:int, code:str)->tuple[bool,str]:
        code=code.strip().upper()
        with self.db.connection() as c:
            c.execute("BEGIN IMMEDIATE"); cp=c.execute("SELECT * FROM coupons WHERE code=?",(code,)).fetchone()
            if not cp or not cp["active"] or cp["uses"]>=cp["max_uses"]: return False,"Invalid or exhausted coupon."
            try: c.execute("INSERT INTO coupon_uses(code,user_id,created_at) VALUES(?,?,?)",(code,uid,now_iso()))
            except Exception: return False,"You have already redeemed this coupon."
            c.execute("UPDATE coupons SET uses=uses+1 WHERE code=?",(code,))
            c.execute("UPDATE users SET balance=balance+?,updated_at=? WHERE id=?",(cp["reward"],now_iso(),uid))
            c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(uid,cp["reward"],"coupon",code,now_iso())); c.commit()
        return True,f"🎁 Coupon redeemed. *{cp['reward']:,}* coins added."


class Games:
    def __init__(self,db:Database): self.db=db
    def flip(self,uid:int,amount:int)->tuple[bool,str]:
        with self.db.connection() as c:
            c.execute("BEGIN IMMEDIATE"); row=c.execute("SELECT balance FROM users WHERE id=?",(uid,)).fetchone()
            if not row or amount<=0 or int(row[0])<amount: return False,"Insufficient balance."
            win=random.choice([True,False]); delta=amount if win else -amount
            c.execute("UPDATE users SET balance=balance+?,updated_at=? WHERE id=?",(delta,now_iso(),uid))
            c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(uid,delta,"flip","win" if win else "loss",now_iso())); c.commit()
        return True,(f"🪙 Heads! You won *{amount:,}* coins." if win else f"🪙 Tails. You lost *{amount:,}* coins.")

    def create_trust(self,chat_id,initiator,target,amount:int=0)->int:
        if initiator==target: raise ValueError("You cannot challenge yourself.")
        if amount<0: raise ValueError("Amount cannot be negative.")
        with self.db.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            for uid in (initiator,target):
                row=c.execute("SELECT balance,is_banned FROM users WHERE id=?",(uid,)).fetchone()
                if not row: raise ValueError("Both players need an account.")
                if row["is_banned"]: raise ValueError("A player is unavailable.")
                if amount and int(row["balance"])<amount: raise ValueError("Both players need enough coins for this stake.")
            if amount:
                t=now_iso()
                for uid in (initiator,target):
                    c.execute("UPDATE users SET balance=balance-?,updated_at=? WHERE id=?",(amount,t,uid))
                    c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(uid,-amount,"trust_hold","pending",t))
            expires=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()
            cur=c.execute("INSERT INTO trust_games(chat_id,initiator_id,target_id,stake,created_at,expires_at) VALUES(?,?,?,?,?,?)",(chat_id,initiator,target,amount,now_iso(),expires)); c.commit(); return cur.lastrowid

    def _expire_in_connection(self, c, g):
        if g["status"] != "open": return
        stake=int(g["stake"]); t=now_iso()
        if stake:
            for uid in (int(g["initiator_id"]), int(g["target_id"])):
                c.execute("UPDATE users SET balance=balance+?,updated_at=? WHERE id=?",(stake,t,uid))
                c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(uid,stake,"trust_refund",f"game:{g['id']}",t))
        c.execute("UPDATE trust_games SET status='expired',resolved_at=? WHERE id=?",(t,int(g["id"])))

    def expire_trust_games(self) -> int:
        count=0
        with self.db.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            rows=c.execute("SELECT * FROM trust_games WHERE status='open' AND expires_at IS NOT NULL AND expires_at<=?",(now_iso(),)).fetchall()
            for g in rows:
                self._expire_in_connection(c,g); count += 1
            c.commit()
        return count

    def choose_trust(self,game_id,uid,choice)->tuple[bool,str]:
        if choice not in {"trust","betray"}: return False,"Invalid choice."
        with self.db.connection() as c:
            c.execute("BEGIN IMMEDIATE"); g=c.execute("SELECT * FROM trust_games WHERE id=?",(game_id,)).fetchone()
            if not g or g["status"]!="open": return False,"This game is no longer active."
            if g["expires_at"] and datetime.fromisoformat(g["expires_at"]) <= datetime.now(timezone.utc):
                self._expire_in_connection(c, g)
                c.commit()
                return False,"This Trust Game expired; all held stakes were returned."
            col="initiator_choice" if uid==g["initiator_id"] else "target_choice" if uid==g["target_id"] else None
            if not col: return False,"You are not a player in this game."
            if g[col]: return False,"You already chose."
            c.execute(f"UPDATE trust_games SET {col}=? WHERE id=?",(choice,game_id))
            g=c.execute("SELECT * FROM trust_games WHERE id=?",(game_id,)).fetchone()
            if g["initiator_choice"] and g["target_choice"]:
                stake=int(g["stake"]); a=int(g["initiator_id"]); b=int(g["target_id"]); ac=g["initiator_choice"]; bc=g["target_choice"]; t=now_iso()
                if stake:
                    if ac==bc=="trust":
                        for uid in (a,b):
                            c.execute("UPDATE users SET balance=balance+?,updated_at=? WHERE id=?",(stake*2,t,uid))
                            c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(uid,stake*2,"trust_reward","cooperate",t))
                        result=f"🤝 Both trusted. Each player receives *{stake*2:,}* coins."
                    elif ac==bc=="betray":
                        for uid in (a,b):
                            c.execute("UPDATE users SET balance=balance+?,updated_at=? WHERE id=?",(stake,t,uid))
                        result="😈 Both betrayed. Your stakes were returned."
                    else:
                        winner=a if ac=="betray" else b; loser=b if winner==a else a
                        c.execute("UPDATE users SET balance=balance+?,updated_at=? WHERE id=?",(stake*3,t,winner))
                        c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(winner,stake*3,"trust_reward","betrayal",t))
                        result=f"😈 Betrayal! The betrayer wins *{stake*3:,}* coins."
                else:
                    result="🤝 Both trusted." if ac==bc=="trust" else "😈 A betrayal happened."
                c.execute("UPDATE trust_games SET status='resolved',resolved_at=? WHERE id=?",(t,game_id)); c.commit(); return True,result
            c.commit(); return True,"Choice recorded. Waiting for the other player."
