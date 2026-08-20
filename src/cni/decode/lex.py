"""Lexicon load + tokenize. Surface forms only in .tm files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from cni.kernel.tmutil import clean
from cni.paths import WORLD_DIR

_HEADER = re.compile(r"^lex\s+(\S+)\s*\{\s*$")
_IN = re.compile(r"^in\s+(\S+)\s+(\S+)\s*$")
_OUT = re.compile(r"^out\s+(\S+)\s+(.+)$")
_SKIP = set(" \t\r\n，。！、；：,.!;:?？()（）")


@dataclass
class Sense:
    name: str
    surface: str = ""
    open: bool = False


@dataclass
class Lex:
    name: str
    to_sense: dict[str, str] = field(default_factory=dict)
    to_form: dict[str, str] = field(default_factory=dict)

    @property
    def vocab(self) -> set[str]:
        return set(self.to_sense)


@lru_cache(maxsize=4)
def load_lex(path: Path) -> Lex:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    name = "lex"
    to_sense: dict[str, str] = {}
    to_form: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = clean(lines[i])
        if not line:
            i += 1
            continue
        if head := _HEADER.match(line):
            name = head.group(1)
            i += 1
            while i < len(lines):
                inner = clean(lines[i])
                i += 1
                if inner == "}":
                    break
                if not inner:
                    continue
                if m := _IN.match(inner):
                    to_sense[m.group(1)] = m.group(2)
                elif m := _OUT.match(inner):
                    to_form[m.group(1)] = m.group(2)
            continue
        i += 1
    return Lex(name=name, to_sense=to_sense, to_form=to_form)


def lex_ch() -> Lex:
    return load_lex(WORLD_DIR / "lex.ch.tm")


def lex_en() -> Lex:
    return load_lex(WORLD_DIR / "lex.en.tm")


def pick_lex(text: str) -> Lex:
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return lex_ch()
    return lex_en()


def tokenize(text: str, lex: Lex) -> list[Sense]:
    keys = sorted(lex.to_sense, key=len, reverse=True)
    senses: list[Sense] = []
    i = 0
    n = len(text)
    iso = re.compile(r"\d{4}-\d{2}-\d{2}")
    while i < n:
        if text[i] in _SKIP:
            i += 1
            continue
        # G 注入的绝对日期单独成块，避免与前后汉字粘连
        m = iso.match(text, i)
        if m:
            chunk = m.group(0)
            senses.append(Sense(chunk, surface=chunk, open=True))
            i = m.end()
            continue
        hit = ""
        for key in keys:
            if text.startswith(key, i):
                hit = key
                break
        if hit:
            sense = lex.to_sense[hit]
            # 单字形容词后接汉字：优先并入开名（「小明」≠「小」+「明」）
            end = i + len(hit)
            if (
                len(hit) == 1
                and sense.startswith("adj_")
                and end < n
                and "\u4e00" <= text[end] <= "\u9fff"
                and text[end] not in _SKIP
                and not any(text.startswith(k, end) for k in keys)
            ):
                hit = ""
            else:
                senses.append(Sense(sense, surface=hit))
                i = end
                continue
        if hit:
            continue
        # open chunk: consecutive non-lex chars；汉字与 ASCII/数字边界切开
        j = i + 1
        while j < n and text[j] not in _SKIP:
            if iso.match(text, j):
                break
            if any(text.startswith(k, j) for k in keys):
                break
            if _script_break(text[j - 1], text[j]):
                break
            j += 1
        chunk = text[i:j]
        senses.append(Sense(chunk, surface=chunk, open=True))
        i = j
    return senses


def _script_break(a: str, b: str) -> bool:
    """汉字 ↔ 拉丁/数字 之间切开。"""
    def kind(ch: str) -> str:
        if "\u4e00" <= ch <= "\u9fff":
            return "cjk"
        if ch.isdigit() or ch in "-":
            return "num"
        if ch.isascii() and ch.isalpha():
            return "lat"
        return "other"

    return kind(a) != kind(b) and "other" not in {kind(a), kind(b)}


def form_of(const: str, lex: Lex | None = None) -> str | None:
    lex = lex or lex_ch()
    return lex.to_form.get(const)
