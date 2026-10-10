"""Privacy helpers: redact personal identifiers before anything leaves the app.

Only redacted text is ever sent to the optional LLM. Nothing is written to disk.
"""
from __future__ import annotations

import hashlib
import re

_RULES = [
    ("[EMAIL]", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("[UPI_ID]", re.compile(r"\b[\w.-]{2,}@[a-zA-Z]{2,}\b")),
    ("[CARD_NUMBER]", re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b")),
    ("[ID_NUMBER]", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    ("[PHONE]", re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")),
    ("[OTP]", re.compile(r"\b(?:otp|code|pin)\b[^\d\n]{0,12}\d{4,8}\b", re.IGNORECASE)),
]


def redact(text: str) -> str:
    if not text:
        return ""
    for token, rx in _RULES:
        text = rx.sub(token, text)
    return text


def pseudonym_map(names: list[str], me: str | None = None) -> dict[str, str]:
    """Map real participant names to neutral labels ('You', 'Person A', ...)."""
    mapping: dict[str, str] = {}
    letter = ord("A")
    for n in names:
        if me and n == me:
            mapping[n] = "You"
        else:
            mapping[n] = f"Person {chr(letter)}"
            letter = min(letter + 1, ord("Z"))
    return mapping


def replace_names(text: str, mapping: dict[str, str]) -> str:
    for real, alias in sorted(mapping.items(), key=lambda kv: -len(kv[0])):
        if real and real != "Unknown" and len(real) > 1:
            text = re.sub(re.escape(real), alias, text, flags=re.IGNORECASE)
    return text


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
