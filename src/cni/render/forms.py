"""Load form.tm outs (REN / polar surfaces).

World: src/cni/data/world/form.tm
User:  knowledge/user/form.tm (overrides)
Config reply_mode only remaps keys yes/no.

Polar: D supplies slots; form templates compose them
  polar.<stem>.yes|no  → specific
  polar.default.yes|no → general ({clause}{pred})
  polar.neg.* / polar.affix.neg / polar_trig.* / polar.mode
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from cni.kernel.tmutil import clean
from cni.paths import USER_DIR, WORLD_DIR
from cni.user_config import clear_user_config_cache, reply_mode as _cfg_reply_mode

_OUT = re.compile(r"^out\s+(\S+)\s+(.+)$")
_ABUA = re.compile(
    r"(?:可)?([\u4e00-\u9fff])不(?:可)?\1([\u4e00-\u9fff]*)\s*$"
)
_ABUA_SIMPLE = re.compile(r"([\u4e00-\u9fff]{1,2})不\1\s*$")
_MODE_BOOL = {"yes": "true", "no": "false"}
_MODE_ZH_BOOL = {"yes": "是", "no": "否"}
_STEM_STOP = set(
    "零〇一二两三四五六七八九十百千万亿月年天日个期行条顿岁届名台件次番"
    "的了呢啊吧呀嘛着过就都也还很非常"
)
_MOD_PREFIXES = ("严格", "是否", "真的", "到底", "究竟", "请", "请问")


def _parse_outs(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    forms: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = clean(raw)
        if m := _OUT.match(line):
            forms[m.group(1)] = m.group(2)
    return forms


@lru_cache(maxsize=8)
def _load_forms_cached(world: str, user: str, mode: str) -> dict[str, str]:
    forms = _parse_outs(Path(world))
    forms.update(_parse_outs(Path(user)))
    if mode == "bool":
        forms.update(_MODE_BOOL)
    elif mode == "zh_bool":
        forms.update(_MODE_ZH_BOOL)
    return forms


def load_forms(
    path: Path | None = None,
    *,
    user_path: Path | None = None,
    reply_mode: str | None = None,
    config_path: Path | None = None,
) -> dict[str, str]:
    world = str(path or (WORLD_DIR / "form.tm"))
    user = str(user_path or (USER_DIR / "form.tm"))
    mode = (
        reply_mode
        if reply_mode is not None
        else _cfg_reply_mode(str(config_path) if config_path else None)
    )
    return _load_forms_cached(world, user, mode)


def form(const: str) -> str | None:
    return load_forms().get(const)


def _is_han(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"


def _strip_mod_prefixes(stem: str) -> str:
    for pref in _MOD_PREFIXES:
        if stem.startswith(pref) and len(stem) > len(pref):
            stem = stem[len(pref) :]
    return stem


def _auto_stem_tail(body: str) -> str | None:
    body = (body or "").rstrip("，,。；;、 ")
    if not body:
        return None
    for n in (2, 3, 1, 4):
        if len(body) < n:
            continue
        cand = body[-n:]
        if all(_is_han(c) for c in cand) and not any(c in _STEM_STOP for c in cand):
            return cand
    i = len(body)
    while i > 0 and _is_han(body[i - 1]) and (len(body) - i) < 4:
        i -= 1
    return body[i:] or None


def stem_from_trigger(trigger: str) -> str | None:
    t = (trigger or "").strip().rstrip("？?")
    if not t:
        return None
    m = _ABUA.search(t)
    if m:
        return _strip_mod_prefixes(m.group(1) + m.group(2))
    m = _ABUA_SIMPLE.search(t)
    if m:
        return _strip_mod_prefixes(m.group(1))
    if t.endswith("吗"):
        return _strip_mod_prefixes(_auto_stem_tail(t[:-1]) or "")
    if 1 <= len(t) <= 4 and all(_is_han(c) for c in t):
        return _strip_mod_prefixes(t)
    return None


def resolve_polar_stem(
    question: str,
    forms: dict[str, str] | None = None,
    *,
    trigger: str = "",
) -> str | None:
    forms = forms if forms is not None else load_forms()
    raw = (question or "").strip().rstrip("？?")
    if trigger:
        got = stem_from_trigger(trigger)
        if got:
            return got
    binds = [
        (k[len("polar_trig.") :], v)
        for k, v in forms.items()
        if k.startswith("polar_trig.")
    ]
    for trig, stem in sorted(binds, key=lambda x: len(x[0]), reverse=True):
        if raw.endswith(trig):
            return stem
    m = _ABUA.search(raw) or _ABUA_SIMPLE.search(raw)
    if m:
        if m.lastindex and m.lastindex >= 2 and m.group(2) is not None:
            return _strip_mod_prefixes(m.group(1) + (m.group(2) or ""))
        return _strip_mod_prefixes(m.group(1))
    if raw.endswith("吗"):
        return _strip_mod_prefixes(_auto_stem_tail(raw[:-1]) or "") or None
    return None


def morph_polar(stem: str, ok: bool, forms: dict[str, str] | None = None) -> str:
    """Stem → pred using form affixes/neg only (no hardcoded 是的/不是)."""
    forms = forms if forms is not None else load_forms()
    stem = (stem or "").strip()
    if not stem:
        return forms.get("yes" if ok else "no") or ""
    if ok:
        return stem
    special = forms.get(f"polar.neg.{stem}")
    if special:
        return special
    if stem.startswith("不") or stem.startswith("没"):
        return stem
    return f"{forms.get('polar.affix.neg') or '不'}{stem}"


def _clause_of_ask(question: str, *, trigger: str = "", stem: str = "") -> str:
    raw = (question or "").strip().rstrip("？?")
    if not raw:
        return ""
    if trigger and raw.endswith(trigger):
        return raw[: -len(trigger)].strip("，,。；;、 ")
    if stem and raw.endswith(stem + "吗"):
        return raw[: -(len(stem) + 1)].strip("，,。；;、 ")
    if raw.endswith("吗"):
        body = raw[:-1]
        if stem and body.endswith(stem):
            return body[: -len(stem)].strip("，,。；;、 ")
        return body.strip("，,。；;、 ")
    m = _ABUA.search(raw) or _ABUA_SIMPLE.search(raw)
    if m:
        return raw[: m.start()].strip("，,。；;、 ")
    return ""


def fill_slots(tpl: str, slots: dict[str, str]) -> str:
    out = tpl or ""
    for key, val in slots.items():
        out = out.replace("{" + key + "}", val or "")
    if "stem" in slots:
        out = out.replace("{0}", slots.get("stem") or "")
    return out


def polar_slots(
    question: str,
    ok: bool,
    *,
    trigger: str = "",
    topic: str = "",
    forms: dict[str, str] | None = None,
) -> dict[str, str]:
    forms = forms if forms is not None else load_forms()
    stem = resolve_polar_stem(question, forms, trigger=trigger) or ""
    clause = _clause_of_ask(question, trigger=trigger, stem=stem)
    pred = morph_polar(stem, ok, forms) if stem else (forms.get("yes" if ok else "no") or "")
    return {
        "clause": clause,
        "stem": stem,
        "pred": pred,
        "topic": topic or "",
        "trigger": trigger or "",
        "yes": forms.get("yes") or "",
        "no": forms.get("no") or "",
        "ok": "1" if ok else "0",
    }


def polar_spoken(
    question: str,
    ok: bool,
    *,
    trigger: str = "",
    topic: str = "",
) -> str:
    """Compose reply from form templates + D slots."""
    forms = load_forms()
    side = "yes" if ok else "no"
    slots = polar_slots(question, ok, trigger=trigger, topic=topic, forms=forms)
    stem, pred, clause = slots["stem"], slots["pred"], slots["clause"]

    specific = forms.get(f"polar.{stem}.{side}") if stem else None
    if specific:
        if "{" in specific:
            return fill_slots(specific, slots)
        slots = {**slots, "pred": specific}
        pred = specific

    mode = forms.get("polar.mode", "clause").casefold()
    if mode == "short" or not clause:
        return pred

    default_tpl = forms.get(f"polar.default.{side}")
    if default_tpl:
        return fill_slots(default_tpl, {**slots, "pred": pred})

    if ok and stem and clause.endswith(stem):
        return clause
    if (not ok) and stem and clause.endswith(stem):
        return clause[: -len(stem)] + pred
    return f"{clause}{pred}" if clause else pred


def clear_forms_cache() -> None:
    clear_user_config_cache()
    _load_forms_cached.cache_clear()
