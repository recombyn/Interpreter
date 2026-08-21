"""Gap / out-of-scope stress: ≥100 prompts that Para likely cannot implement correctly.

Goal: probe known boundaries — open calc, untaught topics, fuzzy units, why/how advice,
summarize/compare, no-pin deixis, poetry, nested syntax — and classify outcomes:
  refuse_ok | ask_ok | misfire | other
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from para.judge import clear_judge_cache
from para.kernel import boot
from para.knowledge.text_doc import load_user_memories
from para.preprocess import load_user_dict
from para.route import turn
from para.session import Session
from para.system_tm import clear_tm_caches
from para.user_config import clear_user_config_cache

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "runtime" / "qa_gap100_report.json"
OUT_MD = ROOT / "runtime" / "qa_gap100_report.md"
TARGET = 100

# Rules that usually mean "we answered as if we knew" on gap prompts → suspect
_MISFIRE_RULES = frozenset(
    {
        "D1",
        "D2",
        "D3",
        "D4",
        "D5",
        "D21",
        "D22",
        "D23",
        "D24",
        "D25",
        "D26",
        "D36",
        "D37",
        "D37y",
        "D40",
        "D40y",
        "D66",
        "D67",
        "D67.char",
        "D67.len",
        "D69",
    }
)

_REFUSE_RULES = frozenset({"REN2", "I11", ""})


def build_gap_prompts() -> list[tuple[str, str, str]]:
    """(category, question, expect_note)."""
    out: list[tuple[str, str, str]] = []

    def add(cat: str, q: str, note: str = "") -> None:
        out.append((cat, q, note))

    # --- 1. 开放量化 / 计算（无法条数值槽）---
    for q in (
        "辞退要赔多少",
        "辞退赔多少钱",
        "解雇赔偿金是多少",
        "经济补偿怎么算",
        "经济补偿N加1怎么算",
        "加班费怎么算",
        "加班费是多少",
        "双倍工资怎么算",
        "未签合同双倍工资赔多少",
        "年终奖要发多少",
        "最低工资是多少",
        "社保要交多少",
        "公积金比例是多少",
        "工伤赔多少",
        "医疗期工资怎么发",
        "产假工资怎么算",
        "陪产假几天工资怎么算",
        "高温津贴标准是多少",
        "夜班补贴法定多少",
        "迟到扣多少工资合法吗",
    ):
        add("开放量化", q, "无计算/无 limits 主题")

    # --- 2. 未建 D69 主题（看起来像合规问）---
    for topic in (
        "年假",
        "病假",
        "事假",
        "婚假",
        "产假",
        "陪产假",
        "丧假",
        "调休",
        "加班",
        "值班",
        "社保",
        "公积金",
        "竞业补偿",
        "违约金",
        "培训费",
        "服务期",
        "保密费",
        "实习期",
        "见习期",
        "劳务关系",
    ):
        add("未建主题判定", f"{topic}合法吗", "无对应 rule/limits")
        add("未建主题判定", f"{topic}三个月合法吗", "无对应 rule")

    # --- 3. 模糊 / 半量时长（解析缺口）---
    for q in (
        "试用期半个月合法吗",
        "合同一年试用期半个月合法吗",
        "试用期一个半月合法吗",
        "试用期两周合法吗",
        "试用期十五天合法吗",
        "试用期大约六个月合法吗",
        "试用期差不多半年合法吗",
        "试用期六个月左右合法吗",
        "竞业限制一年半合法吗",
        "竞业限制十八个月合法吗",
    ):
        add("模糊时长", q, "半/周/大约 未进 parse_duration")

    # --- 4. 因果 / 为什么 / 解释 ---
    for q in (
        "为什么试用期不能超过六个月",
        "为什么要签书面劳动合同",
        "为什么辞退要给补偿",
        "试用期的立法目的是什么",
        "劳动合同法保护谁",
        "这条法的含义是什么",
        "第十九条是什么意思",
        "请解释一下试用期规定",
        "总结一下劳动合同法",
        "劳动法讲了什么",
    ):
        add("因果概括", q, "无摘要/解释引擎")

    # --- 5. 建议 / 怎么办（行动指导）---
    for q in (
        "被辞退了怎么办",
        "公司不交社保怎么办",
        "不想签竞业限制怎么办",
        "试用期被辞退怎么维权",
        "应该去哪里仲裁",
        "劳动仲裁流程是什么",
        "起诉公司要准备什么材料",
        "我该不该签这个合同",
        "这份合同有没有坑",
        "帮我审查一下劳动合同",
    ):
        add("行动建议", q, "不做律师建议")

    # --- 6. 对比 / 多跳推理 ---
    for q in (
        "试用期和见习期有什么区别",
        "劳动合同和劳务合同有什么不同",
        "固定期限和无固定期限哪个更好",
        "竞业限制和保密协议是一回事吗",
        "经济补偿和经济赔偿有何区别",
        "第十九条和第二十条哪个更重要",
        "如果既超试用期又不交社保怎么处理",
        "先加班后辞退怎么算赔偿",
        "合同没签但干了三年算什么关系",
        "口头约定试用期一年算数吗",
    ):
        add("对比多跳", q, "无多跳/对比推理")

    # --- 7. 无钉指代 / 开放检索 ---
    for q in (
        "那呢",
        "这个合法吗",
        "上面说的呢",
        "还有吗",
        "详细说说",
        "继续",
        "为什么",
        "然后呢",
        "呢",
        "吗",
    ):
        add("无钉短问", q, "无实体钉不应开放检索")

    # --- 8. 诗句 / 闲聊 / 外域 ---
    for q in (
        "静夜思怎么赏析",
        "床前明月光什么意思",
        "今天天气怎么样",
        "你是谁",
        "讲个笑话",
        "用英语解释试用期",
        "What is probation period",
        "民法典第一千条是什么",
        "公司法注册资本最低多少",
        "刑法故意伤害怎么判",
    ):
        add("外域闲聊", q, "I11/外域/未教")

    # --- 9. 长难嵌套 / 倒装 ---
    for q in (
        "如果公司在我入职后第三个月以试用期不合格为由辞退且未说明理由是否合法",
        "在未约定书面试用期的情况下口头说试用三个月算不算数以及能否主张双倍工资",
        "被要求签竞业限制却不给补偿金的时候我还能不能要求继续履行合同",
        "用人单位违法约定的试用期已经履行的部分应当如何支付赔偿金按什么标准",
        "连续订立二次固定期限劳动合同后用人单位是否必须订立无固定期限合同有无例外",
    ):
        add("长难嵌套", q, "D层模板易误匹配")

    # dedupe
    seen: set[str] = set()
    uniq: list[tuple[str, str, str]] = []
    for cat, q, note in out:
        if q in seen:
            continue
        seen.add(q)
        uniq.append((cat, q, note))
    if len(uniq) < TARGET:
        raise SystemExit(f"only {len(uniq)} gap prompts, need ≥{TARGET}")
    return uniq


def classify(rule: str, spoken: str) -> str:
    r = rule or ""
    s = (spoken or "").strip()
    if r in {"D69.ask"} or s.startswith("请问"):
        return "ask_ok"
    if r in _REFUSE_RULES or s in {"我不知道", "我不了解这个信息", "好的"}:
        return "refuse_ok"
    if r == "I11":
        return "refuse_ok"
    if r in _MISFIRE_RULES and s:
        return "misfire"
    if not s:
        return "empty"
    return "other"


def main() -> None:
    clear_tm_caches()
    clear_judge_cache()
    clear_user_config_cache()
    load_user_dict.cache_clear()

    w = boot()
    load_user_memories(w)
    # Fresh session: no pins — stress open/gap asks
    s = Session()
    prompts = build_gap_prompts()

    cases: list[dict] = []
    for cat, q, note in prompts:
        r = turn(w, s, q)
        spoken = (r.spoken or "").strip()
        kind = classify(r.rule or "", spoken)
        cases.append(
            {
                "n": len(cases) + 1,
                "cat": cat,
                "q": q,
                "note": note,
                "rule": r.rule or "",
                "spoken": spoken[:220],
                "kind": kind,
            }
        )

    kinds = Counter(c["kind"] for c in cases)
    rules = Counter(c["rule"] for c in cases)
    cats = Counter(c["cat"] for c in cases)
    misfires = [c for c in cases if c["kind"] == "misfire"]

    report = {
        "total": len(cases),
        "kinds": dict(kinds.most_common()),
        "rules": dict(rules.most_common()),
        "cats": dict(cats.most_common()),
        "misfire_n": len(misfires),
        "misfire_rate": round(len(misfires) / len(cases), 4),
        "cases": cases,
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# 未覆盖 / 难实现场景压测（≥100）",
        "",
        f"- **样本数**: {len(cases)}",
        f"- **误匹配 misfire**: {len(misfires)}/{len(cases)} ({report['misfire_rate']*100:.1f}%)",
        f"- **正确拒绝 refuse_ok**: {kinds.get('refuse_ok', 0)}",
        f"- **追问 ask_ok**: {kinds.get('ask_ok', 0)}",
        f"- **其他 other**: {kinds.get('other', 0)}",
        "",
        "> 这些问法故意踩能力边界：开放计算、未建主题、模糊时长、因果建议、对比多跳、无钉短问、外域、长难句。",
        "> `misfire` = 仍落到 D21/D36/D67/D69 等并给出“像有答案”的回复（值得修）。",
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

    if misfires:
        md += ["", "## 误匹配明细", "", "| # | 类 | 规则 | 问法 | 回答 |", "| ---: | --- | --- | --- | --- |"]
        for c in misfires:
            q = c["q"].replace("|", "\\|")
            sp = c["spoken"].replace("|", "\\|").replace("\n", " ")
            if len(sp) > 60:
                sp = sp[:57] + "…"
            md.append(f"| {c['n']} | {c['cat']} | `{c['rule']}` | {q} | {sp} |")

    md += ["", "## 全量明细", "", "| # | 类 | 结果 | 规则 | 问法 | 回答 |", "| ---: | --- | --- | --- | --- | --- |"]
    for c in cases:
        q = c["q"].replace("|", "\\|")
        sp = c["spoken"].replace("|", "\\|").replace("\n", " ")
        if len(sp) > 48:
            sp = sp[:45] + "…"
        md.append(
            f"| {c['n']} | {c['cat']} | `{c['kind']}` | `{c['rule']}` | {q} | {sp} |"
        )
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(
        f"total={len(cases)} misfire={len(misfires)} "
        f"refuse={kinds.get('refuse_ok', 0)} ask={kinds.get('ask_ok', 0)} other={kinds.get('other', 0)}"
    )
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
