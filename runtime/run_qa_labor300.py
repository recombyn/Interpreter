"""Labor-law focused Q&A ≥300 prompts across knowledge points → report."""

from __future__ import annotations

import json
import re
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
OUT_JSON = ROOT / "runtime" / "qa_labor300_report.json"
OUT_MD = ROOT / "runtime" / "qa_labor300_report.md"

CN = "零一二三四五六七八九十"


def cn_num(n: int) -> str:
    if n <= 10:
        return "十" if n == 10 else CN[n]
    if n < 20:
        return "十" + CN[n - 10]
    if n % 10 == 0:
        return CN[n // 10] + "十"
    return CN[n // 10] + "十" + CN[n % 10]


def build_labor_prompts() -> list[tuple[str, str]]:
    """(category, question) — labor knowledge points only."""
    out: list[tuple[str, str]] = []

    def add(cat: str, q: str) -> None:
        out.append((cat, q))

    text_path = LABOR / "劳动法.text"
    lines = text_path.read_text(encoding="utf-8").splitlines() if text_path.is_file() else []
    articles = extract_article_lines(text_path) if text_path.is_file() else []

    # --- A. 按行正文 ---
    for n in list(range(1, 31)) + [40, 50, 60, 70, 80, 84, 90, 100, 101, 120, 140, 200, 250, 280, 300, 320]:
        if 1 <= n <= len(lines):
            add("行正文", f"劳动法第{n}行的内容是什么")

    # --- B. 按条正文（依赖 article.maps.tm）---
    for no, _line in articles[:60]:
        add("条正文", f"劳动法第{no}条的内容是什么")

    # --- C. 第N个字 / 字数（知识点：条文字符）---
    # 第一条 → map → 行；第3字应为「完」（为了完善…）
    for no, line_no in articles[:40]:
        add("条字符", f"劳动法第{no}条的第一个字是什么")
        add("条字符", f"劳动法第{no}条的第三个字是啥")
        add("条字符", f"劳动法第{no}条有多少字")
        add("行字符", f"劳动法第{line_no}行的第2个字是什么")

    # 显式用户举例
    add("条字符", "劳动法第一条的第三个字是啥")
    add("条字符", "劳动法第一条的第一个字是什么")
    add("条字符", "劳动法第一条有多少字")

    # --- D. 试用期阈值 / 多档 ---
    for n in range(1, 13):
        add("试用期判定", f"试用期{cn_num(n)}个月合法吗")
        add("试用期判定", f"试用期{n}个月合规吗")
    for c in ("三个月", "半年", "一年", "两年", "三年", "四年"):
        for p in ("一个月", "二个月", "三个月", "六个月"):
            add("试用期多档", f"合同{c}试用期{p}合法吗")

    add("试用期追问", "试用期合法吗")
    add("试用期合取", "试用期六个月严格合法吗")
    add("试用期合取", "试用期七个月严格合法吗")

    # --- E. 竞业 / 合同类型 ---
    for n in range(1, 5):
        add("竞业", f"竞业限制{cn_num(n)}年合法吗")
        add("竞业", f"竞业限制{n}年可以吗")
    add("竞业", "竞业限制合法吗")
    for v in ("固定期限", "无固定期限", "以完成一定工作任务为期限", "口头协议"):
        add("合同类型", f"合同类型{v}合法吗")
    add("合同类型", "合同类型合法吗")

    # --- F. 文档级 / 主题 ---
    add("文档", "劳动法的内容是什么")
    add("文档", "劳动合同法的内容是什么")

    # --- G. 短问 / 指代（先钉一行）---
    add("行正文", "劳动法第84行的内容是什么")
    add("短问", "那呢")
    add("短问", "呢")

    # --- H. 应失败 / 边界知识点 ---
    add("边界", "劳动法第九百条的内容是什么")
    add("边界", "劳动法第9999行的内容是什么")
    add("边界", "劳动法第一条的第999个字是什么")
    add("边界", "加班费怎么算")
    add("边界", "辞退要赔多少")
    add("边界", "试用期是否违法")

    # pad to ≥300 with systematic line+char combos
    n = 1
    while len(out) < 320:
        line_no = 20 + (n % 100)
        if line_no <= len(lines):
            add("补齐字符", f"劳动法第{line_no}行的第{1 + n % 5}个字是什么")
            add("补齐正文", f"劳动法第{line_no}行的内容是什么")
        n += 1
        if n > 500:
            break

    # dedupe preserve order
    seen: set[str] = set()
    uniq: list[tuple[str, str]] = []
    for cat, q in out:
        if q in seen:
            continue
        seen.add(q)
        uniq.append((cat, q))
    return uniq[:320] if len(uniq) >= 300 else uniq


def expected_char(entity_line_content: str, idx: int) -> str | None:
    return None  # unused; spot-check uses live turn


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
    prompts = build_labor_prompts()
    assert len(prompts) >= 300, len(prompts)

    cases: list[dict] = []
    for cat, q in prompts:
        r = turn(w, s, q)
        spoken = (r.spoken or "").strip()
        cases.append(
            {
                "n": len(cases) + 1,
                "cat": cat,
                "q": q,
                "rule": r.rule or "",
                "spoken": spoken[:220],
                "ok": bool(r.ok) and bool(spoken),
            }
        )

    # spot-check 第一条第3字
    s2 = Session()
    spot_r = turn(w, s2, "劳动法第一条的第三个字是啥")

    rules = Counter(c["rule"] for c in cases)
    cats = Counter(c["cat"] for c in cases)
    ok_n = sum(1 for c in cases if c["ok"])
    report = {
        "total": len(cases),
        "ok": ok_n,
        "ok_rate": round(ok_n / len(cases), 4),
        "spot_第一条第3字": {
            "q": "劳动法第一条的第三个字是啥",
            "rule": spot_r.rule,
            "spoken": spot_r.spoken,
            "expect": "完",
            "pass": (spot_r.spoken or "") == "完",
        },
        "rules": dict(rules.most_common()),
        "cats": dict(cats.most_common()),
        "cases": cases,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# 劳动法专项 300+ 问法测试报告",
        "",
        f"- **样本数**: {len(cases)}",
        f"- **有答复**: {ok_n}/{len(cases)} ({report['ok_rate']*100:.1f}%)",
        f"- **抽检** `劳动法第一条的第三个字是啥` → `{spot_r.spoken}` "
        f"(期望`完`, {'通过' if report['spot_第一条第3字']['pass'] else '未通过'})",
        "",
        "## 规则分布",
        "",
        "| 规则 | 次数 |",
        "| --- | ---: |",
    ]
    for k, v in rules.most_common():
        md.append(f"| `{k or '(空)'}` | {v} |")
    md += ["", "## 类别分布", "", "| 类别 | 次数 |", "| --- | ---: |"]
    for k, v in cats.most_common():
        md.append(f"| {k} | {v} |")
    md += ["", "## 明细", "", "| # | 类 | 规则 | 问法 | 回答 |", "| ---: | --- | --- | --- | --- |"]
    for c in cases:
        q = c["q"].replace("|", "\\|")
        sp = c["spoken"].replace("|", "\\|").replace("\n", " ")
        if len(sp) > 72:
            sp = sp[:69] + "…"
        md.append(f"| {c['n']} | {c['cat']} | `{c['rule']}` | {q} | {sp} |")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"ok={ok_n}/{len(cases)} spot={spot_r.rule}:{spot_r.spoken}")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
