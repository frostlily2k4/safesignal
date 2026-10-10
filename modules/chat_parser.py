"""Parse WhatsApp chat exports (Android and iPhone) or plain pasted chats.

Supported line shapes:
  Android : 12/03/24, 9:15 pm - Ravi: hello
  iPhone  : [12/03/24, 9:15:32 PM] Ravi: hello
  Plain   : Ravi: hello      (or just lines of text with no sender)
Lines that do not start a new message are treated as continuations.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from config import MAX_MESSAGES

_TIME = r"(\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?:\s?[apAP]\.?\s?[mM]\.?)?)"
_DATE = r"(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})"
ANDROID_RE = re.compile(rf"^{_DATE},?\s+{_TIME}\s+[-–]\s+(.*)$")
IOS_RE = re.compile(rf"^\[{_DATE},?\s+{_TIME}\]\s+(.*)$")
PLAIN_SENDER_RE = re.compile(r"^([^:\n]{1,40}?):\s+(.+)$")

SKIP_TEXTS = {
    "<media omitted>",
    "image omitted",
    "video omitted",
    "audio omitted",
    "sticker omitted",
    "gif omitted",
    "document omitted",
    "this message was deleted",
    "you deleted this message",
    "null",
}


@dataclass
class ChatMessage:
    timestamp: datetime | None
    sender: str
    text: str


def _normalise(raw: str) -> str:
    for ch in ("\u200e", "\u200f", "\ufeff"):
        raw = raw.replace(ch, "")
    return raw.replace("\u202f", " ").replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")


def _parse_datetime(date_s: str, time_s: str) -> datetime | None:
    date_s = re.sub(r"[.-]", "/", date_s)
    time_s = time_s.replace(".", ":").upper().replace("A:M:", "AM").replace("P:M:", "PM")
    time_s = re.sub(r"\s+", " ", time_s.replace("A.M.", "AM").replace("P.M.", "PM")).strip()
    time_s = re.sub(r"(\d)(AM|PM)$", r"\1 \2", time_s)
    date_fmts = ["%d/%m/%y", "%d/%m/%Y", "%m/%d/%y", "%m/%d/%Y"]  # day-first (India) tried first
    time_fmts = ["%I:%M %p", "%I:%M:%S %p", "%H:%M", "%H:%M:%S"]
    for df in date_fmts:
        for tf in time_fmts:
            try:
                return datetime.strptime(f"{date_s} {time_s}", f"{df} {tf}")
            except ValueError:
                continue
    return None


def _split_sender(rest: str):
    """'Ravi: hi' -> ('Ravi', 'hi'); system lines without a sender -> None."""
    if ": " not in rest:
        return None
    sender, text = rest.split(": ", 1)
    sender = sender.strip()
    if not sender or len(sender) > 60:
        return None
    return sender, text


def _keep(text: str) -> bool:
    t = text.strip()
    return bool(t) and t.lower() not in SKIP_TEXTS


def detect_format(raw: str) -> str:
    lines = [ln for ln in _normalise(raw).split("\n") if ln.strip()][:50]
    hits = sum(1 for ln in lines if ANDROID_RE.match(ln) or IOS_RE.match(ln))
    return "whatsapp" if lines and hits >= max(1, len(lines) // 4) else "plain"


def parse_chat(raw: str, max_messages: int = MAX_MESSAGES) -> list[ChatMessage]:
    if not raw or not raw.strip():
        return []
    raw = _normalise(raw)
    fmt = detect_format(raw)
    messages: list[ChatMessage] = []
    current: ChatMessage | None = None
    in_system_line = False

    def flush():
        nonlocal current
        if current is not None and _keep(current.text):
            current.text = current.text.strip()
            messages.append(current)
        current = None

    for line in raw.split("\n"):
        if fmt == "whatsapp":
            m = ANDROID_RE.match(line) or IOS_RE.match(line)
            if m:
                flush()
                date_s, time_s, rest = m.groups()
                split = _split_sender(rest)
                if split is None:  # e.g. "Messages are end-to-end encrypted"
                    in_system_line = True
                    continue
                in_system_line = False
                current = ChatMessage(_parse_datetime(date_s, time_s), split[0], split[1])
            elif current is not None and not in_system_line and line.strip():
                current.text += "\n" + line
        else:
            if not line.strip():
                continue
            m = PLAIN_SENDER_RE.match(line.strip())
            if m:
                flush()
                current = ChatMessage(None, m.group(1).strip(), m.group(2))
            elif current is not None and current.sender != "Unknown":
                current.text += "\n" + line.strip()
            else:
                flush()
                current = ChatMessage(None, "Unknown", line.strip())
        if len(messages) >= max_messages:
            break
    flush()
    return messages[:max_messages]


def senders(messages: list[ChatMessage]) -> list[str]:
    seen: dict[str, int] = {}
    for m in messages:
        seen[m.sender] = seen.get(m.sender, 0) + 1
    return sorted(seen, key=lambda s: -seen[s])
