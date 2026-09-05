from __future__ import annotations
import html
import re

_TG_RE = re.compile(r'<tg-emoji\s+emoji-id="([0-9]+)">(.*?)</tg-emoji>')

def md_to_html(text: str) -> str:
    protected = []
    def hold(m):
        protected.append(m.group(0))
        return f"\x00TG{len(protected)-1}\x00"
    text = _TG_RE.sub(hold, text)
    text = html.escape(text, quote=False)
    text = re.sub(r'\[\[quote\]\](.*?)\[\[/quote\]\]', r'<blockquote>\1</blockquote>', text, flags=re.DOTALL)
    text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*([^*\n]+)\*', r'<b>\1</b>', text)
    for i, value in enumerate(protected):
        text = text.replace(f"\x00TG{i}\x00", value)
    return text
