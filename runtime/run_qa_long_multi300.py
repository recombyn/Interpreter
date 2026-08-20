"""Stress: long-text parse + multi-question-in-one-turn — 300 prompts.

Does NOT expect full multi-answer support (ambig_mode first → often one hit).
Reports what Interpreter actually does: first-only / refuse / partial / misfire.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from cni.judge import clear_judge_cache
from cni.kernel import boot
from cni.knowledge.text_doc import load_user_memories
from cni.paths import USER_DIR
from cni.preprocess import load_user_dict
from cni.route import turn
from cni.session import Session
from cni.system_tm import clear_system_cache
from cni.tools.compile_labor_articles import extract_article_lines, main as compile_articles
from cni.user_config import clear_user_config_cache

ROOT = Path(__file__).resolve().parents[1]
LABOR = USER_DIR / "劳动法"
OUT_JSON = ROOT / "runtime" / "qa_long_multi300_report.json"
OUT_MD = ROOT / "runtime" / "qa_long_multi300_report.md"
TARGET = 300


def build_prompts() -> list[tuple[str, str]]:
    """(category, question) — ≥300 unique."""
    out: list[tuple[str, str]] = []

    def add(cat: str, q: str) -> None:
        out.append((cat, q))

    text_path = LABOR / "劳动法.text"
    lines = text_path.read_text(encoding="utf-8").splitlines() if text_path.is_file() else []
    articles = extract_article_lines(text_path) if text_path.is_file() else []
    # Prefer long non-empty lines for paste-style asks
    long_lines = [
        (i, ln.strip())
        for i, ln in enumerate(lines, 1)
        if len(ln.strip()) >= 40 and ln.strip() not in {"（空行）"}
    ]

    # --- A. 长行正文回显（D67）---
    for i, _ln in long_lines[:40]:
        add("长行正文", f"劳动法第{i}行的内容是什么")

    # --- B. 把长法条原文贴进问句再问（解析/抗噪）---
    for i, ln in long_lines[:25]:
        snippet = ln[:120]
        add("长文夹问", f"根据下面这段：{snippet}。请问劳动法第{i}行的内容是什么")
        add("长文夹问", f"原文是「{snippet}」，第{i}行有什么")

    # --- C. 长条按条查询 + 字 ---
    for no, line_no in articles[:30]:
        add("长条查询", f"请详细告诉我劳动法第{no}条的内容是什么，不要省略")
        add("长条夹字", f"劳动法第{no}条写得很长，请问它的第一个字是什么")
        if line_no <= len(lines) and len(lines[line_no - 1]) >= 20:
            add("长条夹字", f"劳动法第{line_no}行内容很多，第三个字是啥")

    # --- D. 同句双问 / 三问（多问题）---
    pairs = [
        ("劳动法第20行的内容是什么", "劳动法第21行的内容是什么"),
        ("劳动法第一条的内容是什么", "劳动法第二条的内容是什么"),
        ("试用期六个月合法吗", "竞业限制二年合法吗"),
        ("试用期三个月合法吗", "试用期七个月合法吗"),
        ("劳动法第84行的内容是什么", "试用期六个月合法吗"),
        ("劳动法第八条的第一个字是什么", "劳动法第八条有多少字"),
        ("合同类型固定期限合法吗", "试用期二个月合法吗"),
        ("劳动法第1行的内容是什么", "那第2行呢"),
        ("竞业限制一年合法吗", "竞业限制三年合法吗"),
        ("劳动法第一条的第三个字是啥", "劳动法第一条有多少字"),
    ]
    for a, b in pairs:
        add("双问并列", f"{a}？{b}？")
        add("双问逗号", f"{a}，另外{b}")
        add("双问和", f"{a}和{b}")
        add("双问还有", f"{a}，还有{b}")

    for a, b in pairs[:5]:
        c = "劳动法第50行的内容是什么"
        add("三问", f"{a}？{b}？{c}？")
        add("三问顿号", f"请问：{a}；{b}；{c}")

    # --- E. 长难单句（嵌套合规 + 检索）---
    for q in (
        "如果公司在劳动合同中约定试用期为六个月且合同期限为两年请问试用期六个月合法吗",
        "在已经书面约定的前提下试用期六个月严格合法吗并且劳动法第84行的内容是什么",
        "员工入职后被要求签订竞业限制两年且不给补偿时竞业限制二年合法吗",
        "请先回答试用期一个月合法吗然后再说明劳动法第十九条的内容是什么",
        "关于试用期不得超过六个月这一规定请问试用期五个月合法吗试用期七个月合法吗",
        "劳动合同法里提到的试用期上限结合合同一年一年的情况合同一年试用期二个月合法吗",
        "我想同时确认两件事试用期合法吗以及竞业限制合法吗",
        "先查劳动法第84行的内容是什么再判断试用期六个月合法吗",
        "在未看清条文的情况下直接问试用期八个月合法吗以及加班费怎么算",
        "若口头约定试用期半个月而书面合同为三年试用期半个月合法吗",
    ):
        add("长难单句", q)

    # --- F. 超长前缀噪声 + 短问 ---
    noise = (
        "本人已阅读相关材料并知悉用人单位与劳动者应当依法订立劳动合同，"
        "保护劳动者的合法权益，构建和发展和谐稳定的劳动关系。"
    )
    for stem in (
        "试用期六个月合法吗",
        "劳动法第84行的内容是什么",
        "劳动法第一条的第三个字是啥",
        "竞业限制二年合法吗",
        "合同类型固定期限合法吗",
    ):
        for n in (1, 2, 3):
            add("超长前缀", f"{noise * n}请问{stem}")

    # --- G. 多问混域（一个能答一个不能）---
    for q in (
        "试用期六个月合法吗？加班费怎么算？",
        "劳动法第20行的内容是什么？辞退要赔多少？",
        "竞业限制二年合法吗？被辞退了怎么办？",
        "劳动法第一条有多少字？为什么要签书面合同？",
        "合同类型固定期限合法吗？年假合法吗？",
        "试用期半个月合法吗？试用期是否违法？",
        "劳动法第84行的内容是什么？第十九条是什么意思？",
        "试用期三个月合法吗？经济补偿怎么算？",
    ):
        add("混域双问", q)

    # pad
    n = 0
    while len(out) < TARGET + 40:
        n += 1
        i = 30 + (n % max(1, len(long_lines)))
        if long_lines:
            line_no, _ = long_lines[n % len(long_lines)]
            add("补齐长行", f"请完整复述劳动法第{line_no}行的内容是什么")
            add("补齐双问", f"劳动法第{line_no}行的内容是什么？试用期{1 + n % 6}个月合法吗？")
        if n > 400:
            break

    seen: set[str] = set()
    uniq: list[tuple[str, str]] = []
    for cat, q in out:
        if q in seen:
            continue
        seen.add(q)
        uniq.append((cat, q))
    if len(uniq) < TARGET:
        raise SystemExit(f"only {len(uniq)} prompts, need {TARGET}")
    return uniq[:TARGET]


def classify(q: str, rule: str, spoken: str) -> str:
    """Heuristic outcome label for long/multi stress."""
    r = rule or ""
    s = (spoken or "").strip()
    multi = ("？" in q[:-1]) or ("?" in q[:-1]) or ("，另外" in q) or ("还有" in q) or ("和" in q and q.count("合法吗") + q.count("是什么") >= 2)
    if r in {"REN2", "I11"} or s in {"我不知道", "我不了解这个信息"}:
        return "refuse"
    if r == "AMB1":
        return "ambig_ask"
    if not s:
        return "empty"
    # Multi-ask but only one clause answered (no second answer marker)
    if multi and r in {"D67", "D67.char", "D67.len", "D69", "D69.ask", "D21", "D36"}:
        # crude: answered something but unlikely both
        if s.count("见劳动法") >= 2 or (s.count("。") >= 2 and len(s) > 40):
            return "multi_ok"
        return "first_only"
    if r in {"D67", "D67.char", "D67.len", "D69", "D69.ask"}:
        return "single_ok"
    if r in {"D21", "D24", "D36", "D27", "D44"}:
        return "misfire"
    return "other"


def main() -> None:
    clear_system_cache()
    clear_judge_cache()
    clear_user_config_cache()
    load_user_dict.cache_clear()
    compile_articles(["--write", "--dir", str(LABOR)])
    load_user_dict.cache_clear()

    w = boot()
    load_user_memories(w)
    s = Session()
    prompts = build_prompts()
    assert len(prompts) == TARGET

    cases: list[dict] = []
    for cat, q in prompts:
        r = turn(w, s, q)
        spoken = (r.spoken or "").strip()
        kind = classify(q, r.rule or "", spoken)
        cases.append(
            {
                "n": len(cases) + 1,
                "cat": cat,
                "q": q[:180],
                "q_len": len(q),
                "rule": r.rule or "",
                "spoken": spoken[:220],
                "kind": kind,
                "ok": bool(r.ok) and bool(spoken),
            }
        )

    kinds = Counter(c["kind"] for c in cases)
    rules = Counter(c["rule"] for c in cases)
    cats = Counter(c["cat"] for c in cases)
    ok_n = sum(1 for c in cases if c["ok"])
    long_n = sum(1 for c in cases if c["q_len"] >= 80)
    avg_len = round(sum(c["q_len"] for c in cases) / len(cases), 1)

    report = {
        "total": len(cases),
        "ok": ok_n,
        "ok_rate": round(ok_n / len(cases), 4),
        "avg_q_len": avg_len,
        "long_q_ge80": long_n,
        "kinds": dict(kinds.most_common()),
        "rules": dict(rules.most_common()),
        "cats": dict(cats.most_common()),
        "cases": cases,
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# 长文本 + 多问同句压测（300）",
        "",
        f"- **样本数**: {len(cases)}",
        f"- **有答复**: {ok_n}/{len(cases)} ({report['ok_rate']*100:.1f}%)",
        f"- **问句均长**: {avg_len} 字；≥80 字: {long_n}",
        f"- **first_only（多问只答一条）**: {kinds.get('first_only', 0)}",
        f"- **multi_ok（像答了多条）**: {kinds.get('multi_ok', 0)}",
        f"- **single_ok**: {kinds.get('single_ok', 0)}",
        f"- **refuse**: {kinds.get('refuse', 0)}",
        f"- **misfire**: {kinds.get('misfire', 0)}",
        "",
        "> 当前 `ambig_mode first`：同句多问通常只命中第一条可解析规则，不拆成多答。",
        "",
        "## 结果种类",
        "",
        "| 种类 | 次数 |",
        "| --- | ---: |",
    ]
    for k, v in kinds.most_common():
        md.append(f"| `{k}` | {v} |")
    md += ["", "## 规则分布", "", "| 规则 | 次数 |", "| --- | ---: |"]
    for k, v in rules.most_common():
        md.append(f"| `{k or '(空)'}` | {v} |")
    md += ["", "## 类别", "", "| 类别 | 次数 |", "| --- | ---: |"]
    for k, v in cats.most_common():
        md.append(f"| {k} | {v} |")
    md += ["", "## 明细", "", "| # | 类 | 结果 | 规则 | 字数 | 问法 | 回答 |", "| ---: | --- | --- | --- | ---: | --- | --- |"]
    for c in cases:
        q = c["q"].replace("|", "\\|").replace("\n", " ")
        if len(q) > 48:
            q = q[:45] + "…"
        sp = c["spoken"].replace("|", "\\|").replace("\n", " ")
        if len(sp) > 40:
            sp = sp[:37] + "…"
        md.append(
            f"| {c['n']} | {c['cat']} | `{c['kind']}` | `{c['rule']}` | {c['q_len']} | {q} | {sp} |"
        )
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(
        f"ok={ok_n}/{len(cases)} avg_len={avg_len} "
        f"first_only={kinds.get('first_only', 0)} multi_ok={kinds.get('multi_ok', 0)} "
        f"single_ok={kinds.get('single_ok', 0)} refuse={kinds.get('refuse', 0)} misfire={kinds.get('misfire', 0)}"
    )
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
