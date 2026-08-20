"""Input repair E1–E5（表1写死；同音组在代码里，不另开 .tm）。"""

from __future__ import annotations

# E2 同音组：组内字 → 规范字（算法数据，非用户词典）
_PIN_GROUPS: tuple[tuple[str, ...], ...] = (
    ("机", "积", "基"),
    ("器", "气", "期"),
    ("是", "时", "事", "市", "试"),
    ("有", "又", "友"),
    ("在", "再"),
    ("的", "地", "得"),
    ("和", "合"),
    ("比", "笔"),
    ("吗", "嘛"),
    ("没", "每"),
    ("不", "部"),
)


def _pins() -> dict[str, str]:
    out: dict[str, str] = {}
    for group in _PIN_GROUPS:
        canon = group[0]
        for ch in group:
            if len(ch) == 1:
                out[ch] = canon
    return out


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


def repair(raw: str, vocab: set[str], known: set[str]) -> str:
    """E1 exact → E2 same reading (unique) → E3/E4 toward known only → E5 no insert.

    E3/E4 deliberately ignore closed lex (避免「苹果」→「如果」).
    """
    exact_keys = sorted({*vocab, *known}, key=len, reverse=True)
    pins = _pins()
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
            # 保留标点：五七言分句 / D66 正文逗号；空白仍丢弃
            out.append(raw[i])
            i += 1
            continue
        hit = ""
        for key in exact_keys:
            if raw.startswith(key, i) and len(key) > len(hit):
                hit = key
        if hit:
            out.append(hit)
            i += len(hit)
            continue
        j = i + 1
        while j < n and raw[j] not in "，。！、；：,.!;:?？":
            if any(raw.startswith(k, j) for k in exact_keys):
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
                # E3/E4：仅同音组内的错别字/多字，避免「小红」被改成「小明」
                if _pin_key(window, pins) != _pin_key(key, pins):
                    continue
                if _lev(window, key) == 1:
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
