"""Evaluate Interpreter labor-law capability using user-layer knowledge only.

Does not modify system world (lex/system.tm). Loads knowledge/user/labor_law.tm
as memory and exercises teach/query/dict paths.

Usage:
  PYTHONPATH=src python -m cni.tools.eval_labor_law
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

from cni.kernel import boot
from cni.kernel.machine import load_msgs
from cni.paths import USER_DIR
from cni.preprocess import apply_user_dict, load_user_dict
from cni.route import hear, route, turn
from cni.session import Session

LABOR_DIR = USER_DIR / "劳动法"
LABOR_MEMORY = LABOR_DIR / "labor_law.tm"
REPORT_PATH = LABOR_DIR / "labor_law_eval_report.json"


@dataclass
class CaseResult:
    category: str
    name: str
    input: str
    expected: str
    actual: str
    rule: str
    ok: bool
    note: str = ""


@dataclass
class Report:
    title: str
    layer: str
    memory_file: str
    summary: dict[str, int] = field(default_factory=dict)
    by_category: dict[str, dict[str, int]] = field(default_factory=dict)
    cases: list[CaseResult] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)


def _boot_with_user_labor() -> tuple:
    w = boot(memory_path=None)
    if LABOR_MEMORY.is_file():
        load_msgs(w, LABOR_MEMORY)
    return w, Session()


def _check(
    report: Report,
    *,
    category: str,
    name: str,
    inp: str,
    expected: str,
    actual: str,
    rule: str = "",
    note: str = "",
    match: str = "contains",
) -> None:
    if match == "equals":
        ok = actual == expected
    elif match == "rule":
        ok = rule == expected
    else:
        ok = expected in (actual or "")
    report.cases.append(
        CaseResult(
            category=category,
            name=name,
            input=inp,
            expected=expected,
            actual=actual or "",
            rule=rule or "",
            ok=ok,
            note=note,
        )
    )


def eval_memory_queries(report: Report) -> None:
    w, s = _boot_with_user_labor()
    pairs = [
        ("isa_employee", "员工是什么", "员工是人"),
        ("isa_company", "公司是什么", "公司是组织"),
        ("isa_contract", "劳动合同是什么", "劳动合同是合同"),
        ("isa_overtime", "加班是什么", "加班是工作"),
        ("isa_wage", "最低工资是什么", "最低工资是工资"),
        ("isa_hours", "法定工时是什么", "法定工时是八小时"),
        ("has_yes", "公司有员工吗", "是的"),
        ("content_labor", "劳动法的内容是什么", "保护劳动者的合法权益"),
        ("content_contract_law", "劳动合同法的内容是什么", "规范劳动合同的订立履行"),
    ]
    for name, q, exp in pairs:
        got = turn(w, s, q)
        _check(
            report,
            category="memory_query",
            name=name,
            inp=q,
            expected=exp,
            actual=got.spoken or "",
            rule=got.rule,
        )


def eval_teach_roundtrip(report: Report) -> None:
    w, s = _boot_with_user_labor()
    teaches = [
        ("teach_isa", "教兼职是工作", "兼职是工作", "兼职是什么"),
        ("teach_has", "教员工有社保", "员工有社会保险", "员工有社保吗"),
        ("teach_content", "教规章的内容是不得违法解除", "规章的内容是不得违法解除", "规章的内容是什么"),
    ]
    for name, teach, spoken_sub, ask in teaches:
        g = route(w, s, teach)
        _check(
            report,
            category="teach_write",
            name=name + "_write",
            inp=teach,
            expected=spoken_sub,
            actual=g.spoken or "",
            rule=g.rule,
            note="write path",
        )
        q = turn(w, s, ask)
        if ask.endswith("吗"):
            exp_q = "是的"
        elif "内容" in ask:
            exp_q = "不得违法解除"
        else:
            exp_q = spoken_sub
        _check(
            report,
            category="teach_query",
            name=name + "_query",
            inp=ask,
            expected=exp_q,
            actual=q.spoken or "",
            rule=q.rule,
        )


def eval_user_dict(report: Report) -> None:
    load_user_dict.cache_clear()
    pairs = [
        ("dict_overtime", "OT是工作", "加班是工作"),
        ("dict_worker", "劳动者是人", "员工是人"),
        ("dict_employer", "用人单位是组织", "公司是组织"),
        ("dict_en", "laborlaw的内容是保护权益", "劳动法的内容是保护权益"),
        ("dict_social", "员工有五险一金", "员工有社会保险"),
        ("dict_plus_gap", "N+1是工作", "N+1是工作"),
    ]
    for name, src, exp in pairs:
        out = apply_user_dict(src)
        _check(
            report,
            category="user_dict",
            name=name,
            inp=src,
            expected=exp,
            actual=out,
            match="equals",
        )


def eval_dict_then_teach(report: Report) -> None:
    """Aliases rewritten then taught/queried (no preloaded memory for these)."""
    w = boot(memory_path=None)
    s = Session()
    load_user_dict.cache_clear()
    # After dict: 劳动者→员工; teach isa; ask
    g = route(w, s, "教劳动者是人")
    _check(
        report,
        category="dict_pipeline",
        name="worker_alias_teach",
        inp="教劳动者是人",
        expected="员工是人",
        actual=g.spoken or "",
        rule=g.rule,
        note="user_dict maps 劳动者→员工 before I11",
    )
    q = turn(w, s, "员工是什么")
    _check(
        report,
        category="dict_pipeline",
        name="worker_alias_query",
        inp="员工是什么",
        expected="员工是人",
        actual=q.spoken or "",
        rule=q.rule,
    )

    g2 = route(w, s, "教OT是工作")
    _check(
        report,
        category="dict_pipeline",
        name="overtime_alias_teach",
        inp="教OT是工作",
        expected="加班是工作",
        actual=g2.spoken or "",
        rule=g2.rule,
    )


def eval_known_gaps(report: Report) -> None:
    """Document hard limits without user-dict mitigation."""
    from cni.preprocess import apply_i
    from cni.repair import repair
    from cni.decode.lex import lex_ch

    # Raw I11 trap: 者 inside 劳动者
    prep = apply_i("劳动者是人")
    _check(
        report,
        category="known_gap",
        name="i11_blocks_worker_literal",
        inp="劳动者是人",
        expected="I11",
        actual=prep.intercept_rule,
        match="equals",
        note="classical particle 者 triggers I11 without user_dict alias",
    )

    lex = lex_ch()
    fixed = repair("法定工时是八小时", lex.vocab, set())
    _check(
        report,
        category="known_gap",
        name="pin_corrupts_hour",
        inp="法定工时是八小时",
        expected="八小是",
        actual=fixed,
        note="E2 pin 时→是 when 小时 not yet in domain",
        match="contains",
    )

    # Without memory, open labor ask misses
    w, s = boot(memory_path=None), Session()
    q = turn(w, s, "劳动法的内容是什么")
    _check(
        report,
        category="known_gap",
        name="empty_world_miss",
        inp="劳动法的内容是什么",
        expected="我不知道",
        actual=q.spoken or "",
        rule=q.rule,
        note="no user memory ⇒ REN2",
        match="equals",
    )


def finalize(report: Report) -> None:
    total = len(report.cases)
    passed = sum(1 for c in report.cases if c.ok)
    failed = total - passed
    report.summary = {"total": total, "passed": passed, "failed": failed}
    cats: dict[str, dict[str, int]] = {}
    for c in report.cases:
        bucket = cats.setdefault(c.category, {"total": 0, "passed": 0, "failed": 0})
        bucket["total"] += 1
        bucket["passed" if c.ok else "failed"] += 1
    report.by_category = cats
    report.findings = [
        "User-layer memory (labor_law.tm) enables isa/has/content Q&A without touching system lex.",
        "user_dict aliases (劳动者→员工, OT→加班) let teach path avoid I11 and use Interpreter-friendly surfaces.",
        "Literal 劳动者 is blocked by I11 (classical 者); mitigation must stay in user_dict, not system.tm.",
        "Character pin 时→是 corrupts 小时 before domain knows the open name; seed memory or avoid 时 in first teach.",
        "Empty world correctly returns REN2 for labor questions — knowledge is not baked into system layer.",
        "Latin user_dict keys must match [A-Za-z][A-Za-z0-9]* (e.g. OT); tokens like N+1 are not rewritten.",
    ]


def main() -> int:
    report = Report(
        title="Interpreter Labor-Law Capability (User Layer)",
        layer="knowledge/user only (labor_law.tm + user_dict.tm)",
        memory_file=str(LABOR_MEMORY),
    )
    eval_user_dict(report)
    eval_memory_queries(report)
    eval_teach_roundtrip(report)
    eval_dict_then_teach(report)
    eval_known_gaps(report)
    finalize(report)

    payload = {
        "title": report.title,
        "layer": report.layer,
        "memory_file": report.memory_file,
        "summary": report.summary,
        "by_category": report.by_category,
        "findings": report.findings,
        "cases": [asdict(c) for c in report.cases],
    }
    REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report.summary, ensure_ascii=False))
    print(f"wrote {REPORT_PATH}")
    failed = [c for c in report.cases if not c.ok]
    for c in failed:
        print(f"FAIL [{c.category}/{c.name}] {c.input!r} expected={c.expected!r} actual={c.actual!r} rule={c.rule}")
    return 0 if report.summary.get("failed", 1) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
