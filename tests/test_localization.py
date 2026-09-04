import json
from pathlib import Path
from app.locales.loader import SUPPORTED, load

BASE=Path(__file__).resolve().parents[1]/"app"/"locales"

def test_each_language_is_one_complete_file():
    required={"buttons","messages","help","languages"}
    for lang in SUPPORTED:
        data=json.loads((BASE/f"{lang}.json").read_text(encoding="utf-8"))
        assert required <= data.keys()
        assert set(data["buttons"]) == set(load("en")["buttons"])
        assert set(data["messages"]) == set(load("en")["messages"])
        assert set(data["help"]) == {"1","2","3","4","5"}


def test_no_hardcoded_button_labels_in_ui_handlers():
    for name in ("app/keyboards/home.py","app/keyboards/help.py","app/keyboards/profile.py","app/keyboards/wallet.py","app/keyboards/games.py"):
        text=(Path(__file__).resolve().parents[1]/name).read_text(encoding="utf-8")
        # Button constructors should receive localized dictionary values, not quoted UI labels.
        assert 'btn("' not in text


def test_all_button_custom_emoji_keys(monkeypatch):
    from app.emoji import EMOJI_ENV, custom_emoji_ids, emoji_for
    for key, env in EMOJI_ENV.items():
        monkeypatch.setenv(env, "123456789")
        assert '<tg-emoji emoji-id="123456789">' in emoji_for(key, "fallback")
    monkeypatch.delenv("EMOJI_HELP", raising=False)
    assert emoji_for("help", "fallback") == "fallback"


def test_professional_modular_ui_layout():
    root = Path(__file__).resolve().parents[1] / "app"
    expected = [
        "handlers/start.py", "handlers/help.py", "handlers/economy.py", "handlers/games.py",
        "handlers/ai.py", "handlers/admin.py", "handlers/callbacks.py",
        "keyboards/home.py", "keyboards/help.py", "keyboards/profile.py",
        "keyboards/wallet.py", "keyboards/games.py", "keyboards/language.py",
    ]
    assert all((root / item).is_file() for item in expected)
    # Feature UI logic is fully modular; feature code must not depend on legacy facades.
    handler_text = "\n".join(p.read_text(encoding="utf-8") for p in (root / "handlers").glob("*.py"))
    assert "from app.ui" not in handler_text


def test_help_page_indicator_changes():
    from app.keyboards.help import help_keyboard
    for page in range(1, 6):
        markup = help_keyboard(page, "en")
        labels = [b["text"] for b in markup["inline_keyboard"][0]]
        assert any(f"{page}/5" in label for label in labels)
