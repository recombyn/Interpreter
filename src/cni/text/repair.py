"""Pre-decode repair: typos, extra/missing chars, closed-class homophones.

Maps toward lex forms and already-known world names. Decode stays exact.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from cni.paths import WORLD_DIR
from cni.world.parser import _clean

PIN_PATH = WORLD_DIR / "ch.pin.tm"


def _lev(left: str, right: str) -> int:
    if left == right:
        return 0
    if abs(len(left) - len(right)) > 1:
        return 2
    if len(left) == len(right):
        return 1 if sum(a != b for a, b in zip(left, right)) == 1 else 2
    if len(left) > len(right):
        left, right = right, left
    i = 0
    while i < len(left) and left[i] == right[i]:
        i += 1
    return 0 if left[i:] == right[i + 1 :] else 2


@lru_cache(maxsize=1)
def load_pins(path: Path | None = None) -> dict[str, str]:
    path = path or PIN_PATH
    if not path.is_file():
        return {}
    pins: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = _clean(raw)
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3 or parts[0] != "group":
            continue
        canon = parts[2]
        for char in parts[2:]:
            if len(char) == 1:
                pins[char] = canon
    return pins


def _longest_exact(raw: str, index: int, keys: list[str]) -> str | None:
    hit = ""
    for key in keys:
        if raw.startswith(key, index) and len(key) > len(hit):
            hit = key
    return hit or None


def _best_fuzzy(
    raw: str, index: int, keys: list[str], min_len: int
) -> tuple[str, int] | None:
    best: tuple[int, int, int, str] | None = None
    n = len(raw)
    for key in keys:
        if len(key) < min_len:
            continue
        for clen in (len(key) - 1, len(key), len(key) + 1):
            if clen < min_len - 1 or clen < 1 or index + clen > n:
                continue
            window = raw[index : index + clen]
            dist = _lev(window, key)
            if dist != 1:
                continue
            rec = (dist, -len(key), clen, key)
            if best is None or rec < best:
                best = rec
    if best is None:
        return None
    return best[3], best[2]


def _greedy(raw: str, keys: list[str], min_fuzzy: int) -> str:
    ordered = sorted(set(keys), key=len, reverse=True)
    out: list[str] = []
    i = 0
    while i < len(raw):
        exact = _longest_exact(raw, i, ordered)
        if exact:
            out.append(exact)
            i += len(exact)
            continue
        fuzzy = _best_fuzzy(raw, i, ordered, min_fuzzy)
        if fuzzy:
            canon, consumed = fuzzy
            out.append(canon)
            i += consumed
            continue
        out.append(raw[i])
        i += 1
    return "".join(out)


def _pin_gap(raw: str, pins: dict[str, str], lex1: set[str]) -> str:
    n = len(raw)
    for i in range(2, n - 1):
        if n - i - 1 < 2:
            break
        mid = raw[i]
        if mid in lex1:
            continue
        canon = pins.get(mid)
        if not canon or canon not in lex1:
            continue
        left, right = raw[:i], raw[i + 1 :]
        if len(left) >= 2 and len(right) >= 2:
            return left + canon + right
    return raw


def _drop_extra(raw: str, keys: list[str], lex1: set[str]) -> str:
    ordered = sorted(set(keys), key=len, reverse=True)
    out: list[str] = []
    i = 0
    n = len(raw)
    while i < n:
        exact = _longest_exact(raw, i, ordered)
        if exact:
            if (
                out
                and len(out[-1]) == 1
                and out[-1] not in lex1
                and len(exact) >= 2
                and exact.startswith(out[-1])
            ):
                out.pop()
            out.append(exact)
            i += len(exact)
            continue
        out.append(raw[i])
        i += 1
    return "".join(out)


def repair_text(
    text: str,
    *,
    closed: list[str],
    known: list[str],
    pins: dict[str, str],
    spaced: bool,
) -> str:
    if spaced:
        keys = [k for k in closed + known if len(k) >= 3]
        folded = {k.casefold(): k for k in keys}
        bits: list[str] = []
        for word in text.split():
            hit = folded.get(word.casefold())
            if hit:
                bits.append(hit)
                continue
            best = None
            for key in keys:
                dist = _lev(word.casefold(), key.casefold())
                rec = (dist, -len(key), key)
                if dist == 1 and (best is None or rec < best):
                    best = rec
            bits.append(best[2] if best else word)
        return " ".join(bits)

    keys = list(closed) + list(known)
    lex1 = {form for form in closed if len(form) == 1}
    raw = text
    prev = ""
    for _ in range(3):
        if raw == prev:
            break
        prev = raw
        raw = _greedy(raw, closed, min_fuzzy=8)
        if known:
            raw = _greedy(raw, known, min_fuzzy=2)
        raw = _pin_gap(raw, pins, lex1)
        raw = _drop_extra(raw, keys, lex1)
    return raw
