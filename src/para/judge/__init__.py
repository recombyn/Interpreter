"""D69 judgment: threshold / enum / tiers / conjunction + missing-slot ask.

Table-1 algorithms; topics and facts live under knowledge/user/.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re

from para.kernel.machine import MachineWorld
from para.kernel.tmutil import clean
from para.paths import USER_DIR, get_user_dir

# Legacy single-file path kept for tools that pass an explicit path.
_RULES = USER_DIR / "rules.tm"

_CN_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}

_DURATION = re.compile(
    r"^\s*(?P<num>\d+|[一二两三四五六七八九十零〇]+)\s*"
    r"(?P<unit>个?月|个月|月|天|日|年)?\s*$"
)
# 半个月 / 一个半月 / 两周
_HALF_DUR = re.compile(
    r"^\s*(?:(?P<pre>\d+|[一二两三四五六七八九十])\s*个?)?半\s*"
    r"(?P<unit>个?月|个月|月|天|日|年)\s*$"
)
_WEEK_DUR = re.compile(
    r"^\s*(?P<num>\d+|[一二两三四五六七八九十零〇]+)\s*周\s*$"
)

_OPS = {
    "le": lambda a, b: a <= b,
    "ge": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
    "lt": lambda a, b: a < b,
    "gt": lambda a, b: a > b,
}

# Leading explain cues (stripped before match; sets JudgeHit.explain)
_COND_CUE = re.compile(r"^(?:什么情况下|何种情况|什么条件|在什么情况)")
# Asking "is it illegal?" → polar stem 违法 (forms: polar.违法.yes=不违法)
_NEG_TRIG = frozenset({"违法吗", "违法"})
# Positive compliance asks (same polarity as 合法吗)
_POS_LEGAL_TRIG = frozenset({"不违法吗", "不违法", "合法吗", "合法", "合不合法"})


def strip_cond_cue(text: str) -> tuple[str, bool]:
    """Strip leading 什么情况下… ; return (rest, explain)."""
    raw = (text or "").strip().rstrip("？?")
    m = _COND_CUE.match(raw)
    if m is None:
        return raw, False
    return raw[m.end() :].lstrip("的下，, "), True


@dataclass(frozen=True)
class JudgeRule:
    topic: str
    op: str  # le|ge|eq|lt|gt|in
    key: str  # 上限|下限|许可
    triggers: tuple[str, ...]
    also: tuple[str, ...] = ()


@dataclass(frozen=True)
class Duration:
    value: float  # 允许 0.5（半个月）等
    unit: str  # 月 / 天 / 年 / ""


@dataclass(frozen=True)
class Tier:
    """Contract length band → limit value (same unit as topic 单位)."""

    topic: str
    lo_months: int  # inclusive
    hi_months: int  # exclusive; 0 = +inf
    limit: int


@dataclass(frozen=True)
class JudgeHit:
    rule: JudgeRule
    duration: Duration | None = None
    contract: Duration | None = None
    enum_value: str = ""
    need_value: bool = False
    trigger: str = ""
    explain: bool = False  # 什么情况下…
    invert_polar: bool = False  # trigger is 违法吗 style


@dataclass(frozen=True)
class JudgeOutcome:
    """kind: answer | ask | miss | explain — miss → REN2."""

    kind: str
    topic: str
    ok: bool = False
    detail: str = ""
    ask: str = ""
    source: str = ""
    trigger: str = ""
    conditions: str = ""  # human-readable tier bands
    invert_polar: bool = False


def clear_judge_cache() -> None:
    _load_all_judge.cache_clear()
    load_judge_rules.cache_clear()
    load_tiers.cache_clear()
    judge_topics.cache_clear()


def _parse_rules_file(path: Path) -> tuple[list[JudgeRule], list[Tier]]:
    rules: list[JudgeRule] = []
    tiers: list[Tier] = []
    if not path.is_file():
        return rules, tiers
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = clean(raw)
        if line.startswith("tier "):
            # tier 试用期 3 12 1
            parts = line.split()
            if len(parts) >= 5:
                try:
                    tiers.append(
                        Tier(
                            topic=parts[1],
                            lo_months=int(parts[2]),
                            hi_months=int(parts[3]),
                            limit=int(parts[4]),
                        )
                    )
                except ValueError:
                    pass
            continue
        if not line.startswith("rule "):
            continue
        parts = line.split(maxsplit=4)
        if len(parts) < 5:
            continue
        _, topic, op, key_part, triggers = parts
        op_n = op.casefold()
        if op_n not in _OPS and op_n != "in":
            continue
        key_bits = [k.strip() for k in key_part.split("&") if k.strip()]
        if not key_bits:
            continue
        key, also = key_bits[0], tuple(key_bits[1:])
        if op_n == "in":
            if key not in {"许可", "允许"}:
                continue
            key = "许可"
        elif key not in {"上限", "下限"}:
            continue
        trigs = tuple(t.strip() for t in triggers.split("|") if t.strip())
        if not trigs:
            continue
        rules.append(
            JudgeRule(topic=topic, op=op_n, key=key, triggers=trigs, also=also)
        )
    return rules, tiers


def _iter_rules_paths(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("rules.tm") if p.is_file())


@lru_cache(maxsize=8)
def _load_all_judge(
    path: str | None = None,
    root: str | None = None,
) -> tuple[tuple[JudgeRule, ...], tuple[Tier, ...]]:
    """Merge knowledge/user/**/rules.tm (or a single explicit path)."""
    rules: list[JudgeRule] = []
    tiers: list[Tier] = []
    seen_r: set[tuple] = set()
    seen_t: set[tuple] = set()
    if path:
        paths = [Path(path)]
    else:
        paths = _iter_rules_paths(Path(root) if root else get_user_dir())
    for p in paths:
        rs, ts = _parse_rules_file(p)
        for r in rs:
            key = (r.topic, r.op, r.key, r.triggers, r.also)
            if key in seen_r:
                continue
            seen_r.add(key)
            rules.append(r)
        for t in ts:
            key = (t.topic, t.lo_months, t.hi_months, t.limit)
            if key in seen_t:
                continue
            seen_t.add(key)
            tiers.append(t)
    rules.sort(key=lambda r: len(r.topic), reverse=True)
    return tuple(rules), tuple(tiers)


@lru_cache(maxsize=8)
def load_judge_rules(path: str | None = None) -> tuple[JudgeRule, ...]:
    return _load_all_judge(path, str(get_user_dir()))[0]


@lru_cache(maxsize=4)
def load_tiers(path: str | None = None) -> tuple[Tier, ...]:
    return _load_all_judge(path, str(get_user_dir()))[1]


@lru_cache(maxsize=4)
def judge_topics(path: str | None = None) -> frozenset[str]:
    return frozenset(r.topic for r in load_judge_rules(path))


def parse_cn_int(text: str) -> int | None:
    t = (text or "").strip()
    if not t:
        return None
    if t.isdigit():
        return int(t)
    if t in _CN_DIGITS:
        return _CN_DIGITS[t]
    if t == "十":
        return 10
    if t.startswith("十") and len(t) == 2:
        ones = _CN_DIGITS.get(t[1])
        return 10 + ones if ones is not None else None
    if len(t) == 2 and t[1] == "十":
        tens = _CN_DIGITS.get(t[0])
        return tens * 10 if tens is not None else None
    if len(t) == 3 and t[1] == "十":
        tens = _CN_DIGITS.get(t[0])
        ones = _CN_DIGITS.get(t[2])
        if tens is not None and ones is not None:
            return tens * 10 + ones
    return None


def norm_duration_unit(unit_raw: str) -> str:
    """Normalize 个月/天/日/年 → 月/天/年 (empty if unknown)."""
    u = (unit_raw or "").strip()
    if "月" in u:
        return "月"
    if u in {"天", "日"}:
        return "天"
    if "年" in u:
        return "年"
    return ""


def parse_duration(text: str) -> Duration | None:
    raw = (text or "").strip()
    if not raw:
        return None
    hm = _HALF_DUR.match(raw)
    if hm is not None:
        pre = hm.group("pre")
        base = float(parse_cn_int(pre) or 0) if pre else 0.0
        return Duration(value=base + 0.5, unit=norm_duration_unit(hm.group("unit")))
    wm = _WEEK_DUR.match(raw)
    if wm is not None:
        weeks = parse_cn_int(wm.group("num"))
        if weeks is None:
            return None
        # 周 → 月（约 4 周/月），保留小数供 le 比较
        return Duration(value=weeks / 4.0, unit="月")
    m = _DURATION.match(raw)
    if m is None:
        return None
    val = parse_cn_int(m.group("num"))
    if val is None:
        return None
    return Duration(value=float(val), unit=norm_duration_unit(m.group("unit") or ""))


def duration_to_months(dur: Duration) -> int | None:
    """合同档用整月；不足一月按向上取整（有试用即占档）。"""
    import math

    if dur.unit == "月" or not dur.unit:
        if dur.value <= 0:
            return 0
        return int(math.ceil(dur.value - 1e-9))
    if dur.unit == "年":
        return int(math.ceil(dur.value * 12 - 1e-9))
    if dur.unit == "天":
        if dur.value <= 0:
            return 0
        return max(1, int(math.ceil(dur.value / 30.0 - 1e-9)))
    return None


def of_value(machine: MachineWorld, role: str, entity: str) -> str | None:
    vals = of_values(machine, role, entity)
    return vals[0] if vals else None


def of_values(machine: MachineWorld, role: str, entity: str) -> list[str]:
    out: list[str] = []
    for atom in machine.facts:
        if (
            atom.pred == "of"
            and len(atom.args) == 3
            and atom.args[0] == role
            and atom.args[1] == entity
        ):
            if atom.args[2] not in out:
                out.append(atom.args[2])
    return out


def _truthy(val: str | None) -> bool:
    if not val:
        return False
    return val not in {"否", "不", "无", "false", "False", "0", "空"}


def _check_also(
    machine: MachineWorld,
    rule: JudgeRule,
    *,
    waived: frozenset[str] | set[str] | None = None,
) -> str | None:
    waived = waived or set()
    for key in rule.also:
        if key in waived:
            continue
        if not _truthy(of_value(machine, key, rule.topic)):
            return key
    return None


def split_probation_contract(mid: str) -> tuple[Duration | None, Duration | None]:
    """Parse mid into (probation, contract?)."""
    mid = (mid or "").strip().strip("，,")
    if not mid:
        return None, None
    if "合同" in mid:
        left, right = mid.split("合同", 1)
        right = re.sub(r"^期限", "", right).strip("，, ")
        return parse_duration(left.strip("，, ")), parse_duration(right)
    d = parse_duration(mid)
    return d, None


def pick_tier_limit(topic: str, contract_months: int, tiers: tuple[Tier, ...] | None = None) -> int | None:
    tiers = tiers if tiers is not None else load_tiers()
    for t in tiers:
        if t.topic != topic:
            continue
        hi_ok = t.hi_months == 0 or contract_months < t.hi_months
        if t.lo_months <= contract_months and hi_ok:
            return t.limit
    return None


def _cn_month(n: int) -> str:
    m = {1: "一个月", 2: "二个月", 3: "三个月", 6: "六个月"}
    return m.get(n, f"{n}个月")


def format_tier_bands(
    topic: str, tiers: tuple[Tier, ...], unit: str = "月"
) -> str:
    """e.g. 合同期限三个月以上不满一年的，试用期不得超过一个月；…"""
    del unit  # reserved; labor tiers use 月 wording
    parts: list[str] = []
    for t in sorted(tiers, key=lambda x: x.lo_months):
        if t.topic != topic:
            continue
        if t.hi_months == 0:
            if t.lo_months >= 36:
                band = "劳动合同期限三年以上固定期限和无固定期限"
            else:
                band = f"合同期限{t.lo_months}个月以上"
        elif t.lo_months == 0:
            if t.hi_months == 3:
                band = "劳动合同期限不满三个月"
            else:
                band = f"劳动合同期限不满{_cn_month(t.hi_months)}"
        else:
            lo, hi = t.lo_months, t.hi_months
            if lo == 3 and hi == 12:
                band = "劳动合同期限三个月以上不满一年"
            elif lo == 12 and hi == 36:
                band = "劳动合同期限一年以上不满三年"
            else:
                band = f"劳动合同期限{lo}个月以上不满{hi}个月"
        if t.limit <= 0:
            parts.append(f"{band}的，不得约定{topic}")
        else:
            parts.append(f"{band}的，{topic}不得超过{_cn_month(t.limit)}")
    return "；".join(parts)


def _hit_flags(trig: str, *, explain: bool) -> dict:
    return {
        "trigger": trig,
        "explain": explain,
        "invert_polar": trig in _NEG_TRIG,
    }


def match_judge(
    text: str, rules: tuple[JudgeRule, ...] | None = None
) -> JudgeHit | None:
    raw = (text or "").strip().rstrip("？?")
    if not raw:
        return None
    rules = rules if rules is not None else load_judge_rules()

    explain = False
    raw, explain = strip_cond_cue(raw)
    if not raw:
        return None

    # Pattern B: 合同(期限)?{dur}…{topic}{dur}{trig}
    for rule in rules:
        if rule.op == "in":
            continue
        for trig in sorted(rule.triggers, key=len, reverse=True):
            if not raw.endswith(trig):
                continue
            body = raw[: -len(trig)]
            m = re.match(
                rf"^合同(?:期限)?(.+?){re.escape(rule.topic)}(.+)$",
                body,
            )
            if not m:
                continue
            contract_raw = m.group(1).strip("，, ")
            contract = parse_duration(contract_raw)
            # Non-empty mid between 合同 and topic must be a real duration;
            # otherwise junk like「试用期…另外」would still yield a Pattern B hit.
            if contract_raw and contract is None:
                continue
            probation = parse_duration(m.group(2).strip("，, "))
            if probation is None:
                continue
            return JudgeHit(
                rule=rule,
                duration=probation,
                contract=contract,
                **_hit_flags(trig, explain=explain),
            )

    for rule in rules:
        for trig in sorted(rule.triggers, key=len, reverse=True):
            if not raw.endswith(trig):
                continue
            body = raw[: -len(trig)]
            if not body.startswith(rule.topic):
                continue
            mid = body[len(rule.topic) :].strip()
            flags = _hit_flags(trig, explain=explain)
            if not mid:
                return JudgeHit(rule=rule, need_value=True, **flags)
            if rule.op == "in":
                return JudgeHit(rule=rule, enum_value=mid, **flags)
            probation, contract = split_probation_contract(mid)
            if probation is None:
                continue
            return JudgeHit(
                rule=rule,
                duration=probation,
                contract=contract,
                **flags,
            )
    return None


def find_judge_spans(
    text: str, rules: tuple[JudgeRule, ...] | None = None
) -> list[tuple[int, int, str]]:
    """Locate judge clauses inside a longer utterance (multi-fire, not punct-split).

    Returns (start, end, fragment) sorted by start. Overlaps dropped (keep earlier).
    """
    raw = text or ""
    if not raw.strip():
        return []
    rules = rules if rules is not None else load_judge_rules()
    cands: list[tuple[int, int, str]] = []

    for rule in rules:
        for trig in sorted(rule.triggers, key=len, reverse=True):
            start = 0
            while True:
                i = raw.find(trig, start)
                if i < 0:
                    break
                end = i + len(trig)
                # Prefer topic-local span; fall back to 「合同…主题…触发」
                left = raw[:i]
                frag: str | None = None
                frag_start = -1
                # Prefer 「合同…主题…触发」so tier contract length is kept
                if rule.op != "in":
                    cidx = left.rfind("合同")
                    tidx_b = left.rfind(rule.topic)
                    if (
                        cidx >= 0
                        and tidx_b > cidx
                        and match_judge(raw[cidx:end].rstrip("？?")) is not None
                    ):
                        frag_start, frag = cidx, raw[cidx:end]
                if frag is None:
                    tidx = left.rfind(rule.topic)
                    if tidx >= 0:
                        piece = raw[tidx:end]
                        if match_judge(piece.rstrip("？?")) is not None:
                            frag_start, frag = tidx, piece
                if frag is not None and frag_start >= 0:
                    cands.append((frag_start, end, frag.strip()))
                start = i + 1

    cands.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    out: list[tuple[int, int, str]] = []
    last_end = -1
    for s, e, frag in cands:
        if s < last_end:
            continue
        out.append((s, e, frag))
        last_end = e
    return out


def match_duration_only(text: str) -> Duration | None:
    raw = (text or "").strip().rstrip("？?")
    trigs = sorted(
        {t for rule in load_judge_rules() for t in rule.triggers},
        key=len,
        reverse=True,
    )
    for trig in (*trigs, "吗"):
        if raw.endswith(trig) and raw != trig:
            raw = raw[: -len(trig)]
            break
    return parse_duration(raw)


def compare(op: str, actual: int, limit: int) -> bool:
    fn = _OPS.get(op.casefold())
    if fn is None:
        raise ValueError(f"unknown op: {op}")
    return bool(fn(actual, limit))


def _parse_limit_num(limit_s: str) -> int | None:
    got = parse_cn_int(limit_s)
    if got is not None:
        return got
    try:
        return int(limit_s)
    except ValueError:
        return None


def evaluate_hit(
    machine: MachineWorld,
    hit: JudgeHit,
    *,
    waived_also: frozenset[str] | set[str] | None = None,
) -> JudgeOutcome:
    rule = hit.rule
    source = of_value(machine, "出处", rule.topic) or ""
    trig = hit.trigger
    inv = hit.invert_polar
    missing = _check_also(machine, rule, waived=waived_also)
    if missing:
        return JudgeOutcome(
            kind="ask",
            topic=rule.topic,
            detail=f"need_also:{missing}",
            ask=f"请问{rule.topic}是否已「{missing}」？",
            source=source,
            trigger=trig,
            invert_polar=inv,
        )
    if hit.need_value:
        if rule.op == "in":
            ask = f"请问{rule.topic}是哪一种？"
        else:
            unit = of_value(machine, "单位", rule.topic) or ""
            if unit == "月":
                ask = f"请问{rule.topic}几个月？"
            elif unit == "天":
                ask = f"请问{rule.topic}多少天？"
            elif unit == "年":
                ask = f"请问{rule.topic}几年？"
            else:
                ask = f"请问{rule.topic}多久？"
        return JudgeOutcome(
            kind="ask",
            topic=rule.topic,
            detail="need_value",
            ask=ask,
            source=source,
            trigger=trig,
            invert_polar=inv,
        )

    if rule.op == "in":
        allowed = of_values(machine, "许可", rule.topic)
        if not allowed:
            return JudgeOutcome(
                kind="miss",
                topic=rule.topic,
                detail="no_permit",
                source=source,
                trigger=trig,
                invert_polar=inv,
            )
        ok = hit.enum_value in allowed or any(
            hit.enum_value == a or a in hit.enum_value or hit.enum_value in a
            for a in allowed
        )
        return JudgeOutcome(
            kind="answer",
            topic=rule.topic,
            ok=ok,
            detail="ok" if ok else "not_in",
            source=source,
            trigger=trig,
            invert_polar=inv,
        )

    assert hit.duration is not None
    dur = hit.duration
    unit_s = of_value(machine, "单位", rule.topic)
    if unit_s and dur.unit and unit_s != dur.unit:
        return JudgeOutcome(
            kind="miss",
            topic=rule.topic,
            detail="unit_mismatch",
            source=source,
            trigger=trig,
            invert_polar=inv,
        )
    if unit_s and not dur.unit:
        dur = Duration(value=dur.value, unit=unit_s)

    tiers = load_tiers()
    topic_tiers = tuple(t for t in tiers if t.topic == rule.topic)
    unit_label = unit_s or dur.unit or "月"
    bands = format_tier_bands(rule.topic, topic_tiers, unit=unit_label) if topic_tiers else ""

    # Tiered limit when contract length known → binary ok
    if hit.contract is not None:
        cm = duration_to_months(hit.contract)
        limit: int | None = None
        if cm is not None:
            limit = pick_tier_limit(rule.topic, cm, tiers=tiers)
        if limit is None:
            limit_s = of_value(machine, rule.key, rule.topic)
            if limit_s is None:
                return JudgeOutcome(
                    kind="miss",
                    topic=rule.topic,
                    detail="no_limit",
                    source=source,
                    trigger=trig,
                    invert_polar=inv,
                    conditions=bands,
                )
            limit = _parse_limit_num(limit_s)
            if limit is None:
                return JudgeOutcome(
                    kind="miss",
                    topic=rule.topic,
                    detail="bad_limit",
                    source=source,
                    trigger=trig,
                    invert_polar=inv,
                    conditions=bands,
                )
        ok = compare(rule.op, dur.value, limit)
        return JudgeOutcome(
            kind="answer",
            topic=rule.topic,
            ok=ok,
            detail="ok" if ok else "over_tier",
            source=source,
            trigger=trig,
            invert_polar=inv,
            conditions=bands,
        )

    # No contract: if topic has tiers, do not bare-yes on absolute 上限 alone
    if topic_tiers:
        allowing = [t for t in topic_tiers if compare(rule.op, dur.value, t.limit)]
        abs_s = of_value(machine, rule.key, rule.topic)
        abs_limit = _parse_limit_num(abs_s) if abs_s else None

        if hit.explain:
            ok = bool(allowing)
            if abs_limit is not None and not compare(rule.op, dur.value, abs_limit):
                ok = False
            return JudgeOutcome(
                kind="explain",
                topic=rule.topic,
                ok=ok,
                detail="explain",
                source=source,
                trigger=trig,
                invert_polar=inv,
                conditions=bands,
            )

        if abs_limit is not None and not compare(rule.op, dur.value, abs_limit):
            return JudgeOutcome(
                kind="answer",
                topic=rule.topic,
                ok=False,
                detail="over_abs",
                source=source,
                trigger=trig,
                invert_polar=inv,
                conditions=bands,
            )
        if not allowing:
            return JudgeOutcome(
                kind="answer",
                topic=rule.topic,
                ok=False,
                detail="no_tier",
                source=source,
                trigger=trig,
                invert_polar=inv,
                conditions=bands,
            )
        return JudgeOutcome(
            kind="answer",
            topic=rule.topic,
            ok=True,
            detail="conditional",
            source=source,
            trigger=trig,
            invert_polar=inv,
            conditions=bands,
        )

    # Absolute limit only (no tiers for this topic)
    limit_s = of_value(machine, rule.key, rule.topic)
    if limit_s is None:
        return JudgeOutcome(
            kind="miss",
            topic=rule.topic,
            detail="no_limit",
            source=source,
            trigger=trig,
            invert_polar=inv,
        )
    limit = _parse_limit_num(limit_s)
    if limit is None:
        return JudgeOutcome(
            kind="miss",
            topic=rule.topic,
            detail="bad_limit",
            source=source,
            trigger=trig,
            invert_polar=inv,
        )

    ok = compare(rule.op, dur.value, limit)
    return JudgeOutcome(
        kind="answer",
        topic=rule.topic,
        ok=ok,
        detail="ok",
        source=source,
        trigger=trig,
        invert_polar=inv,
    )


def _match_pending_duration_legal(
    text: str,
    pending_topic: str,
    rules: tuple[JudgeRule, ...],
) -> JudgeHit | None:
    """Bare 「六个月不违法」 / 「6个月合法吗」 while pending a judge topic."""
    raw = (text or "").strip().rstrip("？?")
    if not raw or not pending_topic:
        return None
    for rule in rules:
        if rule.topic != pending_topic or rule.op == "in":
            continue
        for trig in sorted(rule.triggers, key=len, reverse=True):
            if not raw.endswith(trig):
                continue
            body = raw[: -len(trig)].strip()
            dur = parse_duration(body)
            if dur is None:
                continue
            return JudgeHit(
                rule=rule,
                duration=dur,
                **_hit_flags(trig, explain=False),
            )
    # Also allow POS_LEGAL / NEG without being listed (defensive)
    for trig in sorted(_POS_LEGAL_TRIG | _NEG_TRIG, key=len, reverse=True):
        if not raw.endswith(trig):
            continue
        body = raw[: -len(trig)].strip()
        dur = parse_duration(body)
        if dur is None:
            continue
        for rule in rules:
            if rule.topic != pending_topic or rule.op == "in":
                continue
            return JudgeHit(
                rule=rule,
                duration=dur,
                **_hit_flags(trig, explain=False),
            )
    return None


def judge(
    machine: MachineWorld,
    text: str,
    *,
    rules: tuple[JudgeRule, ...] | None = None,
    pending_topic: str = "",
    waived_also: frozenset[str] | set[str] | None = None,
    pending_text: str = "",
) -> JudgeOutcome | None:
    """Return outcome, or None if text is not a judge question / pending resume."""
    rules = rules if rules is not None else load_judge_rules()
    raw = (text or "").strip()

    # Affirm resume for conjunction ask
    if pending_topic and pending_text and re.fullmatch(
        r"(是|对|有|已约定|书面约定了?|是的)\s*[。.!！]?", raw
    ):
        hit = match_judge(pending_text, rules=rules)
        if hit is not None and hit.rule.topic == pending_topic:
            # waive first missing also from detail path: waive all rule.also for this turn
            return evaluate_hit(
                machine, hit, waived_also=set(hit.rule.also) | set(waived_also or ())
            )

    hit = match_judge(text, rules=rules)
    if hit is not None:
        return evaluate_hit(machine, hit, waived_also=waived_also)

    if pending_topic:
        # 「六个月不违法」while waiting after 试用期合法吗
        legal_hit = _match_pending_duration_legal(text, pending_topic, rules)
        if legal_hit is not None:
            return evaluate_hit(machine, legal_hit, waived_also=waived_also)
        dur = match_duration_only(text)
        if dur is not None:
            for rule in rules:
                if rule.topic != pending_topic or rule.op == "in":
                    continue
                return evaluate_hit(
                    machine,
                    JudgeHit(rule=rule, duration=dur),
                    waived_also=waived_also,
                )
        # bare enum value resume (short answers only; avoid「加班费怎么算」等长句误吸入)
        for rule in rules:
            if rule.topic != pending_topic or rule.op != "in":
                continue
            bare = raw.rstrip("？?")
            if not bare or any(bare.endswith(t) for t in rule.triggers):
                continue
            if len(bare) > 16 or any(x in bare for x in ("怎么", "什么", "为何", "是否", "如何")):
                continue
            return evaluate_hit(
                machine,
                JudgeHit(rule=rule, enum_value=bare),
                waived_also=waived_also,
            )
    return None
