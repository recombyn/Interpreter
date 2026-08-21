"""100-case D69-focused eval (tiers / triggers / composition gaps).

Usage:
  set PYTHONPATH=src
  python -m para.tools.eval_d69_100
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

from para import Para
from para.paths import USER_DIR

LABOR_DIR = USER_DIR / "劳动法"
CASES_PATH = LABOR_DIR / "d69_cases_100.json"
REPORT_PATH = LABOR_DIR / "d69_100_report.json"

# Contract months → tier max probation (months)
_TIERS = (
    (0, 3, 0),
    (3, 12, 1),
    (12, 36, 2),
    (36, None, 6),
)

_CONTRACTS: list[tuple[str, float]] = [
    ("2月", 2),
    ("3月", 3),
    ("6月", 6),
    ("1年", 12),
    ("2年", 24),
    ("3年", 36),
    ("5年", 60),
]

_TRIALS: list[tuple[str, float]] = [
    ("0个月", 0),
    ("半个月", 0.5),
    ("1月", 1),
    ("2月", 2),
    ("3月", 3),
    ("6月", 6),
    ("7月", 7),
]


def _tier_max(contract_months: float) -> float:
    for lo, hi, lim in _TIERS:
        if contract_months >= lo and (hi is None or contract_months < hi):
            return float(lim)
    return 0.0


def _legal(contract_m: float, trial_m: float) -> bool:
    return trial_m <= _tier_max(contract_m)


def _case(
    cid: str,
    category: str,
    inp: str,
    expected: str | list[str],
    *,
    match: str = "contains",
    turns: list[str] | None = None,
    tag: str | None = None,
    expect_status: str | None = None,
    note: str = "",
    wanted_upgrade: str = "",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": cid,
        "category": category,
        "input": inp,
        "expected": expected,
        "match": match,
    }
    if turns is not None:
        row["turns"] = turns
    if tag:
        row["tag"] = tag
    if expect_status:
        row["expect_status"] = expect_status
    if note:
        row["note"] = note
    if wanted_upgrade:
        row["wanted_upgrade"] = wanted_upgrade
    return row


def _trial_surface(tn: str) -> str:
    return {
        "0个月": "零个月",
        "半个月": "半个月",
        "1月": "一个月",
        "2月": "二个月",
        "3月": "三个月",
        "6月": "六个月",
        "7月": "七个月",
    }.get(tn, tn)


def _contract_surface(cn: str) -> str:
    return {
        "2月": "二个月",
        "3月": "三个月",
        "6月": "六个月",
        "1年": "一年",
        "2年": "二年",
        "3年": "三年",
        "5年": "五年",
    }.get(cn, cn)


def generate_cases() -> list[dict[str, Any]]:
    """Build exactly 100 D69 stress cases (deterministic)."""
    cases: list[dict[str, Any]] = []
    n = 0

    def add(row: dict[str, Any]) -> None:
        nonlocal n
        n += 1
        row["id"] = row.get("id") or f"d69_{n:03d}"
        cases.append(row)

    # --- tier_binary (~28): legal matrix samples ---
    # Pick combinations that cover each tier edge + over-limit.
    tier_picks: list[tuple[str, float, str, float]] = [
        # [0,3) max 0
        ("2月", 2, "0个月", 0),
        ("2月", 2, "半个月", 0.5),
        ("2月", 2, "1月", 1),
        ("2月", 2, "2月", 2),
        # [3,12) max 1
        ("3月", 3, "半个月", 0.5),
        ("3月", 3, "1月", 1),
        ("3月", 3, "2月", 2),
        ("6月", 6, "1月", 1),
        ("6月", 6, "2月", 2),
        ("6月", 6, "3月", 3),
        # [12,36) max 2
        ("1年", 12, "1月", 1),
        ("1年", 12, "2月", 2),
        ("1年", 12, "3月", 3),
        ("1年", 12, "6月", 6),
        ("2年", 24, "半个月", 0.5),
        ("2年", 24, "2月", 2),
        ("2年", 24, "3月", 3),
        ("2年", 24, "7月", 7),
        # [36,+inf) max 6
        ("3年", 36, "3月", 3),
        ("3年", 36, "6月", 6),
        ("3年", 36, "7月", 7),
        ("5年", 60, "半个月", 0.5),
        ("5年", 60, "2月", 2),
        ("5年", 60, "6月", 6),
        ("5年", 60, "7月", 7),
        # word-order variants (试用期…合同…)
        ("1年", 12, "2月", 2),
        ("3年", 36, "6月", 6),
        ("6月", 6, "1月", 1),
    ]
    assert len(tier_picks) == 28
    for i, (cn, cm, tn, tm) in enumerate(tier_picks):
        ok = _legal(cm, tm)
        csurf = _contract_surface(cn)
        tsurf = _trial_surface(tn)
        if i >= 25:
            inp = f"试用期{tsurf}合同{csurf}合法吗"
        else:
            inp = f"合同{csurf}试用期{tsurf}合法吗"
        add(
            _case(
                "",
                "tier_binary",
                inp,
                "合法" if ok else "不合法",
                note=f"tier max={_tier_max(cm)} trial={tm}",
            )
        )

    # --- conditional (~12): no contract duration ---
    cond = [
        ("试用期半个月合法吗", ["情况下合法", "合法"]),
        ("试用期一个月合法吗", ["情况下合法", "合法"]),
        ("试用期二个月合法吗", ["情况下合法", "合法"]),
        ("试用期三个月合法吗", ["情况下合法", "合法"]),
        ("试用期六个月合法吗", "情况下合法"),
        ("试用期七个月合法吗", "不合法"),
        ("试用期八个月合法吗", "不合法"),
        ("什么情况下试用期六个月不违法", ["情况下合法", "不得超过"]),
        ("什么情况下试用期一个月合法", ["情况下", "不得超过"]),
        ("试用期六个月合法吗", "不得超过"),  # narrative must cite caps
        ("试用期零个月合法吗", ["合法", "情况下"]),
        ("试用期一个半月合法吗", ["情况下合法", "合法"]),
    ]
    assert len(cond) == 12
    for inp, exp in cond:
        add(_case("", "conditional", inp, exp if isinstance(exp, str) else exp))

    # --- trigger_variants (~12) ---
    triggers = [
        ("试用期六个月合不合法", ["情况下合法", "合法"]),
        ("试用期六个月合规吗", "情况下合法"),
        ("试用期六个月可以吗", "情况下合法"),
        ("试用期六个月不违法吗", "情况下合法"),
        ("试用期六个月违法吗", "不违法"),
        ("试用期六个月不违法", "情况下合法"),
        ("试用期七个月合不合法", "不合法"),
        ("试用期七个月合规吗", "不合法"),
        ("试用期七个月可以吗", "不合法"),
        ("真的试用期六个月合法吗", "情况下合法"),
        ("到底试用期六个月合法吗", "情况下合法"),
        ("请问试用期六个月合法吗", "情况下合法"),
    ]
    assert len(triggers) == 12
    for inp, exp in triggers:
        add(_case("", "trigger_variants", inp, exp))

    # --- jingye (~8) ---
    jingye = [
        ("竞业限制一年合法吗", "合法"),
        ("竞业限制二年合法吗", "合法"),
        ("竞业限制两年合法吗", "合法"),
        ("竞业限制三年合法吗", "不合法"),
        ("竞业限制半年合法吗", "合法"),
        ("竞业限制三年合规吗", "不合法"),
        ("竞业限制二年可以吗", "合法"),
        ("竞业限制四年合法吗", "不合法"),
    ]
    assert len(jingye) == 8
    for inp, exp in jingye:
        add(_case("", "jingye", inp, exp))

    # --- enum (~6) ---
    enums = [
        ("合同类型固定期限合法吗", "合法"),
        ("合同类型无固定期限合法吗", "合法"),
        ("合同类型以完成一定工作任务为期限合法吗", "合法"),
        ("合同类型口头协议合法吗", "不合法"),
        ("合同类型临时工合法吗", "不合法"),
        ("合同类型固定期限合规吗", "合法"),
    ]
    assert len(enums) == 6
    for inp, exp in enums:
        add(_case("", "enum", inp, exp))

    # --- conjunction (~8) ---
    conj = [
        ("试用期六个月严格合法吗", "情况下合法"),
        ("试用期一个月严格合法吗", ["情况下合法", "合法"]),
        ("合同三年试用期六个月严格合法吗", "合法"),
        ("合同一年试用期二个月严格合法吗", "合法"),
        ("合同一年试用期三个月严格合法吗", "不合法"),
        ("试用期七个月严格合法吗", "不合法"),
        # with USER_DIR limits.tm, 书面约定 fact present → no ask; still exercise surface
        ("试用期六个月严格合法吗", "不得超过"),
        ("合同五年试用期六个月严格合法吗", "合法"),
    ]
    assert len(conj) == 8
    for inp, exp in conj:
        add(_case("", "conjunction", inp, exp))

    # --- multi_long (~10) ---
    prefix = "本人已阅读材料并知悉应当依法订立劳动合同。"
    multi = [
        (
            "试用期六个月合法吗竞业限制二年合法吗",
            ["情况下合法", "竞业限制二年合法"],
        ),
        (
            "竞业限制二年合法吗试用期六个月合法吗",
            ["竞业限制二年合法", "情况下合法"],
        ),
        (
            "试用期七个月合法吗竞业限制三年合法吗",
            ["不合法", "不合法"],
        ),
        (
            "合同类型固定期限合法吗试用期六个月合法吗",
            ["合法", "情况下合法"],
        ),
        (prefix + "试用期六个月合法吗", "情况下合法"),
        (prefix + "竞业限制二年合法吗", "合法"),
        ("另外试用期六个月合法吗", "情况下合法"),
        ("另外竞业限制三年合法吗", "不合法"),
        (
            "试用期六个月合法吗另外竞业限制二年合法吗",
            ["情况下合法", "合法"],
        ),
        (
            prefix + "试用期六个月合法吗竞业限制二年合法吗",
            ["情况下合法", "竞业限制二年合法"],
        ),
    ]
    assert len(multi) == 10
    for inp, exp in multi:
        add(_case("", "multi_long", inp, exp))

    # --- ask_resume (~6): shared session across turns ---
    ask = [
        {
            "turns": ["试用期合法吗", "六个月"],
            "expected": "情况下合法",
            "note": "ask then duration",
        },
        {
            "turns": ["试用期合法吗", "六个月不违法"],
            "expected": ["情况下合法", "合法"],
            "note": "bare duration + polarity after pin",
        },
        {
            "turns": ["试用期合法吗", "七个月"],
            "expected": "不合法",
            "note": "ask then over-limit",
        },
        {
            "turns": ["竞业限制合法吗", "二年"],
            "expected": "合法",
            "note": "jingye ask resume",
        },
        {
            "turns": ["竞业限制合法吗", "三年"],
            "expected": "不合法",
            "note": "jingye ask over",
        },
        {
            "turns": ["试用期合法吗", "半个月"],
            "expected": ["情况下合法", "合法"],
            "note": "half-month resume",
        },
    ]
    assert len(ask) == 6
    for row in ask:
        add(
            _case(
                "",
                "ask_resume",
                row["turns"][-1],
                row["expected"],
                turns=row["turns"],
                note=row.get("note", ""),
            )
        )

    # --- composition: former gaps now gated (P1/P2 surface) ---
    p2 = [
        (
            "劳务派遣试用期三个月合法吗",
            "不知道",
            "p2_topic",
            "no 劳务派遣 rule — miss/REN2",
        ),
        (
            "试用期六个月或者七个月合法吗",
            "请问",
            "p2_or_dur",
            "or of durations — mixed → ask",
        ),
        (
            "试用期六个月并且竞业限制二年合法吗",
            "都合法",
            "p2_and",
            "conjunction of two judges without 都",
        ),
        (
            "试用期不是六个月合法吗",
            "请问",
            "p2_not_value",
            "negated duration → ask",
        ),
        (
            "合同一年试用期二个月或三个月合法吗",
            "请问",
            "p2_tier_or",
            "or under tier — mixed → ask",
        ),
        (
            "既没有书面约定又试用期七个月严格合法吗",
            "不合法",
            "p2_not_also",
            "not + over-limit + strict",
        ),
        (
            "试用期六个月且未书面约定严格合法吗",
            "不合法",
            "p2_not_also",
            "not+also on strict conjunction",
        ),
        (
            "没有书面约定试用期六个月合法吗",
            "不合法",
            "p2_not_also",
            "prefix 没有书面约定 on soft 合法吗",
        ),
        (
            "固定期限或无固定期限合同类型合法吗",
            "合法",
            "p2_enum_or",
            "or of enum values",
        ),
        (
            "竞业限制二年且试用期六个月都合法吗",
            "都合法",
            "p2_all",
            "all of two topics",
        ),
    ]
    for inp, exp, cat, note in p2:
        add(_case("", cat, inp, exp, note=note))

    # Keep total at 100: p2(10) replaces former 10 gaps
    assert len(p2) == 10
    assert len(cases) == 100, f"expected 100 cases, got {len(cases)}"
    # renumber ids stably
    for i, c in enumerate(cases, 1):
        c["id"] = f"d69_{i:03d}"
    return cases


def _contains_polar(text: str, needle: str) -> bool:
    """Substring match that does not treat 不合法 as 合法 (etc.).

    Also accepts trigger-aligned polar synonyms: 合法↔合规/可以, 不合法↔不合规/不可以.
    """
    yes_forms = ("合法", "合规", "可以", "不违法", "情况下合法")
    no_forms = ("不合法", "不合规", "不可以")
    if needle in {"合法", "合规", "可以", "情况下合法"}:
        if any(n in text for n in no_forms):
            return False
        if needle == "情况下合法":
            return "情况下合法" in text or (
                "情况下" in text and any(y in text for y in ("合法", "合规", "可以"))
            )
        return any(y in text for y in yes_forms)
    if needle == "不合法":
        return any(n in text for n in no_forms)
    if needle == "不违法":
        return "不违法" in text
    return needle in text


def _match_expected(spoken: str, expected: str | list[str], match: str, rule: str) -> bool:
    if match == "rule":
        return rule == (expected if isinstance(expected, str) else expected[0])
    if match == "equals":
        return spoken == (expected if isinstance(expected, str) else expected[0])
    # contains: any-of list (OR) when multiple alternatives; single string = must contain
    needles = expected if isinstance(expected, list) else [expected]
    text = spoken or ""
    if isinstance(expected, list):
        # Prefer: all non-polar extras (不得超过/情况) AND at least one polar/core
        polar = [n for n in needles if n in {"合法", "不合法", "不违法", "合规", "可以", "情况下合法"}]
        extras = [n for n in needles if n not in polar]
        if extras and not all(e in text for e in extras):
            return False
        if polar:
            return any(_contains_polar(text, p) for p in polar)
        return all(n in text for n in needles)
    return _contains_polar(text, needles[0]) if needles[0] in {
        "合法", "不合法", "不违法", "合规", "可以"
    } else needles[0] in text


def _gap_score(
    *,
    spoken: str,
    rule: str,
    expected: str | list[str],
    match: str,
) -> tuple[str, bool, str]:
    """Return (gap_hit|gap_miss, ok_coherent, note).

    gap_hit: current system behaved coherently for a known gap
             (D69/D69.ask/REN2, or clear refuse/miss), OR matched hoped output.
    gap_miss: incoherent crash-like / wrong-rule nonsense without refuse.
    ok: rule in D69 family / REN2 / explicit refuse — not a product regression crash.
    """
    coherent_rules = {"D69", "D69.ask", "REN2", "D67"}
    matched = _match_expected(spoken, expected, match, rule)
    coherent = rule in coherent_rules or (not spoken and rule == "") or "不知道" in (spoken or "")
    # D21 polar on composition is a known weak path — still "alive"
    if rule == "D21":
        coherent = True
    if matched:
        return "gap_hit", True, "matched hoped upgrade output (unexpected win)"
    if coherent:
        return "gap_hit", True, "coherent gap behavior (miss/ask/partial/wrong-scope)"
    return "gap_miss", False, f"incoherent rule={rule}"


@dataclass
class CaseResult:
    id: str
    category: str
    input: str
    expected: Any
    actual: str
    rule: str
    ok: bool
    tag: str = ""
    expect_status: str = ""
    gap_result: str = ""  # gap_hit | gap_miss | ""
    note: str = ""
    wanted_upgrade: str = ""
    turns: list[str] = field(default_factory=list)


@dataclass
class Report:
    title: str = "D69 100-case eval"
    summary: dict[str, int] = field(default_factory=dict)
    by_category: dict[str, dict[str, int]] = field(default_factory=dict)
    findings: list[str] = field(default_factory=list)
    cases: list[CaseResult] = field(default_factory=list)


def run_case(case: dict[str, Any]) -> CaseResult:
    turns = case.get("turns") or [case["input"]]
    tag = case.get("tag") or ""
    # Fresh Para per case; multi-turn shares one Para
    eng = Para(user_dir=USER_DIR, remember=False)
    out = None
    for t in turns:
        out = eng.decode(t, write=False)
    assert out is not None
    spoken = out.spoken or ""
    rule = out.rule or ""
    expected = case["expected"]
    match = case.get("match", "contains")

    if tag == "gap":
        gap_result, ok, note = _gap_score(
            spoken=spoken, rule=rule, expected=expected, match=match
        )
        return CaseResult(
            id=case["id"],
            category=case["category"],
            input=case.get("input") or turns[-1],
            expected=expected,
            actual=spoken,
            rule=rule,
            ok=ok,
            tag=tag,
            expect_status=case.get("expect_status") or "gap",
            gap_result=gap_result,
            note=note + ("; " + case["note"] if case.get("note") else ""),
            wanted_upgrade=case.get("wanted_upgrade") or "",
            turns=list(turns),
        )

    ok = _match_expected(spoken, expected, match, rule)
    return CaseResult(
        id=case["id"],
        category=case["category"],
        input=case.get("input") or turns[-1],
        expected=expected,
        actual=spoken,
        rule=rule,
        ok=ok,
        tag=tag,
        note=case.get("note") or "",
        turns=list(turns) if case.get("turns") else [],
    )


def finalize(report: Report) -> None:
    non_gap = [c for c in report.cases if c.tag != "gap"]
    gaps = [c for c in report.cases if c.tag == "gap"]
    passed = sum(1 for c in non_gap if c.ok)
    failed = sum(1 for c in non_gap if not c.ok)
    gap_hit = sum(1 for c in gaps if c.gap_result == "gap_hit")
    gap_miss = sum(1 for c in gaps if c.gap_result == "gap_miss")
    gap_fail = sum(1 for c in gaps if not c.ok)  # incoherent only
    report.summary = {
        "total": len(report.cases),
        "non_gap": len(non_gap),
        "passed": passed,
        "failed": failed,
        "gap_total": len(gaps),
        "gap_hit": gap_hit,
        "gap_miss": gap_miss,
        "gap_fail": gap_fail,
    }
    cats: dict[str, dict[str, int]] = {}
    for c in report.cases:
        b = cats.setdefault(
            c.category,
            {"total": 0, "passed": 0, "failed": 0, "gap_hit": 0, "gap_miss": 0},
        )
        b["total"] += 1
        if c.tag == "gap":
            if c.gap_result == "gap_hit":
                b["gap_hit"] += 1
            else:
                b["gap_miss"] += 1
        else:
            b["passed" if c.ok else "failed"] += 1
    report.by_category = cats

    # Auto findings from failures
    findings: list[str] = []
    fails = [c for c in non_gap if not c.ok]
    if fails:
        by_cat: dict[str, int] = {}
        for c in fails:
            by_cat[c.category] = by_cat.get(c.category, 0) + 1
        findings.append(
            "non-gap failures by category: "
            + ", ".join(f"{k}={v}" for k, v in sorted(by_cat.items()))
        )
    for c in gaps:
        if c.wanted_upgrade:
            findings.append(
                f"[{c.id}] wanted_upgrade: {c.wanted_upgrade} "
                f"(actual rule={c.rule} spoken={c.actual[:60]}…)"
            )
    # trigger 合不合法 known risk
    for c in report.cases:
        if "合不合法" in c.input and c.rule != "D69" and c.tag != "gap":
            findings.append(
                f"trigger 合不合法 routed to {c.rule} not D69 (id={c.id})"
            )
    report.findings = findings


def print_summary(report: Report) -> None:
    s = report.summary
    print("=== D69 100-case summary ===")
    print(
        f"total={s['total']} non_gap={s['non_gap']} "
        f"passed={s['passed']} failed={s['failed']} "
        f"gap_hit={s['gap_hit']} gap_miss={s['gap_miss']} gap_fail={s['gap_fail']}"
    )
    print("--- by category ---")
    for cat, b in sorted(report.by_category.items()):
        print(
            f"  {cat}: total={b['total']} passed={b['passed']} failed={b['failed']} "
            f"gap_hit={b['gap_hit']} gap_miss={b['gap_miss']}"
        )
    fails = [c for c in report.cases if c.tag != "gap" and not c.ok]
    print(f"--- top failure examples ({min(8, len(fails))}/{len(fails)}) ---")
    for c in fails[:8]:
        exp = c.expected if isinstance(c.expected, str) else "|".join(c.expected)
        print(
            f"  FAIL [{c.category}/{c.id}] {c.input!r}\n"
            f"    expected~{exp!r} rule={c.rule} actual={c.actual[:80]!r}"
        )
    gaps = [c for c in report.cases if c.tag == "gap"]
    print("--- gap samples ---")
    for c in gaps[:5]:
        print(
            f"  {c.gap_result} [{c.id}] {c.input!r} rule={c.rule} "
            f"upgrade={c.wanted_upgrade!r}"
        )


def main() -> int:
    LABOR_DIR.mkdir(parents=True, exist_ok=True)
    cases = generate_cases()
    CASES_PATH.write_text(
        json.dumps({"version": 1, "count": len(cases), "cases": cases}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {CASES_PATH} ({len(cases)} cases)")

    report = Report()
    for i, case in enumerate(cases, 1):
        result = run_case(case)
        report.cases.append(result)
        if i % 20 == 0:
            print(f"  … {i}/{len(cases)}")

    finalize(report)
    payload = {
        "title": report.title,
        "summary": report.summary,
        "by_category": report.by_category,
        "findings": report.findings,
        "cases": [asdict(c) for c in report.cases],
    }
    REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {REPORT_PATH}")
    print_summary(report)
    # Exit 0 even with failures — this is a diagnostic harness
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
