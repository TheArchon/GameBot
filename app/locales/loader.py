from __future__ import annotations
import json
import re
from functools import lru_cache
from pathlib import Path

SUPPORTED = ("en", "hi", "id", "it", "ur")
BASE = Path(__file__).resolve().parent

@lru_cache(maxsize=len(SUPPORTED))
def load(language: str = "en") -> dict:
    language = language if language in SUPPORTED else "en"
    return json.loads((BASE / f"{language}.json").read_text(encoding="utf-8"))

def t(language: str, key: str, **kwargs) -> str:
    data = load(language)
    value = data
    for part in key.split("."):
        value = value[part]
    return value.format(**kwargs) if kwargs else value

def localize_result(language: str, text: str) -> str:
    """Translate dynamic service results while keeping domain services language-neutral."""
    lang = language if language in SUPPORTED else "en"
    patterns = [
        (r"^You cannot send coins to yourself\.$", "send_self"),
        (r"^Amount must be greater than zero\.$", "amount_positive"),
        (r"^Both users must have an account with the bot\.$", "both_accounts"),
        (r"^This transfer is unavailable\.$", "transfer_unavailable"),
        (r"^Insufficient balance\.$", "insufficient"),
        (r"^💸 Sent \*(\d[\d,]*)\* coins successfully\.$", "sent"),
        (r"^You cannot steal from yourself\.$", "steal_self"),
        (r"^Steal is on cooldown\. Try again in (\d+)s\.$", "steal_cooldown"),
        (r"^That user is unavailable\.$", "user_unavailable"),
        (r"^🛡️ Their shield is active\.$", "shield_active_result"),
        (r"^That user cannot be stolen below the 100-coin protection floor\.$", "steal_floor"),
        (r"^Steal amount must be greater than zero\.$", "steal_positive"),
        (r"^You can steal at most \*(\d[\d,]*)\* coins from this user\.$", "steal_max"),
        (r"^💰 You successfully stole \*(\d[\d,]*)\* coins\.$", "steal_success"),
        (r"^🪙 Heads! You won \*(\d[\d,]*)\* coins\.$", "flip_win"),
        (r"^🪙 Tails\. You lost \*(\d[\d,]*)\* coins\.$", "flip_loss"),
        (r"^Invalid choice\.$", "trust_invalid"),
        (r"^This game is no longer active\.$", "trust_inactive"),
        (r"^This Trust Game expired; all held stakes were returned\.$", "trust_expired"),
        (r"^You are not a player in this game\.$", "trust_not_player"),
        (r"^You already chose\.$", "trust_chosen"),
        (r"^Choice recorded\. Waiting for the other player\.$", "trust_waiting"),
        (r"^🤝 Both trusted\.$", "trust_both"),
        (r"^🤝 Both trusted\. Each player receives \*(\d[\d,]*)\* coins\.$", "trust_both_reward"),
        (r"^😈 Both betrayed\. Your stakes were returned\.$", "trust_both_betray"),
        (r"^😈 Betrayal! The betrayer wins \*(\d[\d,]*)\* coins\.$", "trust_betrayal"),
        (r"^Invalid or exhausted coupon\.$", "coupon_invalid"),
        (r"^You have already redeemed this coupon\.$", "coupon_used"),
        (r"^🎁 Coupon redeemed\. \*(\d[\d,]*)\* coins added\.$", "coupon_success"),
    ]
    for pattern,key in patterns:
        m=re.match(pattern,text)
        if not m: continue
        vals=list(m.groups())
        return t(lang,f"results.{key}",**({f"v{i}":v for i,v in enumerate(vals,1)}))
    return text
