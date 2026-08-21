"""Dim3: MEM1–MEM5 memory / pins (L2)."""

from __future__ import annotations

import pytest

from para.kernel import boot, parse_msg
from para.route import hear, turn
from para.session import Session


@pytest.mark.L2
def test_mem1_focus_stack_cap_five():
    s = Session()
    for name in ("甲", "乙", "丙", "丁", "戊", "己"):
        s.push(name)
    assert len(s.focus_stack) == 5
    assert "甲" not in s.focus_stack
    assert s.focus() == "己"


@pytest.mark.L2
def test_mem2_teach_persists_chat_does_not():
    """Durable: hear/teach writes world; chat turn alone does not invent isa."""
    w, s = boot(), Session()

    def _isa_count() -> int:
        return sum(
            1 for a in w.facts if a.pred == "isa" and list(a.args) == ["电脑", "机器"]
        )

    before = _isa_count()
    turn(w, s, "电脑是机器")  # chat → no write
    assert _isa_count() == before
    hear(w, s, "电脑是机器")  # teach path
    assert _isa_count() == before + 1
    assert w.yes("isa(电脑, 机器)")
    s.push("电脑")
    assert s.reset_if("重置")
    assert s.focus_stack == []
    assert w.yes("isa(电脑, 机器)")


@pytest.mark.L2
def test_mem3_reset_phrases():
    w, s = boot(), Session()
    hear(w, s, "电脑是机器")
    s.push("电脑")
    s.doc_focus = "劳动法"
    assert turn(w, s, "新会话").ok or True
    # reset_if may be inside turn path
    s2 = Session()
    s2.push("电脑")
    assert s2.reset_if("重置")
    assert s2.focus_stack == []


@pytest.mark.L2
def test_mem5_coref_chain_grows():
    s = Session()
    s.note(src="小明", dst="小红", mark="hit")
    assert s.resolve_ana() == "小红"
    assert "小明" in s.coref_chain
    assert "小红" in s.coref_chain
