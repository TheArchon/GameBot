from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
            value = value[1:-1]
        os.environ[key] = value


@dataclass(frozen=True)
class Config:
    bot_token: str
    owner_ids: frozenset[int]
    bot_username: str
    database_path: str
    ai_api_url: str
    ai_api_key: str
    ai_model: str
    ai_system_prompt: str
    daily_reward: int
    referral_reward: int
    start_balance: int
    steal_cooldown: int
    shield_cost: int
    shield_hours: int
    flip_min: int
    flip_max: int
    bid_min: int
    bid_duration_minutes: int
    start_image_path: str = "assets/start.jpg"
    support_url: str = ""
    updates_url: str = ""
    owner_url: str = ""
    emoji_heart: str = ""
    emoji_help: str = ""
    emoji_game: str = ""
    emoji_coin: str = ""
    emoji_shield: str = ""
    referral_milestones: tuple[tuple[int,int], ...] = ()

    @classmethod
    def from_env(cls) -> "Config":
        _load_dotenv()
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token or token.startswith("123456"):
            raise ValueError("BOT_TOKEN is missing or still uses the example value.")
        owners = frozenset(int(x.strip()) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip())
        if not owners:
            raise ValueError("OWNER_IDS must contain at least one Telegram user ID.")
        raw_milestones=os.getenv("REFERRAL_MILESTONES", "1:5000,5:15000,10:30000,25:75000")
        milestones=[]
        for item in raw_milestones.split(","):
            try:
                count, reward = item.split(":", 1)
                count, reward = int(count), int(reward)
                if count > 0 and reward > 0:
                    milestones.append((count, reward))
            except ValueError:
                continue
        milestones=tuple(sorted(set(milestones)))
        return cls(
            bot_token=token,
            owner_ids=owners,
            bot_username=os.getenv("BOT_USERNAME", "").lstrip("@").strip(),
            database_path=os.getenv("DATABASE_PATH", "data/bot.sqlite3"),
            ai_api_url=os.getenv("AI_API_URL", "").strip(),
            ai_api_key=os.getenv("AI_API_KEY", "").strip(),
            ai_model=os.getenv("AI_MODEL", "").strip(),
            ai_system_prompt=os.getenv("AI_SYSTEM_PROMPT", "You are a friendly, witty and respectful Telegram companion. Keep replies natural, concise and safe."),
            daily_reward=max(0, int(os.getenv("DAILY_REWARD", "250"))),
            referral_reward=max(0, int(os.getenv("REFERRAL_REWARD", "500"))),
            referral_milestones=milestones,
            start_balance=max(0, int(os.getenv("START_BALANCE", "500"))),
            steal_cooldown=max(1, int(os.getenv("STEAL_COOLDOWN", "3600"))),
            shield_cost=max(0, int(os.getenv("SHIELD_COST", "200"))),
            shield_hours=max(1, int(os.getenv("SHIELD_HOURS", "2"))),
            flip_min=max(1, int(os.getenv("FLIP_MIN", "10"))),
            flip_max=max(1, int(os.getenv("FLIP_MAX", "10000"))),
            bid_min=max(1, int(os.getenv("BID_MIN", "50"))),
            bid_duration_minutes=max(1, int(os.getenv("BID_DURATION_MINUTES", "10"))),
            start_image_path=os.getenv("START_IMAGE_PATH", "assets/start.jpg").strip(),
            support_url=os.getenv("SUPPORT_URL", "").strip(),
            updates_url=os.getenv("UPDATES_URL", "").strip(),
            owner_url=os.getenv("OWNER_URL", "").strip(),
            emoji_heart=os.getenv("EMOJI_HEART", "").strip(),
            emoji_help=os.getenv("EMOJI_HELP", "").strip(),
            emoji_game=os.getenv("EMOJI_GAME", "").strip(),
            emoji_coin=os.getenv("EMOJI_COIN", "").strip(),
            emoji_shield=os.getenv("EMOJI_SHIELD", "").strip(),
        )
