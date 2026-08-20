"""One-shot: 40 Q&A smoke against user knowledge + D69."""

from __future__ import annotations

import json
from pathlib import Path

from cni.judge import clear_judge_cache
from cni.kernel import boot
from cni.knowledge.text_doc import load_user_memories
from cni.route import hear, turn
from cni.session import Session
from cni.user_config import clear_user_config_cache

OUT = Path("runtime/qa40_report.json")


def main() -> None:
    clear_judge_cache()
    clear_user_config_cache()
    w = boot()
    load_user_memories(w)
    s = Session()
    cases: list[dict] = []

    def add(cat: str, q: str, mode: str = "ask") -> None:
        r = hear(w, s, q) if mode == "teach" else turn(w, s, q)
        cases.append(
            {
                "n": len(cases) + 1,
                "cat": cat,
                "q": q,
                "mode": mode,
                "rule": r.rule or "",
                "spoken": (r.spoken or "")[:160],
                "ok": bool(r.ok),
            }
        )

    # 1–2 teach
    add("教学", "电脑是机器", "teach")
    add("教学", "小明打小红", "teach")
    # 3–5 basic
    add("是非", "电脑是机器吗")
    add("内容问", "电脑是什么")
    add("未知", "火星人是什么")
    # 6–9 threshold
    add("阈值", "试用期六个月合法吗")
    add("阈值", "试用期七个月合法吗")
    add("阈值", "试用期6个月合法吗")
    add("阈值", "试用期一个月合法吗")
    # 10–14 tiers
    add("多档", "合同一年试用期二个月合法吗")
    add("多档", "试用期三个月合同一年合法吗")
    add("多档", "合同三个月试用期一个月合法吗")
    add("多档", "合同两年试用期二个月合法吗")
    add("多档", "合同四年试用期六个月合法吗")
    # 15–16 ask+resume
    add("追问", "试用期合法吗")
    add("追问", "六个月")
    # 17–19 竞业
    add("竞业", "竞业限制二年合法吗")
    add("竞业", "竞业限制三年合法吗")
    add("竞业", "竞业限制合法吗")
    # 20–23 enum
    add("枚举", "合同类型固定期限合法吗")
    add("枚举", "合同类型无固定期限合法吗")
    add("枚举", "合同类型口头协议合法吗")
    add("枚举", "合同类型合法吗")
    # 24 conjunction
    add("合取", "试用期六个月严格合法吗")
    # 25 MEM4
    add("短问", "合法吗")
    # 26–27 content
    add("正文", "劳动法第84行的内容是什么")
    add("正文", "劳动法的内容是什么")
    # 28–31 more
    add("阈值", "试用期十二个月合法吗")
    add("阈值", "试用期可以吗")
    add("追问", "两个月")
    add("社交", "你好")
    # 32–34
    add("社交", "谢谢")
    add("教学", "静夜思的内容是床前明月光", "teach")
    add("正文", "静夜思的内容是什么")
    # 35–37
    add("教学", "下雨了，我不出门", "teach")
    add("是非", "小明打小红吗")
    add("未知", "加班费怎么算")
    # 38–40
    add("阈值", "试用期五个月合法吗")
    add("多档", "合同半年试用期一个月合法吗")
    add("竞业", "竞业限制一年合法吗")

    assert len(cases) == 40
    rules: dict[str, int] = {}
    for c in cases:
        rules[c["rule"]] = rules.get(c["rule"], 0) + 1
    report = {
        "total": 40,
        "ok": sum(1 for c in cases if c["ok"]),
        "rules": rules,
        "cases": cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ok={report['ok']}/40 rules={rules}")
    for c in cases:
        print(f"{c['n']:02d}\t{c['cat']}\t{c['rule']}\t{c['q']}\t→\t{c['spoken']}")


if __name__ == "__main__":
    main()
