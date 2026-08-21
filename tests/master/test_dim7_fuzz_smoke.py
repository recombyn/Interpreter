"""Dim7: fuzz / stress smoke — zero crash, REN2-ish degrade (L3)."""

from __future__ import annotations

import time

import pytest

from para.kernel import boot
from para.route import turn
from para.session import Session


@pytest.mark.L3
@pytest.mark.parametrize(
    "text",
    [
        "的阿巴阿巴是吗合法不",
        "￥%……&*（）",
        "",
        "   ",
        "试用期 999999999999999 个月合法吗",
    ],
)
def test_fuzz_noise_no_exception(text: str):
    w, s = boot(), Session()
    got = turn(w, s, text)
    assert got is not None
    assert isinstance(got.spoken or "", str)


@pytest.mark.L3
def test_long_prefix_bounded(judge_ws):
    """Long filler + trailing judge — must finish without hang (smoke budget)."""
    w, s = judge_ws
    filler = "说明" * 200
    t0 = time.perf_counter()
    got = turn(w, s, filler + "试用期六个月合法吗")
    elapsed = time.perf_counter() - t0
    assert got is not None
    assert got.rule in {"D69", "D69.ask", "REN2", "D21"} or got.ok
    assert elapsed < 120.0, f"too slow: {elapsed:.1f}s"


@pytest.mark.L3
def test_unpunctuated_peel_smoke(judge_ws):
    w, s = judge_ws
    got = turn(w, s, "试用期六个月合法吗如果超过了怎么赔偿")
    assert got is not None
    assert "合法" in (got.spoken or "") or "请问" in (got.spoken or "") or got.rule


@pytest.mark.L3
def test_unpunctuated_two_d69(judge_ws):
    w, s = judge_ws
    got = turn(w, s, "试用期六个月合法吗竞业限制二年合法吗")
    assert "；" in (got.spoken or "") or "合法" in (got.spoken or "")
    assert "D69" in (got.rule or "")
