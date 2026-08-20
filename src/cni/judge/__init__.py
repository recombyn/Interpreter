"""D69 judgment: threshold / enum / tiers / conjunction + missing-slot ask.

Table-1 algorithms; topics and facts live under knowledge/user/.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re

from cni.kernel.machine import MachineWorld
from cni.kernel.tmutil import clean
from cni.paths import USER_DIR

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

_OPS = {
    "le": lambda a, b: a <= b,
    "ge": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
    "lt": lambda a, b: a < b,
    "gt": lambda a, b: a > b,
}


@dataclass(frozen=True)
class JudgeRule:
    topic: str
    op: str  # le|ge|eq|lt|gt|in
    key: str  # 上限|下限|许可
    triggers: tuple[str, ...]
    also: tuple[str, ...] = ()


@dataclass(frozen=True)
class Duration:
    value: int
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


@dataclass(frozen=True)
class JudgeOutcome:
    """kind: answer | ask | miss — miss → REN2."""

    kind: str
    topic: str
    ok: bool = False
    detail: str = ""
    ask: str = ""
    source: str = ""


def clear_judge_cache() -> None:
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
    rules.sort(key=lambda r: len(r.topic), reverse=True)
    return rules, tiers


@lru_cache(maxsize=4)
def load_judge_rules(path: str | None = None) -> tuple[JudgeRule, ...]:
    p = Path(path) if path else _RULES
    rules, _ = _parse_rules_file(p)
    return tuple(rules)


@lru_cache(maxsize=4)
def load_tiers(path: str | None = None) -> tuple[Tier, ...]:
    p = Path(path) if path else _RULES
    _, tiers = _parse_rules_file(p)
    return tuple(tiers)


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


def parse_duration(text: str) -> Duration | None:
    m = _DURATION.match(text or "")
    if m is None:
        return None
    val = parse_cn_int(m.group("num"))
    if val is None:
        return None
    unit_raw = (m.group("unit") or "").strip()
    if "月" in unit_raw:
        unit = "月"
    elif unit_raw in {"天", "日"}:
        unit = "天"
    elif unit_raw == "年":
        unit = "年"
    else:
        unit = ""
    return Duration(value=val, unit=unit)


def duration_to_months(dur: Duration) -> int | None:
    if dur.unit == "月" or not dur.unit:
        return dur.value
    if dur.unit == "年":
        return dur.value * 12
    if dur.unit == "天":
        return max(1, dur.value // 30)
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


def match_judge(
    text: str, rules: tuple[JudgeRule, ...] | None = None
) -> JudgeHit | None:
    raw = (text or "").strip().rstrip("？?")
    if not raw:
        return None
    rules = rules if rules is not None else load_judge_rules()

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
            contract = parse_duration(m.group(1).strip("，, "))
            probation = parse_duration(m.group(2).strip("，, "))
            if probation is None:
                continue
            return JudgeHit(rule=rule, duration=probation, contract=contract)

    for rule in rules:
        for trig in sorted(rule.triggers, key=len, reverse=True):
            if not raw.endswith(trig):
                continue
            body = raw[: -len(trig)]
            if not body.startswith(rule.topic):
                continue
            mid = body[len(rule.topic) :].strip()
            if not mid:
                return JudgeHit(rule=rule, need_value=True)
            if rule.op == "in":
                return JudgeHit(rule=rule, enum_value=mid)
            probation, contract = split_probation_contract(mid)
            if probation is None:
                continue
            return JudgeHit(rule=rule, duration=probation, contract=contract)
    return None


def match_duration_only(text: str) -> Duration | None:
    raw = (text or "").strip().rstrip("？?")
    for trig in ("合法吗", "合规吗", "可以吗", "吗"):
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
    limit = parse_cn_int(limit_s)
    if limit is not None:
        return limit
    if limit_s.isdigit():
        return int(limit_s)
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
    missing = _check_also(machine, rule, waived=waived_also)
    if missing:
        return JudgeOutcome(
            kind="ask",
            topic=rule.topic,
            detail=f"need_also:{missing}",
            ask=f"请问{rule.topic}是否已「{missing}」？",
            source=source,
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
            kind="ask", topic=rule.topic, detail="need_value", ask=ask, source=source
        )

    if rule.op == "in":
        allowed = of_values(machine, "许可", rule.topic)
        if not allowed:
            return JudgeOutcome(
                kind="miss", topic=rule.topic, detail="no_permit", source=source
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
        )

    assert hit.duration is not None
    dur = hit.duration
    unit_s = of_value(machine, "单位", rule.topic)
    if unit_s and dur.unit and unit_s != dur.unit:
        return JudgeOutcome(
            kind="miss", topic=rule.topic, detail="unit_mismatch", source=source
        )
    if unit_s and not dur.unit:
        dur = Duration(value=dur.value, unit=unit_s)

    # Tiered limit when contract length known
    limit: int | None = None
    if hit.contract is not None:
        cm = duration_to_months(hit.contract)
        if cm is not None:
            limit = pick_tier_limit(rule.topic, cm)

    if limit is None:
        limit_s = of_value(machine, rule.key, rule.topic)
        if limit_s is None:
            return JudgeOutcome(
                kind="miss", topic=rule.topic, detail="no_limit", source=source
            )
        limit = _parse_limit_num(limit_s)
        if limit is None:
            return JudgeOutcome(
                kind="miss", topic=rule.topic, detail="bad_limit", source=source
            )

    ok = compare(rule.op, dur.value, limit)
    return JudgeOutcome(
        kind="answer", topic=rule.topic, ok=ok, detail="ok", source=source
    )


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


def match_judge_legacy(
    text: str, rules: tuple[JudgeRule, ...] | None = None
) -> tuple[JudgeRule, Duration] | None:
    hit = match_judge(text, rules=rules)
    if hit is None or hit.duration is None or hit.need_value:
        return None
    return hit.rule, hit.duration
