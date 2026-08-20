"""Shared .tm line helpers."""

from __future__ import annotations


class ParseError(ValueError):
    def __init__(self, message: str, filename: str = "<tm>", line: int = 1) -> None:
        super().__init__(f"{filename}:{line}: {message}")
        self.filename = filename
        self.line = line


def clean(line: str) -> str:
    if "#" in line:
        line = line[: line.index("#")]
    return line.strip()


def split_args(text: str, filename: str = "<tm>", line: int = 1) -> list[str]:
    parts = [p.strip() for p in text.split(",")]
    if any(not p for p in parts):
        raise ParseError("empty argument", filename, line)
    return parts


def closed_at(lines: list[str], start: int, filename: str, kind: str) -> int:
    depth = 1
    for index in range(start, len(lines)):
        raw = clean(lines[index])
        depth += raw.count("{") - raw.count("}")
        if depth == 0:
            return index + 1
    raise ParseError(f"unclosed {kind}", filename, start)
