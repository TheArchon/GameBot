# ARCHON AI Companion Bot

A production-oriented Telegram companion bot inspired by the interaction model shown in the supplied reference recording. The implementation is original and does not copy proprietary source code, assets, or branding.

## Included

- Video-matched Home card with bundled start artwork and paginated Help Center UX
- Configurable Add-to-Group, Support, Updates and Owner buttons
- Group `/ai on|off` protected by real Telegram admin checks
- Telegram command menu registration on startup
- AI companion with per-user/per-chat rolling memory
- `/resmemory` and `/stats`
- Profile, wallet, leaderboard
- `/flirt`, `/shayari`, `/steal`, `/amount`, `/shield`
- Persistent two-player `/trust` game
- Virtual-coin `/flip`
- Persistent `/bid` auction with refunds and settlement
- Daily check-in and streak rewards
- Referral links, per-referral rewards and persistent referral milestone bonuses/progress
- Coupon creation/redemption with duplicate-use protection
- Owner controls: maintenance, broadcast, balance management, ban/unban, statistics
- Group AI toggle
- SQLite WAL database with foreign keys, constraints and transaction records
- Graceful polling/retry behavior
- Docker deployment
- Offline smoke tests and pytest tests

## Important

Virtual coins are entertainment points only and have no cash value. Do not connect the economy to real-money deposits, withdrawals or gambling.

## Setup

1. Copy `.env.example` to `.env`.
2. Set `BOT_TOKEN` and your numeric `OWNER_IDS`.
3. Optionally set `BOT_USERNAME`, `SUPPORT_URL`, `UPDATES_URL`, `OWNER_URL`, and the bundled `START_IMAGE_PATH`.
4. Optionally set an OpenAI-compatible AI endpoint using `AI_API_URL`, `AI_API_KEY`, and `AI_MODEL`.
5. Run `python -m app`.

Python 3.11+ is recommended. The bot runtime uses Python's standard library; `requirements.txt` only adds the pytest test runner used by the validation suite.

## Docker

```bash
docker compose up -d --build
docker compose logs -f bot
```

## Validation

```bash
python -m compileall -q app tests scripts
python -m pytest -q
python scripts/smoke_test.py
```

## Production notes

- Keep `.env` private.
- Put the bot behind a process supervisor/container restart policy.
- Back up `data/bot.sqlite3` regularly.
- For very large deployments, migrate the database layer to PostgreSQL while keeping the service interfaces unchanged.

## GitHub self-update

The owner can update a running installation directly from Telegram with `/update`. The VPS installation must itself be a Git clone with the `origin` remote configured.

Update flow:

1. `/update` is accepted only from `OWNER_IDS`.
2. The updater refuses to overwrite uncommitted local VPS changes.
3. It fetches and fast-forwards the configured branch (`UPDATE_BRANCH`, default `main`).
4. If `requirements.txt` changed, dependencies are installed when `UPDATE_INSTALL_DEPS=1`.
5. Python compilation and the test suite run before restart.
6. If validation fails, the Git commit is rolled back to the previous commit.
7. If validation passes, the process is replaced with `python -m app`, loading the new code without manually reconnecting to the VPS.

For a private GitHub repository, configure Git authentication on the VPS (SSH deploy key or another secure Git credential mechanism). Never put GitHub credentials or tokens in the bot source or `.env` unless your deployment requires it.

## Final feature notes

- Video-inspired Kai start card and five-page Help Center are bundled with the project.
- Private chats can use AI directly; group AI is opt-in and responds only to replies/mentions after an admin enables it.
- Trust games have held stakes, private choices, expiry and automatic stake refunds.
- Auctions have starting bids, named items, bid holds/refunds, expiry, and winner-to-creator settlement.
- `/send`, `/steal` and related commands can resolve known usernames and, when Telegram permits, live public usernames.
- `/language` supports English, Hindi, Indonesian, Italian and Urdu help content (Help Center content is available in English, Hindi, Indonesian, Italian and Urdu).
- Optional Telegram custom emoji IDs can be configured with `EMOJI_*`; normal Unicode remains the safe fallback.

## Professional modular layout

The bot uses a layered layout: `handlers/` contains command/callback behaviour,
`keyboards/` contains Telegram inline-keyboard builders, `services/` contains domain
logic, and `locales/<lang>.json` contains all text for each language in one file.
There is no legacy `app/ui.py` or `app/handlers.py` feature facade; feature logic is fully modular. `/start` lives in `app/handlers/start.py`, Help Center logic lives in
`app/handlers/help.py`, and their buttons live in `app/keyboards/home.py` and
`app/keyboards/help.py` respectively.

Help navigation uses `Prev | current/5 | Next` plus a dedicated `Home` row, and the
center page indicator updates automatically from `1/5` through `5/5`.
