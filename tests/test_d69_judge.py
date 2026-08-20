"""D69: tiers, cite, conjunction, compile, ask-slot."""

from __future__ import annotations

from cni.decode import effects as fx
from cni.judge import (
    clear_judge_cache,
    compare,
    match_judge,
    parse_duration,
    parse_cn_int,
    pick_tier_limit,
)
from cni.kernel import boot
from cni.knowledge.text_doc import load_user_memories
from cni.route import turn
from cni.session import Session
from cni.tools.compile_limits import extract_from_text, merge_limits, scan_user_docs
from cni.user_config import clear_user_config_cache


def _yesish(spoken: str) -> bool:
    return spoken.startswith(("是的", "true", "是")) or spoken in {"是的", "true", "是"}


def _noish(spoken: str) -> bool:
    return spoken.startswith(("不是", "false", "否")) or spoken in {"不是", "false", "否"}


def test_parse_duration_cn_and_digit():
    assert parse_cn_int("六") == 6
    d = parse_duration("六个月")
    assert d is not None and d.value == 6 and d.unit == "月"


def test_compare_ops():
    assert compare("le", 6, 6)
    assert not compare("le", 7, 6)


def test_match_judge_试用期():
    clear_judge_cache()
    hit = match_judge("试用期六个月合法吗")
    assert hit is not None
    assert hit.rule.topic == "试用期"
    assert hit.duration is not None and hit.duration.value == 6


def test_d69_yes_within_limit_with_cite():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "试用期六个月合法吗")
    assert got.rule == "D69"
    assert _yesish(got.spoken)
    assert "劳动法第" in got.spoken or "见" in got.spoken


def test_d69_no_over_limit():
    clear_judge_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "试用期七个月合法吗")
    assert got.rule == "D69"
    assert _noish(got.spoken)


def test_d69_ren2_without_limit_fact():
    clear_judge_cache()
    w2, s2 = boot(), Session()
    got = turn(w2, s2, "试用期六个月合法吗")
    assert got.rule == "REN2"


def test_d69_teach_limit_then_judge():
    clear_judge_cache()
    w, s = boot(), Session()
    fx.write_limit(w, "试用期", "6", unit="月")
    got = turn(w, s, "试用期6个月合法吗")
    assert got.rule == "D69"
    assert _yesish(got.spoken)


def test_d69_ask_then_resume():
    clear_judge_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    ask = turn(w, s, "试用期合法吗")
    assert ask.rule == "D69.ask"
    got = turn(w, s, "六个月")
    assert got.rule == "D69"
    assert _yesish(got.spoken)


def test_d69_enum_合同类型():
    clear_judge_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    assert _yesish(turn(w, s, "合同类型固定期限合法吗").spoken)
    assert _noish(turn(w, s, "合同类型口头协议合法吗").spoken)


def test_d69_竞业限制_from_compile():
    clear_judge_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    assert _yesish(turn(w, s, "竞业限制二年合法吗").spoken)
    assert _noish(turn(w, s, "竞业限制三年合法吗").spoken)


def test_mem4_合法吗_to_judge_ask():
    clear_judge_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    turn(w, s, "试用期六个月合法吗")
    got = turn(w, s, "合法吗")
    assert got.rule == "D69.ask"


def test_tier_pick():
    clear_judge_cache()
    assert pick_tier_limit("试用期", 6) == 1   # [3,12)
    assert pick_tier_limit("试用期", 24) == 2  # [12,36)
    assert pick_tier_limit("试用期", 48) == 6  # [36,+∞)
    assert pick_tier_limit("试用期", 2) == 0   # [0,3)


def test_d69_tier_合同一年试用期二个月():
    clear_judge_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    # 合同一年 → 档上限 2 月；试用期 2 月 → 合法
    ok = turn(w, s, "合同一年试用期二个月合法吗")
    assert ok.rule == "D69"
    assert _yesish(ok.spoken)
    # 试用期三个月超档
    bad = turn(w, s, "试用期三个月合同一年合法吗")
    assert bad.rule == "D69"
    assert _noish(bad.spoken)


def test_d69_conjunction_严格合法吗():
    clear_judge_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    # limits 已有 of(书面约定, 试用期, 是)
    got = turn(w, s, "试用期六个月严格合法吗")
    assert got.rule == "D69"
    assert _yesish(got.spoken)


def test_d69_conjunction_ask_when_missing():
    clear_judge_cache()
    w, s = boot(), Session()
    # no user memories → no 书面约定 fact
    got = turn(w, s, "试用期六个月严格合法吗")
    # no 上限 either → could be need_also ask first (also checked before limit)
    assert got.rule in {"D69.ask", "REN2"}
    if got.rule == "D69.ask":
        assert "书面" in got.spoken
        fx.write_limit(w, "试用期", "6", unit="月")
        # affirm without fact → waive also
        s.pending_judge_topic = "试用期"
        s.pending_judge_text = "试用期六个月严格合法吗"
        ans = turn(w, s, "是")
        assert ans.rule == "D69"
        assert _yesish(ans.spoken)


def test_compile_extract_试用期_max():
    text = (
        "劳动合同期限三个月以上不满一年的，试用期不得超过一个月；"
        "三年以上固定期限和无固定期限的劳动合同，试用期不得超过六个月。"
    )
    hits = extract_from_text(text, stem="劳动法", line_no=84, topics=["试用期"])
    merged = merge_limits(hits)
    assert merged[("试用期", "上限")].value == 6


def test_compile_scan_user_docs():
    clear_judge_cache()
    assert "试用期" in {h.topic for h in scan_user_docs()}
