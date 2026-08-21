"""Input repair E1–E5 (homophone groups from system.tm pin_group)."""

from __future__ import annotations

from functools import lru_cache

from para.system_tm import load_system


@lru_cache(maxsize=1)
def pin_char_map() -> dict[str, str]:
    """pin_group → single char to canonical; invalidated by clear_tm_caches."""
    out: dict[str, str] = {}
    for group in load_system().pin_groups:
        if not group:
            continue
        canon = group[0]
        for ch in group:
            if len(ch) == 1:
                out[ch] = canon
    return out


def clear_pin_map_cache() -> None:
    pin_char_map.cache_clear()


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


def _pin_key(text: str, pins: dict[str, str]) -> str:
    return "".join(pins.get(ch, ch) for ch in text)


def _e3_match(window: str, key: str, pins: dict[str, str]) -> bool:
    """Same length, same pin reading, edit distance 1."""
    return (
        len(window) == len(key)
        and _pin_key(window, pins) == _pin_key(key, pins)
        and _lev(window, key) == 1
    )


def _e4_match(window: str, key: str, pins: dict[str, str]) -> bool:
    """One extra char at edge: delete recovers key; extra twins first/last key char.

    Trailing twin: 机器器 / 积气气. Leading twin: 机机器.
    Must NOT treat 合同类型+合(法吗) as twin of 合 inside 合同.
    """
    if len(window) != len(key) + 1:
        return False
    key_pin = _pin_key(key, pins)
    for i in range(len(window)):
        extra = window[i]
        cand = window[:i] + window[i + 1 :]
        if not (cand == key or _pin_key(cand, pins) == key_pin):
            continue
        extra_pin = pins.get(extra, extra)
        if i == len(window) - 1:
            last = key[-1]
            if extra == last or extra_pin == pins.get(last, last):
                return True
        elif i == 0:
            first = key[0]
            if extra == first or extra_pin == pins.get(first, first):
                return True
    return False


def _protected_phrases() -> tuple[str, ...]:
    """Judge triggers (len>=2) + 合不合法 — never pin-rewrite / chunk-split inside."""
    phrases: set[str] = {"合不合法"}
    try:
        from para.judge import load_judge_rules

        for rule in load_judge_rules():
            for trig in rule.triggers:
                if len(trig) >= 2:
                    phrases.add(trig)
    except ImportError:
        phrases = {
            "合不合法",
            "不违法吗",
            "违法吗",
            "合法吗",
            "合规吗",
            "可以吗",
        }
    return tuple(sorted(phrases, key=len, reverse=True))


def repair(raw: str, vocab: set[str], known: set[str]) -> str:
    """E1 exact → E2 same reading (unique) → E3/E4 toward known only → E5 no insert.

    E3/E4 deliberately ignore closed lex (avoid mapping open names onto closed lex).
    """
    exact_keys = sorted({*vocab, *known}, key=len, reverse=True)
    pins = pin_char_map()
    protected = _protected_phrases()
    fuzzy_keys = sorted(
        {k for k in known if len(k) >= 2 and k not in {"me", "other", "here", "now"}},
        key=len,
        reverse=True,
    )
    if not exact_keys:
        return raw
    out: list[str] = []
    i = 0
    n = len(raw)
    while i < n:
        if raw[i].isspace():
            i += 1
            continue
        if raw[i] in "，。！、；：,.!;:?？":
            # Keep punctuation: 5/7-char verse splits / D66 body commas; still drop whitespace
            out.append(raw[i])
            i += 1
            continue
        # Protect judge triggers (e.g. 合不合法) before exact/chunk so pin cannot rewrite 合→和
        prot = ""
        for phrase in protected:
            if raw.startswith(phrase, i) and len(phrase) > len(prot):
                prot = phrase
        if prot:
            out.append(prot)
            i += len(prot)
            continue
        hit = ""
        for key in exact_keys:
            if raw.startswith(key, i) and len(key) > len(hit):
                hit = key
        if hit:
            # E4: 「机器器」— exact prefix + one redundant twin char
            clen = len(hit) + 1
            if (
                hit in fuzzy_keys
                and i + clen <= n
                and _e4_match(raw[i : i + clen], hit, pins)
            ):
                out.append(hit)
                i += clen
                continue
            out.append(hit)
            i += len(hit)
            continue
        j = i + 1
        while j < n and raw[j] not in "，。！、；：,.!;:?？":
            if any(raw.startswith(k, j) for k in exact_keys):
                break
            if any(raw.startswith(p, j) for p in protected):
                break
            j += 1
        chunk = raw[i:j]
        pin = _pin_key(chunk, pins)
        e2 = [
            k
            for k in known
            if len(k) == len(chunk) and _pin_key(k, pins) == pin and k != chunk
        ]
        if len(e2) == 1:
            out.append(e2[0])
            i = j
            continue
        # Before single-char pin rewrite: never rewrite inside a protected trigger
        pin_blocked = False
        for phrase in protected:
            if raw.startswith(phrase, i):
                out.append(phrase)
                i += len(phrase)
                pin_blocked = True
                break
        if pin_blocked:
            continue
        ch = raw[i]
        if len(chunk) == 1 and ch in pins and pins[ch] in exact_keys:
            out.append(pins[ch])
            i += 1
            continue
        best: list[tuple[str, int]] = []
        for key in fuzzy_keys:
            for clen in (len(key), len(key) + 1):
                if clen < 1 or i + clen > n:
                    continue
                window = raw[i : i + clen]
                if len(window) < len(key):
                    continue
                # E3: same-len pin typo; E4: one extra char, delete recovers pin-key
                if _e3_match(window, key, pins) or _e4_match(window, key, pins):
                    best.append((key, clen))
        uniq = {k for k, _ in best}
        if len(uniq) == 1:
            key = next(iter(uniq))
            clen = next(c for k, c in best if k == key)
            out.append(key)
            i += clen
            continue
        out.append(chunk)
        i = j
    return "".join(out)
