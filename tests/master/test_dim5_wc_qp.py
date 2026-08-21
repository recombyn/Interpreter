"""Dim5: WC1–WC3 world consistency (L2)."""

from __future__ import annotations

import pytest

from para.kernel import boot, parse_msg


def _intro(w, *names: str) -> None:
    for name in names:
        w.apply(parse_msg(f"! {name} : e"))


@pytest.mark.L2
def test_wc1_duplicate_tell_ignored():
    w = boot()
    _intro(w, "猫", "动物")
    w.apply(parse_msg("+ isa(猫, 动物)"))
    n = len(w.facts)
    w.apply(parse_msg("+ isa(猫, 动物)"))
    assert len(w.facts) == n
    assert sum(1 for a in w.facts if a.pred == "isa" and a.args == ("猫", "动物")) == 1


@pytest.mark.L2
def test_wc2_contradictions_coexist():
    """Policy: no force-resolve — both facts remain."""
    w = boot()
    _intro(w, "猫", "动物", "植物")
    w.apply(parse_msg("+ isa(猫, 动物)"))
    w.apply(parse_msg("+ isa(猫, 植物)"))
    assert w.yes("isa(猫, 动物)")
    assert w.yes("isa(猫, 植物)")


@pytest.mark.L2
def test_wc3_exact_drop():
    w = boot()
    _intro(w, "猫", "动物", "植物")
    w.apply(parse_msg("+ isa(猫, 动物)"))
    w.apply(parse_msg("+ isa(猫, 植物)"))
    w.apply(parse_msg("- isa(猫, 植物)"))
    assert not w.yes("isa(猫, 植物)")
    assert w.yes("isa(猫, 动物)")
