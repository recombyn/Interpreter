"""Batch Q&A: 300 prompts → JSON + Markdown report."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from cni.judge import clear_judge_cache
from cni.kernel import boot
from cni.knowledge.text_doc import load_user_memories
from cni.route import hear, turn
from cni.session import Session
from cni.user_config import clear_user_config_cache

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "runtime" / "qa300_report.json"
OUT_MD = ROOT / "runtime" / "qa300_report.md"

CN = "零一二三四五六七八九十"


def cn_num(n: int) -> str:
    if n <= 10:
        return "十" if n == 10 else CN[n]
    if n < 20:
        return "十" + CN[n - 10]
    if n % 10 == 0:
        return CN[n // 10] + "十"
    return CN[n // 10] + "十" + CN[n % 10]


def build_prompts() -> list[tuple[str, str, str]]:
    """Return list of (cat, mode, text). mode: ask|teach."""
    out: list[tuple[str, str, str]] = []

    def add(cat: str, text: str, mode: str = "ask") -> None:
        out.append((cat, mode, text))

    # --- seed teaches ---
    add("教学", "电脑是机器", "teach")
    add("教学", "小明打小红", "teach")
    add("教学", "猫是动物", "teach")
    add("教学", "张三是员工", "teach")
    add("教学", "静夜思的内容是床前明月光", "teach")
    add("教学", "加班费的内容是不低于工资百分之一百五十", "teach")
    add("教学", "下雨了，我不出门", "teach")

    # --- basic polar / what ---
    for q in (
        "电脑是机器吗",
        "猫是动物吗",
        "张三是员工吗",
        "电脑是动物吗",
        "小明打小红吗",
        "电脑是什么",
        "猫是什么",
        "张三是什么",
        "火星人是什么",
        "独角兽是什么",
    ):
        add("基础", q)

    # --- 试用期 absolute months 1..15 × triggers ---
    for n in range(1, 16):
        for trig in ("合法吗", "合规吗"):
            add("阈值", f"试用期{cn_num(n)}个月{trig}")
            add("阈值", f"试用期{n}个月{trig}")

    # --- digit/cn mix edge ---
    for q in (
        "试用期六个月可以吗",
        "试用期6个月可以吗",
        "试用期十二个月合法吗",
        "试用期0个月合法吗",
    ):
        add("阈值", q)

    # --- multi-tier contract × probation ---
    contracts = [
        ("三个月", 1),
        ("半年", 1),
        ("一年", 2),
        ("两年", 2),
        ("三年", 2),
        ("四年", 6),
        ("五年", 6),
    ]
    probs = ["一个月", "二个月", "三个月", "六个月", "1个月", "2个月", "3个月", "6个月"]
    for c, _ in contracts:
        for p in probs:
            add("多档", f"合同{c}试用期{p}合法吗")
            add("多档", f"试用期{p}合同{c}合法吗")

    # --- 竞业 ---
    for n in range(1, 5):
        add("竞业", f"竞业限制{cn_num(n)}年合法吗")
        add("竞业", f"竞业限制{n}年合法吗")
        add("竞业", f"竞业限制{cn_num(n)}年合规吗")
    add("竞业", "竞业限制合法吗")
    add("竞业", "竞业限制可以吗")

    # --- enum ---
    for v in (
        "固定期限",
        "无固定期限",
        "以完成一定工作任务为期限",
        "口头协议",
        "临时工",
        "实习协议",
    ):
        add("枚举", f"合同类型{v}合法吗")
        add("枚举", f"合同类型{v}可以吗")
    add("枚举", "合同类型合法吗")

    # --- conjunction ---
    for n in (1, 3, 6, 7):
        add("合取", f"试用期{cn_num(n)}个月严格合法吗")

    # --- ask slots (interleaved with resumes later via runner) ---
    for q in (
        "试用期合法吗",
        "试用期合规吗",
        "试用期可以吗",
        "竞业限制合法吗",
        "合同类型合法吗",
    ):
        add("追问入口", q)

    # --- D67 lines ---
    for n in list(range(1, 21)) + [80, 84, 101, 123, 140, 279, 284, 323]:
        add("正文", f"劳动法第{n}行的内容是什么")
    add("正文", "劳动法的内容是什么")
    add("正文", "静夜思的内容是什么")
    add("正文", "加班费的内容是什么")
    add("正文", "不存在文档第1行的内容是什么")

    # --- MEM4-ish short (need focus; runner will pin first) ---
    for q in ("合法吗", "合规吗", "可以吗", "那呢", "呢"):
        add("短问", q)

    # --- unknown / open ---
    for q in (
        "加班费怎么算",
        "试用期是否违法",
        "辞退要赔多少",
        "社保怎么交",
        "年假有几天",
        "最低工资是多少",
        "今天天气怎么样",
        "帮我写诗",
        "什么是量子力学",
        "公司可以不签合同吗",
    ):
        add("未知", q)

    # --- social ---
    for q in ("你好", "您好", "谢谢", "再见", "嗯", "哦"):
        add("社交", q)

    # --- poetry I11 ---
    for q in ("床前明月光", "床前明月光，疑是地上霜", "学而时习之"):
        add("诗词", q)

    # --- more teaches mid-stream ---
    add("教学", "北京是城市", "teach")
    add("教学", "苹果是水果", "teach")
    add("基础", "北京是城市吗")
    add("基础", "苹果是水果吗")
    add("基础", "北京是水果吗")

    # --- pad / trim to exactly 300 ---
    i = 0
    while len(out) < 300:
        i += 1
        add("补齐", f"试用期{i}个月合法吗")
    return out[:300]


def main() -> None:
    clear_judge_cache()
    clear_user_config_cache()
    w = boot()
    load_user_memories(w)
    s = Session()
    prompts = build_prompts()
    assert len(prompts) == 300

    cases: list[dict] = []
    empty = 0
    for cat, mode, text in prompts:
        r = hear(w, s, text) if mode == "teach" else turn(w, s, text)
        spoken = (r.spoken or "").strip()
        if not spoken:
            empty += 1
        cases.append(
            {
                "n": len(cases) + 1,
                "cat": cat,
                "mode": mode,
                "q": text,
                "rule": r.rule or "",
                "spoken": spoken[:200],
                "ok": bool(r.ok) and bool(spoken),
            }
        )

    rules = Counter(c["rule"] for c in cases)
    cats = Counter(c["cat"] for c in cases)
    ok_n = sum(1 for c in cases if c["ok"])
    report = {
        "total": 300,
        "ok": ok_n,
        "empty_spoken": empty,
        "ok_rate": round(ok_n / 300, 4),
        "rules": dict(rules.most_common()),
        "cats": dict(cats.most_common()),
        "cases": cases,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# CNI 300 问法测试报告",
        "",
        f"- **有答复**: {ok_n}/300 ({report['ok_rate']*100:.1f}%)",
        f"- **空答复**: {empty}",
        "",
        "## 规则分布",
        "",
        "| 规则 | 次数 |",
        "| --- | ---: |",
    ]
    for k, v in rules.most_common():
        lines.append(f"| `{k or '(空)'}` | {v} |")
    lines += ["", "## 类别分布", "", "| 类别 | 次数 |", "| --- | ---: |"]
    for k, v in cats.most_common():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## 明细", "", "| # | 类 | 规则 | 问法 | 回答 |", "| ---: | --- | --- | --- | --- |"]
    for c in cases:
        q = c["q"].replace("|", "\\|")
        sp = c["spoken"].replace("|", "\\|").replace("\n", " ")
        if len(sp) > 80:
            sp = sp[:77] + "…"
        lines.append(f"| {c['n']} | {c['cat']} | `{c['rule']}` | {q} | {sp} |")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"ok={ok_n}/300 empty={empty}")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print("rules:", dict(rules.most_common(12)))


if __name__ == "__main__":
    main()
