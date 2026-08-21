"""Dim1: E1–E5 repair — pure function, no world boot (L1 fast)."""

from __future__ import annotations

import pytest

from para.repair import repair

KNOWN = {"机器"}
VOCAB = {"机器", "电脑"}


@pytest.mark.L1
def test_e1_exact_unchanged():
    assert repair("机器", VOCAB, KNOWN) == "机器"
    assert repair("电脑", VOCAB, KNOWN) == "电脑"


@pytest.mark.L1
def test_e2_homophone_unique():
    # pin_group 机/积/基 + 器/气/期 → 积气 ≡ 机器
    assert repair("积气", set(), KNOWN) == "机器"


@pytest.mark.L1
def test_e2_ambiguous_or_unpinned_stays():
    # No unique known hit → leave as-is (safe abandon)
    assert repair("积气", set(), set()) == "积气"


@pytest.mark.L1
def test_e3_edit_distance_one():
    # Same pin-key window, lev=1 → unique replace
    assert repair("积器", set(), KNOWN) == "机器"


@pytest.mark.L1
def test_e4_delete_extra_char():
    """E4: 多一字且删一可匹配（pin 归一后）。"""
    assert repair("机器器", set(), KNOWN) == "机器"
    assert repair("积气气", set(), KNOWN) == "机器"


@pytest.mark.L1
def test_e4_does_not_eat_合法吗_after_合同类型():
    """Regression: 合同类型合法吗 must not lose 合 via E4 twin of 合→和."""
    known = {"合同类型", "机器"}
    assert repair("合同类型合法吗", known, known) == "合同类型合法吗"
    assert repair("固定期限或无固定期限合同类型合法吗", known, known) == (
        "固定期限或无固定期限合同类型合法吗"
    )


@pytest.mark.L1
def test_e5_never_insert_short():
    # 少字永不补
    assert repair("机", set(), KNOWN) == "机"


@pytest.mark.L1
def test_e_protects_合不合法():
    # Regression: pin 合→和 must not rewrite judge trigger
    assert repair("试用期六个月合不合法", {"试用期"}, {"试用期"}) == "试用期六个月合不合法"
