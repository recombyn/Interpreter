"""Run labor-domain eval cases from user-layer JSON (no surface strings in this module).

Does not modify system world (lex/system.tm). Loads knowledge/user domain memory
and exercises teach/query/dict/judge paths.

Usage:
  PYTHONPATH=src python -m para.tools.eval_labor_law
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

from para.kernel import boot
from para.kernel.machine import load_msgs
from para.paths import USER_DIR, set_user_dir
from para.preprocess import apply_user_dict, clear_user_dict_cache
from para.route import route, turn
from para.session import Session


def _labor_dir() -> Path:
    """Resolve domain folder by locating eval_cases.json under knowledge/user."""
    if not USER_DIR.is_dir():
        return USER_DIR
    for path in sorted(USER_DIR.rglob("eval_cases.json")):
        return path.parent
    return USER_DIR


LABOR_DIR = _labor_dir()
LABOR_MEMORY = LABOR_DIR / "labor_law.tm"
CASES_PATH = LABOR_DIR / "eval_cases.json"
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


def _load_cases() -> dict:
    if not CASES_PATH.is_file():
        raise FileNotFoundError(f"missing user-layer cases: {CASES_PATH}")
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _boot_with_user_labor() -> tuple:
    set_user_dir(USER_DIR)
    clear_user_dict_cache()
    w = boot(memory_path=None)
    if LABOR_MEMORY.is_file():
        load_msgs(w, LABOR_MEMORY)
    limits = LABOR_DIR / "limits.tm"
    if limits.is_file():
        load_msgs(w, limits)
    # Synced statute lines (D67 content); optional until texts are compiled.
    statute = LABOR_DIR / "劳动法.tm"
    if statute.is_file():
        load_msgs(w, statute)
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
    also_expected: list[str] | None = None,
) -> None:
    if match == "equals":
        ok = actual == expected
    elif match == "rule":
        ok = rule == expected
    else:
        ok = expected in (actual or "")
    if also_expected:
        text = actual or ""
        ok = ok and all(s in text for s in also_expected)
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


def eval_memory_queries(report: Report, cases: dict) -> None:
    w, s = _boot_with_user_labor()
    for row in cases.get("memory_query", []):
        got = turn(w, s, row["input"])
        _check(
            report,
            category="memory_query",
            name=row["name"],
            inp=row["input"],
            expected=row["expected"],
            actual=got.spoken or "",
            rule=got.rule,
        )


def eval_teach_roundtrip(report: Report, cases: dict) -> None:
    w, s = _boot_with_user_labor()
    for row in cases.get("teach_roundtrip", []):
        g = route(w, s, row["teach"])
        _check(
            report,
            category="teach_write",
            name=row["name"] + "_write",
            inp=row["teach"],
            expected=row["write_expected"],
            actual=g.spoken or "",
            rule=g.rule,
            note="write path",
        )
        q = turn(w, s, row["ask"])
        _check(
            report,
            category="teach_query",
            name=row["name"] + "_query",
            inp=row["ask"],
            expected=row["ask_expected"],
            actual=q.spoken or "",
            rule=q.rule,
        )


def eval_user_dict(report: Report, cases: dict) -> None:
    set_user_dir(USER_DIR)
    clear_user_dict_cache()
    for row in cases.get("user_dict", []):
        out = apply_user_dict(row["input"])
        _check(
            report,
            category="user_dict",
            name=row["name"],
            inp=row["input"],
            expected=row["expected"],
            actual=out,
            match="equals",
        )


def eval_dict_then_teach(report: Report, cases: dict) -> None:
    """Aliases rewritten then taught/queried (no preloaded memory for these)."""
    set_user_dir(USER_DIR)
    clear_user_dict_cache()
    w = boot(memory_path=None)
    s = Session()
    for row in cases.get("dict_pipeline", []):
        got = route(w, s, row["input"])
        _check(
            report,
            category="dict_pipeline",
            name=row["name"],
            inp=row["input"],
            expected=row["expected"],
            actual=got.spoken or "",
            rule=got.rule,
            note=row.get("note") or "",
        )


def eval_judge(report: Report, cases: dict) -> None:
    """D69 threshold / ask using limits.tm + rules.tm."""
    w, s = _boot_with_user_labor()
    for row in cases.get("judge", []):
        got = turn(w, s, row["input"])
        _check(
            report,
            category="judge",
            name=row["name"],
            inp=row["input"],
            expected=row["expected"],
            actual=got.spoken or "",
            rule=got.rule,
            note=row.get("note") or "",
            match=row.get("match", "contains"),
        )


def eval_long_query(report: Report, cases: dict) -> None:
    """Long utterances that still peel D69/D67 spans."""
    w, s = _boot_with_user_labor()
    for row in cases.get("long_query", []):
        got = turn(w, s, row["input"])
        _check(
            report,
            category="long_query",
            name=row["name"],
            inp=row["input"],
            expected=row["expected"],
            actual=got.spoken or "",
            rule=got.rule,
            note=row.get("note") or "",
            match=row.get("match", "contains"),
            also_expected=row.get("also_expected"),
        )


def eval_multi_query(report: Report, cases: dict) -> None:
    """One utterance with multiple query spans; answers joined with ；."""
    w, s = _boot_with_user_labor()
    for row in cases.get("multi_query", []):
        got = turn(w, s, row["input"])
        _check(
            report,
            category="multi_query",
            name=row["name"],
            inp=row["input"],
            expected=row["expected"],
            actual=got.spoken or "",
            rule=got.rule,
            note=row.get("note") or "",
            match=row.get("match", "contains"),
            also_expected=row.get("also_expected"),
        )


def eval_known_gaps(report: Report, cases: dict) -> None:
    """Document hard limits without user-dict mitigation."""
    from para.decode.lex import lex_ch
    from para.preprocess import apply_i
    from para.repair import repair

    for row in cases.get("known_gap", []):
        kind = row.get("kind", "")
        match = row.get("match", "equals")
        if kind == "i11":
            prep = apply_i(row["input"])
            actual, rule = prep.intercept_rule, prep.intercept_rule
        elif kind == "repair":
            lex = lex_ch()
            actual, rule = repair(row["input"], lex.vocab, set()), ""
        elif kind == "empty_turn":
            w, s = boot(memory_path=None), Session()
            q = turn(w, s, row["input"])
            actual, rule = q.spoken or "", q.rule
        else:
            continue
        _check(
            report,
            category="known_gap",
            name=row["name"],
            inp=row["input"],
            expected=row["expected"],
            actual=actual,
            rule=rule,
            note=row.get("note") or "",
            match=match,
        )


def finalize(report: Report, cases: dict) -> None:
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
    report.findings = list(cases.get("findings") or [])


def main() -> int:
    cases = _load_cases()
    report = Report(
        title="Para Labor-Law Capability (User Layer)",
        layer="knowledge/user only (labor_law.tm + user_dict.tm + eval_cases.json)",
        memory_file=str(LABOR_MEMORY),
    )
    eval_user_dict(report, cases)
    eval_memory_queries(report, cases)
    eval_teach_roundtrip(report, cases)
    eval_dict_then_teach(report, cases)
    eval_judge(report, cases)
    eval_long_query(report, cases)
    eval_multi_query(report, cases)
    eval_known_gaps(report, cases)
    finalize(report, cases)

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
        print(
            f"FAIL [{c.category}/{c.name}] {c.input!r} "
            f"expected={c.expected!r} actual={c.actual!r} rule={c.rule}"
        )
    return 0 if report.summary.get("failed", 1) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
