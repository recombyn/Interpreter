"""Dim2: D37–D46 compound + D47–D56 deixis/ellipsis (L1/L2)."""

from __future__ import annotations

import pytest

from para.kernel import boot, parse_msg
from para.route import hear
from para.session import Session


@pytest.mark.L1
def test_d37_cause_pair():
    w, s = boot(), Session()
    assert hear(w, s, "因为人饿所以人吃饭").rule == "D37"
    assert w.apply(parse_msg("? of(cause, e.2, e.1)")) is True


@pytest.mark.L1
def test_d39_contrast_pair():
    w, s = boot(), Session()
    got = hear(w, s, "虽然人累但是人吃饭")
    assert got.rule == "D39"
    assert w.apply(parse_msg("? of(contrast, e.2, e.1)")) is True


@pytest.mark.L1
def test_d40_condition_pair():
    w, s = boot(), Session()
    assert hear(w, s, "如果人来就人吃饭").rule == "D40"
    assert w.apply(parse_msg("? of(condition, e.2, e.1)")) is True


@pytest.mark.L1
def test_d42_before_pair():
    w, s = boot(), Session()
    hear(w, s, "先人吃饭然后人喝水")
    assert w.apply(parse_msg("? of(before, e.2, e.1)")) is True


@pytest.mark.L1
def test_d45_progression_pair():
    w, s = boot(), Session()
    got = hear(w, s, "不但人吃饭而且人喝水")
    assert got.rule == "D45"
    assert w.apply(parse_msg("? of(progression, e.2, e.1)")) is True


@pytest.mark.L1
def test_d50_d51_person_swap():
    """你→me（系统）, 我→other（用户）."""
    w, s = boot(), Session()
    hear(w, s, "你吃饭")
    assert w.apply(parse_msg("? of(agent, e.1, me)")) is True
    w2, s2 = boot(), Session()
    hear(w2, s2, "我吃饭")
    assert w2.apply(parse_msg("? of(agent, e.1, other)")) is True


@pytest.mark.L2
def test_d52_ana_he_uses_focus():
    s = Session()
    s.note(src="小明", dst="电脑", mark="hit")
    assert s.resolve_ana() == "电脑"
