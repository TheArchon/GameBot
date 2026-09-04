from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            con = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA foreign_keys=ON")
            try:
                yield con
            finally:
                con.close()

    def init_schema(self) -> None:
        with self.connection() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY, username TEXT, first_name TEXT NOT NULL DEFAULT '',
              language TEXT NOT NULL DEFAULT 'en', balance INTEGER NOT NULL DEFAULT 0 CHECK(balance >= 0),
              streak INTEGER NOT NULL DEFAULT 0, last_checkin TEXT, referred_by INTEGER,
              shield_until TEXT, is_banned INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chats (
              id INTEGER PRIMARY KEY, title TEXT NOT NULL DEFAULT '', ai_enabled INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
              id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, chat_id INTEGER NOT NULL,
              role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_memories_context ON memories(user_id, chat_id, id);
            CREATE TABLE IF NOT EXISTS transactions (
              id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount INTEGER NOT NULL,
              kind TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id, id);
            CREATE TABLE IF NOT EXISTS coupons (
              code TEXT PRIMARY KEY, reward INTEGER NOT NULL CHECK(reward > 0), max_uses INTEGER NOT NULL CHECK(max_uses > 0),
              uses INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS coupon_uses (
              code TEXT NOT NULL, user_id INTEGER NOT NULL, created_at TEXT NOT NULL,
              PRIMARY KEY(code, user_id), FOREIGN KEY(code) REFERENCES coupons(code) ON DELETE CASCADE,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS auctions (
              id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, creator_id INTEGER NOT NULL,
              item TEXT NOT NULL, current_bid INTEGER NOT NULL, current_bidder INTEGER NOT NULL,
              status TEXT NOT NULL DEFAULT 'open', ends_at TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trust_games (
              id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, initiator_id INTEGER NOT NULL,
              target_id INTEGER NOT NULL, stake INTEGER NOT NULL DEFAULT 0, initiator_choice TEXT, target_choice TEXT,
              status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL, resolved_at TEXT, expires_at TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (
              key TEXT PRIMARY KEY, value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS referrals (
              user_id INTEGER PRIMARY KEY, inviter_id INTEGER NOT NULL, rewarded INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS referral_milestone_rewards (
              user_id INTEGER NOT NULL, milestone INTEGER NOT NULL, reward INTEGER NOT NULL, created_at TEXT NOT NULL,
              PRIMARY KEY(user_id, milestone)
            );
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, actor_id INTEGER,
              chat_id INTEGER, payload TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
            );
            """)
            # Lightweight forward migration for databases created by earlier builds.
            cols={r[1] for r in c.execute("PRAGMA table_info(trust_games)").fetchall()}
            if "stake" not in cols:
                c.execute("ALTER TABLE trust_games ADD COLUMN stake INTEGER NOT NULL DEFAULT 0")
            if "expires_at" not in cols:
                c.execute("ALTER TABLE trust_games ADD COLUMN expires_at TEXT")

    def get_setting(self, key: str, default: str = "") -> str:
        with self.connection() as c:
            row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return str(row[0]) if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connection() as c:
            c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
            c.commit()

    def ensure_user(self, uid: int, username: str = "", first_name: str = "", start_balance: int = 0) -> sqlite3.Row:
        t = now_iso()
        with self.connection() as c:
            c.execute("INSERT INTO users(id,username,first_name,balance,created_at,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, updated_at=excluded.updated_at", (uid, username, first_name, start_balance, t, t))
            c.commit()
            return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

    def user_by_username(self, username: str) -> sqlite3.Row | None:
        username=username.lstrip("@").lower()
        with self.connection() as c:
            return c.execute("SELECT * FROM users WHERE lower(username)=?",(username,)).fetchone()

    def user(self, uid: int) -> sqlite3.Row | None:
        with self.connection() as c:
            return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


    def ensure_chat(self, chat_id: int, title: str = "", ai_enabled: int = 1) -> None:
        t = now_iso()
        with self.connection() as c:
            c.execute("INSERT INTO chats(id,title,ai_enabled,created_at,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,updated_at=excluded.updated_at", (chat_id,title,ai_enabled,t,t))
            c.commit()

    def transfer(self, sender: int, receiver: int, amount: int) -> tuple[bool,str]:
        if sender == receiver: return False, "You cannot send coins to yourself."
        if amount <= 0: return False, "Amount must be greater than zero."
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            a=c.execute("SELECT * FROM users WHERE id=?",(sender,)).fetchone(); b=c.execute("SELECT * FROM users WHERE id=?",(receiver,)).fetchone()
            if not a or not b: return False, "Both users must have an account with the bot."
            if a["is_banned"] or b["is_banned"]: return False, "This transfer is unavailable."
            if int(a["balance"]) < amount: return False, "Insufficient balance."
            t=now_iso()
            c.execute("UPDATE users SET balance=balance-?,updated_at=? WHERE id=?",(amount,t,sender))
            c.execute("UPDATE users SET balance=balance+?,updated_at=? WHERE id=?",(amount,t,receiver))
            c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(sender,-amount,"send",f"to:{receiver}",t))
            c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",(receiver,amount,"receive",f"from:{sender}",t)); c.commit()
            return True, f"💸 Sent *{amount:,}* coins successfully."

    def charm_score(self, uid: int) -> int:
        with self.connection() as c:
            return int(c.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND kind='charm'",(uid,)).fetchone()[0])

    def stolen_total(self, uid: int) -> int:
        with self.connection() as c:
            return int(c.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND kind='steal'",(uid,)).fetchone()[0])

    def referral_count(self, uid: int) -> int:
        with self.connection() as c:
            return int(c.execute("SELECT COUNT(*) FROM referrals WHERE inviter_id=? AND rewarded=1",(uid,)).fetchone()[0])

    def referral_milestones_claimed(self, uid: int) -> set[int]:
        with self.connection() as c:
            return {int(r[0]) for r in c.execute("SELECT milestone FROM referral_milestone_rewards WHERE user_id=?", (uid,)).fetchall()}

    def stats(self) -> dict[str, int]:
        with self.connection() as c:
            users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            balance = c.execute("SELECT COALESCE(SUM(balance),0) FROM users").fetchone()[0]
            groups = c.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
            return {"users": users, "balance": balance, "groups": groups}

    def add_balance(self, uid: int, amount: int, kind: str, note: str = "") -> int:
        if amount == 0:
            row = self.user(uid); return int(row["balance"]) if row else 0
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()
            if not row: raise ValueError("User not found")
            new_balance = int(row[0]) + amount
            if new_balance < 0: raise ValueError("Insufficient balance")
            c.execute("UPDATE users SET balance=?,updated_at=? WHERE id=?", (new_balance, now_iso(), uid))
            c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)", (uid, amount, kind, note, now_iso()))
            c.commit()
            return new_balance

    def leaderboard(self, limit: int = 10) -> list[sqlite3.Row]:
        with self.connection() as c:
            return c.execute("SELECT id,username,first_name,balance FROM users WHERE is_banned=0 ORDER BY balance DESC,id ASC LIMIT ?", (limit,)).fetchall()

    def remember(self, uid: int, chat_id: int, role: str, content: str) -> None:
        with self.connection() as c:
            c.execute("INSERT INTO memories(user_id,chat_id,role,content,created_at) VALUES(?,?,?,?,?)", (uid, chat_id, role, content[:4000], now_iso()))
            c.execute("DELETE FROM memories WHERE user_id=? AND chat_id=? AND id NOT IN (SELECT id FROM memories WHERE user_id=? AND chat_id=? ORDER BY id DESC LIMIT 20)", (uid, chat_id, uid, chat_id))
            c.commit()

    def memory(self, uid: int, chat_id: int) -> list[sqlite3.Row]:
        with self.connection() as c:
            return c.execute("SELECT role,content FROM memories WHERE user_id=? AND chat_id=? ORDER BY id ASC", (uid, chat_id)).fetchall()

    def clear_memory(self, uid: int, chat_id: int) -> None:
        with self.connection() as c:
            c.execute("DELETE FROM memories WHERE user_id=? AND chat_id=?", (uid, chat_id)); c.commit()

    def log_event(self, event_type: str, actor_id: int | None = None, chat_id: int | None = None, payload: dict[str, Any] | None = None) -> None:
        with self.connection() as c:
            c.execute("INSERT INTO events(event_type,actor_id,chat_id,payload,created_at) VALUES(?,?,?,?,?)", (event_type, actor_id, chat_id, json.dumps(payload or {}, ensure_ascii=False), now_iso())); c.commit()
