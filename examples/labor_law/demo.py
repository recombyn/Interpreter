#!/usr/bin/env python3
"""Labor-law case: plug-in Para + user-owned knowledge.

Run from repo root:
  set PYTHONPATH=src
  python examples/labor_law/demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from para import Para  # noqa: E402
from para.paths import USER_DIR  # noqa: E402

STEPS = [
    # --- 单问 ---
    ("query", "员工是什么", "概念图：isa"),
    ("query", "公司有员工吗", "概念图：has polar"),
    ("query", "劳动法的内容是什么", "概念图：content"),
    ("query", "试用期六个月合法吗", "D69 条件档：无合同期限附带分档"),
    ("query", "什么情况下试用期六个月不违法", "D69 explain 分档"),
    ("query", "试用期六个月违法吗", "D69 违法吗 → 不违法+条件"),
    ("query", "试用期七个月合法吗", "D69 超绝对上限 → 否定"),
    ("query", "试用期合法吗", "D69.ask 缺时长"),
    # --- 长句（前缀冗余，仍抽出判定）---
    (
        "query",
        "请问一下我们公司约定试用期六个月合法吗",
        "长句：口语前缀 + 条件档判定",
    ),
    (
        "query",
        "合同一年试用期二个月合法吗",
        "长句：合同期限 + 试用期多档（二元合法）",
    ),
    (
        "query",
        "劳动法第84行的内容是什么",
        "长句/条文：D67 行内容",
    ),
    # --- 一次多问（MULTI）---
    (
        "query",
        "试用期六个月合法吗竞业限制二年合法吗",
        "多问：两个 D69，spoken 用；拼接",
    ),
    (
        "query",
        "劳动法第84行的内容是什么试用期六个月合法吗",
        "多问：D67 条文 + D69 判定",
    ),
    (
        "query",
        "员工入职签一年合同试用期两个月合法吗另外竞业限制两年合法吗",
        "多问：长叙述里两个判定（另外）",
    ),
    # --- 写 / 拒 ---
    ("write", "教兼职是工作", "主机写入新事实"),
    ("query", "兼职是什么", "写后可查"),
    ("query", "火星上有独角兽吗", "未教 → refuse，不编造"),
]


def _brief(out) -> dict:
    return {
        "ok": out.ok,
        "status": out.status,
        "rule": out.rule,
        "spoken": out.spoken,
        "miss": out.miss,
        "facts_added": [f.to_dict() for f in out.facts_added],
        "evidence": [e.to_dict() for e in out.evidence],
        "warn": out.warn,
    }


def main() -> int:
    eng = Para(remember=False, load_user_docs=True, user_dir=USER_DIR)
    print("=== Para · 劳动法案例 ===")
    print(f"user_dir = {eng.user_dir}")
    print(f"loaded memory files: {len(eng.user_docs)}")
    print()
    for kind, text, note in STEPS:
        write = True if kind == "write" else False
        out = eng.decode(text, write=write)
        print(f"# {note}")
        print(f"> {text}")
        print(json.dumps(_brief(out), ensure_ascii=False))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
