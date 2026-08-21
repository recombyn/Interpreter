"""D69: tiers, cite, conjunction, compile, ask-slot."""

from __future__ import annotations

from para.decode import effects as fx
from para.judge import (
    clear_judge_cache,
    compare,
    match_judge,
    parse_duration,
    parse_cn_int,
    pick_tier_limit,
)
from para.kernel import boot
from para.knowledge.text_doc import load_user_memories
from para.route import turn
from para.session import Session
from para.tools.compile_limits import extract_from_text, merge_limits, scan_user_docs
from para.user_config import clear_user_config_cache


def _yesish(spoken: str) -> bool:
    s = spoken or ""
    if any(x in s for x in ("不合法", "不合规", "不可以", "不是")):
        return False
    return any(x in s for x in ("合法", "合规", "可以", "是的")) or s.startswith(
        ("true", "是", "要")
    )


def _noish(spoken: str) -> bool:
    s = spoken or ""
    return any(x in s for x in ("不合法", "不合规", "不可以", "不是", "false", "否"))


def test_parse_duration_cn_and_digit():
    assert parse_cn_int("六") == 6
    d = parse_duration("六个月")
    assert d is not None and d.value == 6 and d.unit == "月"
    half = parse_duration("半个月")
    assert half is not None and half.value == 0.5 and half.unit == "月"
    one_half = parse_duration("一个半月")
    assert one_half is not None and one_half.value == 1.5 and one_half.unit == "月"


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
    # Must attach tier conditions — not bare absolute 上限 yes
    assert any(x in got.spoken for x in ("三年", "不得超过", "情况", "不满"))
    assert "劳动法第" in got.spoken or "见" in got.spoken


def test_d69_conditional_explain_and_违法():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    expl = turn(w, s, "什么情况下试用期六个月不违法")
    assert expl.rule == "D69"
    assert any(x in expl.spoken for x in ("三年", "不得超过", "情况"))
    illegal_q = turn(w, s, "试用期六个月违法吗")
    assert illegal_q.rule == "D69"
    assert "不违法" in illegal_q.spoken or "合法" in illegal_q.spoken
    assert any(x in illegal_q.spoken for x in ("三年", "不得超过", "情况"))


def test_d69_bare_duration_with_focus():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    turn(w, s, "试用期合法吗")  # pin + pending
    got = turn(w, s, "六个月不违法")
    assert got.rule == "D69"
    assert any(x in got.spoken for x in ("三年", "不得超过", "情况", "合法", "不违法"))


def test_d69_半个月_合法():
    """半个月 ≤ some tiers → conditional 合法 narrative."""
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "试用期半个月合法吗")
    assert got.rule == "D69"
    assert _yesish(got.spoken)


def test_polar_form_override_是否(tmp_path, monkeypatch):
    """用户 form 可把谓词改成 是/否（short 模式）。"""
    import para.render.forms as F
    from para.paths import set_user_dir

    (tmp_path / "form.tm").write_text(
        "out polar.mode short\nout polar.合法.yes 是\nout polar.合法.no 否\n",
        encoding="utf-8",
    )
    set_user_dir(tmp_path)
    F.clear_forms_cache()
    try:
        assert F.polar_spoken("试用期六个月合法吗", True, trigger="合法吗") == "是"
        assert F.polar_spoken("试用期七个月合法吗", False, trigger="合法吗") == "否"
    finally:
        set_user_dir(None)
        F.clear_forms_cache()


def test_polar_clause_human_order():
    from para.render.forms import clear_forms_cache, polar_spoken

    clear_forms_cache()
    assert (
        polar_spoken("试用期半个月合法吗", True, trigger="合法吗")
        == "试用期半个月合法"
    )
    assert (
        polar_spoken("试用期七个月合法吗", False, trigger="合法吗")
        == "试用期七个月不合法"
    )


def test_multi_fire_two_d69():
    """一句里两个判定子句 → 各答一次，不是问号硬切。"""
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "试用期六个月合法吗竞业限制二年合法吗")
    assert "合法" in got.spoken and "；" in got.spoken
    assert "D69" in (got.rule or "")


def test_multi_fire_d67_and_d69():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "劳动法第84行的内容是什么试用期六个月合法吗")
    assert "；" in got.spoken
    assert "合法" in got.spoken


def test_long_prefix_peel_d67():
    clear_judge_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    prefix = "本人已阅读材料并知悉应当依法订立劳动合同。"
    got = turn(w, s, prefix + "劳动法第84行的内容是什么")
    assert got.rule == "D67"
    assert got.spoken and got.spoken != "我不知道"


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
    # 竞业限制 has no tiers; without limits.tm abs → REN2
    got = turn(w2, s2, "竞业限制二年合法吗")
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
    assert any(x in got.spoken for x in ("三年", "不得超过", "情况"))


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


def test_mem4_preserves_合规吗_trigger():
    clear_judge_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    turn(w, s, "试用期六个月合法吗")
    expanded = s.expand_short_ask("合规吗")
    assert expanded == "试用期合规吗"


def test_mem4_preserves_合规吗_trigger():
    clear_judge_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    turn(w, s, "试用期六个月合法吗")
    expanded = s.expand_short_ask("合规吗")
    assert expanded == "试用期合规吗"


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


def test_repair_keeps_合不合法():
    from para.repair import repair

    known = {"试用期"}
    assert "合不合法" in repair("试用期六个月合不合法", set(), known)


def test_合不合法_routes_d69():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "试用期六个月合不合法")
    assert got.rule == "D69"
    assert _yesish(got.spoken)


def test_enum_or_两种合同类型():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "固定期限或无固定期限合同类型合法吗")
    assert got.rule == "D69"
    assert _yesish(got.spoken)


def test_未书面约定_严格合法_no():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "试用期六个月且未书面约定严格合法吗")
    assert got.rule == "D69"
    assert _noish(got.spoken)
    assert "不合法" in got.spoken or "不是" in got.spoken


def test_都合法吗_竞业且试用期():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "竞业限制二年且试用期六个月都合法吗")
    assert got.rule == "D69"
    assert "都合法" in got.spoken


def test_p2_没有书面约定_prefix_soft_合法吗():
    """Prefix 没有书面约定 on soft 合法吗 → not_also (same topic has strict also)."""
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "没有书面约定试用期六个月合法吗")
    assert got.rule == "D69"
    assert _noish(got.spoken)


def test_p2_劳务派遣_miss_not_试用期():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "劳务派遣试用期三个月合法吗")
    assert got.rule == "REN2"
    assert "不知道" in got.spoken


def test_p2_duration_or_mixed_asks():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "试用期六个月或者七个月合法吗")
    assert got.rule == "D69.ask"
    assert "请问" in got.spoken
    assert "六个月" in got.spoken and "七个月" in got.spoken


def test_p2_not_duration_asks():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "试用期不是六个月合法吗")
    assert got.rule == "D69.ask"
    assert "请问" in got.spoken


def test_p2_tier_or_mixed_asks():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "合同一年试用期二个月或三个月合法吗")
    assert got.rule == "D69.ask"
    assert "请问" in got.spoken


def test_p2_并且_two_topics():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "试用期六个月并且竞业限制二年合法吗")
    assert got.rule == "D69"
    assert "都合法" in got.spoken


def test_p2_既没有书面约定又七个月严格():
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    got = turn(w, s, "既没有书面约定又试用期七个月严格合法吗")
    assert got.rule == "D69"
    assert _noish(got.spoken)
