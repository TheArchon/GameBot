from __future__ import annotations
import json, urllib.parse, urllib.request, mimetypes, uuid
from pathlib import Path
from app.formatting import md_to_html
from .emoji import render_message_emojis

class TelegramError(RuntimeError): pass

class Telegram:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}"

    def call(self, method: str, **params):
        data = {k: v for k, v in params.items() if v is not None}
        encoded = urllib.parse.urlencode({
            k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
            for k, v in data.items()
        }).encode()
        try:
            req = urllib.request.Request(f"{self.base}/{method}", data=encoded, method="POST")
            with urllib.request.urlopen(req, timeout=45) as r:
                payload = json.loads(r.read().decode())
        except Exception as e:
            raise TelegramError(str(e)) from e
        if not payload.get("ok"):
            raise TelegramError(payload.get("description", "Telegram API error"))
        return payload.get("result")

    def get_updates(self, offset: int | None, timeout: int = 25):
        return self.call("getUpdates", offset=offset, timeout=timeout, allowed_updates=["message", "callback_query"])

    def send(self, chat_id, text, reply_markup=None, reply_to=None, parse_mode="HTML"):
        if parse_mode == "HTML":
            text = render_message_emojis(str(text))
            text = md_to_html(text)
        return self.call("sendMessage", chat_id=chat_id, text=text, reply_markup=reply_markup, reply_to_message_id=reply_to, parse_mode=parse_mode, disable_web_page_preview=True)

    def edit(self, chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
        if parse_mode == "HTML":
            text = render_message_emojis(str(text))
            text = md_to_html(text)
        return self.call("editMessageText", chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=True)

    def edit_caption(self, chat_id, message_id, caption, reply_markup=None, parse_mode="HTML"):
        if parse_mode == "HTML":
            caption = render_message_emojis(str(caption))
            caption = md_to_html(caption)
        return self.call("editMessageCaption", chat_id=chat_id, message_id=message_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)

    def answer_callback(self, cid, text="", alert=False):
        return self.call("answerCallbackQuery", callback_query_id=cid, text=text, show_alert=alert)

    def send_photo(self, chat_id, photo_path, caption="", reply_markup=None, reply_to=None, parse_mode="HTML"):
        path = Path(photo_path)
        if not path.is_file():
            return self.send(chat_id, caption, reply_markup, reply_to, parse_mode)
        if parse_mode == "HTML":
            caption = render_message_emojis(str(caption))
            caption = md_to_html(caption)
        boundary = uuid.uuid4().hex.encode()
        parts = []

        def field(name, value):
            parts.append(b"--" + boundary + b"\r\n")
            parts.append(f'Content-Disposition: form-data; name="{name}"'.encode())
            parts.append(b"\r\n\r\n")
            parts.append(str(value).encode())
            parts.append(b"\r\n")

        field("chat_id", chat_id)
        field("caption", caption)
        field("parse_mode", parse_mode)
        if reply_markup is not None:
            field("reply_markup", json.dumps(reply_markup, ensure_ascii=False))
        if reply_to is not None:
            field("reply_to_message_id", reply_to)
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        parts.append(b"--" + boundary + b"\r\n")
        parts.append(f'Content-Disposition: form-data; name="photo"; filename="{path.name}"'.encode())
        parts.append(f"\r\nContent-Type: {mime}\r\n\r\n".encode())
        parts.append(path.read_bytes())
        parts.append(b"\r\n--" + boundary + b"--\r\n")
        body = b"".join(parts)
        req = urllib.request.Request(
            f"{self.base}/sendPhoto",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                payload = json.loads(r.read().decode())
        except Exception as e:
            raise TelegramError(str(e)) from e
        if not payload.get("ok"):
            raise TelegramError(payload.get("description", "Telegram API error"))
        return payload.get("result")

    def get_chat_member(self, chat_id, user_id):
        return self.call("getChatMember", chat_id=chat_id, user_id=user_id)

    def get_chat(self, chat_id):
        return self.call("getChat", chat_id=chat_id)

    def set_my_commands(self, commands):
        return self.call("setMyCommands", commands=commands)

    def get_me(self):
        return self.call("getMe")
