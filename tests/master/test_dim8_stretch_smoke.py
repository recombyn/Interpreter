"""Dim8 stretch smokes — not full 1000@1s / 100k-leak; CI-safe baselines (L4/stretch)."""

from __future__ import annotations

import time

import pytest

from para.repair import repair
from para.session import Session


@pytest.mark.L4
@pytest.mark.stretch
def test_stretch_pure_preprocess_throughput():
    """Proxy for 8.4: 1000×sample pure repairs should stay under 2s."""
    known = {"机器", "电脑", "劳动法"}
    vocab = known | {"试用期"}
    samples = (
        "积气",
        "机器器",
        "电脑是机器吗",
        "试用期六个月合不合法",
        "食先",
        "粉丝10w",
    )
    t0 = time.perf_counter()
    for _ in range(1000):
        for s in samples:
            repair(s, vocab, known)
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0, f"1000×{len(samples)} repairs took {elapsed:.3f}s"


@pytest.mark.L4
@pytest.mark.stretch
def test_stretch_focus_stack_no_grow_unbounded():
    """Proxy for 8.5: 10k pushes keep focus_stack at max_focus (no leak of pins)."""
    s = Session()
    for i in range(10_000):
        s.push(f"实体{i % 50}")
    assert len(s.focus_stack) == s.max_focus == 5
    assert len(s.coref_chain) <= s.max_coref
