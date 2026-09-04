from __future__ import annotations

def user_from_message(m):
    u=m.get("from",{}); return int(u.get("id")),u.get("username") or "",u.get("first_name") or "User"

def target_id(m):
    r=m.get("reply_to_message")
    if r and r.get("from"): return int(r["from"]["id"])
    return None

def random_choice(items):
    import random
    return random.choice(items)
