# Security Notes

- Never commit `.env` or a real bot token.
- Owner IDs should be numeric Telegram IDs, not usernames.
- The bot does not log OTPs, passwords or bot tokens.
- Virtual economy operations are transactional and enforce non-negative balances.
- Real-money wagering, deposits and withdrawals are intentionally not implemented.
