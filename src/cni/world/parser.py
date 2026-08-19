from __future__ import annotations

import re

_COMMENT = re.compile(r"#.*$")


class WorldParseError(ValueError):
    def __init__(self, message: str, filename: str, line: int) -> None:
        super().__init__(f"{filename}:{line}: {message}")
        self.filename = filename
        self.line = line


def _clean(line: str) -> str:
    return _COMMENT.sub("", line).strip()


def _split_args(text: str, filename: str, line: int) -> list[str]:
    parts = [part.strip() for part in text.split(",")]
    if not parts or any(not part for part in parts):
        raise WorldParseError("malformed argument list", filename, line)
    return parts


def _closed_at(lines: list[str], start: int, filename: str, block: str) -> int:
    depth = 1
    for line_no, raw in enumerate(lines[start:], start=start + 1):
        line = _clean(raw)
        if not line:
            continue
        depth += line.count("{")
        depth -= line.count("}")
        if depth == 0:
            return line_no
    raise WorldParseError(f"unclosed {block} block", filename, start + 1)
