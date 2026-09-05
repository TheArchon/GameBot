from __future__ import annotations
import html
import re

_TG_RE = re.compile(r'<tg-emoji\s+emoji-id="([0-9]+)">(.*?)</tg-emoji>')

def md_to_html(text: str) -> str:
    """Small, safe Markdown subset used by this bot -> Telegram HTML."""
    protected = []

    def hold(m):
        protected.append(m.group(0))
        return f"\x00TG{len(protected)-1}\x00"

    text = _TG_RE.sub(hold, text)
    text = html.escape(text, quote=False)

    lines = text.split("\n")
    output = []
    quote_lines = []

    def flush_quote():
        if quote_lines:
            output.append("<blockquote>" + "\n".join(quote_lines) + "</blockquote>")
            quote_lines.clear()

    for line in lines:
        if line.startswith("> "):
            quote_lines.append(line[2:])
        elif line.startswith(">"):
            quote_lines.append(line[1:].lstrip())
        else:
            flush_quote()
            output.append(line)

    flush_quote()
    text = "\n".join(output)

    text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*([^*\n]+)\*', r'<b>\1</b>', text)

    for i, value in enumerate(protected):
        text = text.replace(f"\x00TG{i}\x00", value)

    return text
