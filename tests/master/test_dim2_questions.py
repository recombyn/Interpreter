"""Dim2: D21–D36 questions — structural acceptance via rule + facts (L1)."""

from __future__ import annotations

import pytest

from para.kernel import boot, parse_msg
from para.route import hear, turn
from para.session import Session


@pytest.mark.L1
def test_d21_yesno_isa():
    w, s = boot(), Session()
    hear(w, s, "电脑是机器")
    got = turn(w, s, "电脑是机器吗")
    assert got.rule in {"D21", "D23"}
    assert got.spoken in {"是的", "true", "是"}


@pytest.mark.L1
def test_d22_d23_polar_variants():
    w, s = boot(), Session()
    hear(w, s, "电脑是机器")
    assert turn(w, s, "电脑是不是机器").spoken in {"是的", "true", "是"}
    assert turn(w, s, "电脑有没有屏幕").rule in {"D22", "D23", "REN2", "D21"}


@pytest.mark.L1
def test_d25_who_agent():
    w, s = boot(), Session()
    hear(w, s, "人买电脑")
    got = turn(w, s, "谁买电脑")
    assert got.rule == "D25"
    assert "人" in (got.spoken or "")


@pytest.mark.L1
def test_d26_what_object():
    w, s = boot(), Session()
    hear(w, s, "人买电脑")
    got = turn(w, s, "人买什么")
    assert got.rule == "D26"
    assert "电脑" in (got.spoken or "")


@pytest.mark.L1
def test_d27_d28_what_who_identity():
    w, s = boot(), Session()
    hear(w, s, "电脑是机器")
    got = turn(w, s, "电脑是什么")
    assert got.rule in {"D27", "D28"}
    assert "机器" in (got.spoken or "")


@pytest.mark.L1
def test_d29_where():
    w, s = boot(), Session()
    hear(w, s, "电脑在桌上")
    got = turn(w, s, "电脑在哪里")
    assert got.rule == "D29"
    assert "桌" in (got.spoken or "")


@pytest.mark.L1
def test_d32_choice_or():
    w, s = boot(), Session()
    hear(w, s, "电脑是机器")
    got = turn(w, s, "电脑是机器还是植物")
    assert got.rule == "D32"
    assert "机器" in (got.spoken or "")


@pytest.mark.L1
def test_d35_rhetorical_refuse():
    w, s = boot(), Session()
    hear(w, s, "电脑是机器")
    got = turn(w, s, "难道电脑不是机器吗")
    assert got.rule == "D35"
    assert "不知道" in (got.spoken or "") or "理解" in (got.spoken or "")
