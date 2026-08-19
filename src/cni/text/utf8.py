from __future__ import annotations


def as_text(data: str | bytes) -> str:
    if isinstance(data, bytes):
        return data.decode("utf-8")
    return data


def as_utf8(text: str) -> bytes:
    return text.encode("utf-8")
