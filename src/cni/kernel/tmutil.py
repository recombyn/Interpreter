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
    """Split comma-separated args; double-quoted segments may contain commas."""
    parts: list[str] = []
    cur: list[str] = []
    i = 0
    in_quote = False
    while i < len(text):
        ch = text[i]
        if in_quote:
            if ch == "\\" and i + 1 < len(text):
                cur.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_quote = False
                i += 1
                continue
            cur.append(ch)
            i += 1
            continue
        if ch == '"':
            in_quote = True
            i += 1
            continue
        if ch == ",":
            part = "".join(cur).strip()
            if not part:
                raise ParseError("empty argument", filename, line)
            parts.append(part)
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    if in_quote:
        raise ParseError("unclosed quote in arguments", filename, line)
    part = "".join(cur).strip()
    if not part:
        raise ParseError("empty argument", filename, line)
    parts.append(part)
    return parts


def format_arg(value: str) -> str:
    """Quote arg when it contains comma/space/quote so save↔load roundtrips."""
    if any(c in value for c in ',()"') or value != value.strip():
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def closed_at(lines: list[str], start: int, filename: str, kind: str) -> int:
    depth = 1
    for index in range(start, len(lines)):
        raw = clean(lines[index])
        depth += raw.count("{") - raw.count("}")
        if depth == 0:
            return index + 1
    raise ParseError(f"unclosed {kind}", filename, start)
