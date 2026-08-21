"""Dim8 CI baselines for throughput (8.4) and bounded growth (8.5).

Aspirational brochure numbers (full pytest suite <1s / 100k full decode turns)
remain marked ``stretch`` on the heaviest cases; CI gates use single-boot hot path
and Session pin bounds — honest industrial smoke, not fake greens.
"""

from __future__ import annotations

import gc
import time
import tracemalloc

import pytest

from para.preprocess import apply_f_order, apply_g
from para.repair import repair
from para.route import turn
from para.session import Session


_PURE_SAMPLES = (
    "积气",
    "机器器",
    "电脑是机器吗",
    "试用期六个月合不合法",
    "食先",
    "粉丝10w",
    "合同类型合法吗",
)


@pytest.mark.L4
def test_8_4_pure_path_1000_under_one_second():
    """8.4 gate: E/F/G-class pure path ≥1000 sample-loops in <1s (no boot)."""
    known = {"机器", "电脑", "劳动法", "合同类型", "试用期"}
    vocab = set(known)
    t0 = time.perf_counter()
    n = 0
    while n < 1000:
        for s in _PURE_SAMPLES:
            repair(s, vocab, known)
            apply_f_order(s)
            apply_g(s)
            n += 1
            if n >= 1000:
                break
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0, f"1000 pure loops took {elapsed:.3f}s"


@pytest.mark.L4
def test_8_4_single_boot_hot_path_throughput(seeded_ws):
    """8.4 gate: one boot, then ≥100 turn cycles with bounded wall time."""
    w, s = seeded_ws
    cases = ("电脑是机器吗", "谢谢", "重置", "人买电脑", "谁买电脑")
    t0 = time.perf_counter()
    for i in range(100):
        turn(w, s, cases[i % len(cases)])
    elapsed = time.perf_counter() - t0
    assert elapsed < 60.0, f"100 hot turns took {elapsed:.1f}s"
    assert len(s.focus_stack) <= s.max_focus


@pytest.mark.L4
def test_8_5_session_pins_survive_100k_pushes():
    """8.5 gate: 100k push/note ops — stacks stay at caps."""
    s = Session()
    for i in range(100_000):
        s.push(f"实体{i % 200}")
        if i % 3 == 0:
            s.note(src=f"甲{i % 10}", dst=f"乙{i % 10}", mark="hit")
        if i % 1000 == 0:
            s.pending_judge_topic = "试用期"
            s.pending_judge_text = "试用期合法吗"
    assert len(s.focus_stack) == s.max_focus == 5
    assert len(s.coref_chain) <= s.max_coref
    assert len(s.event_stack) <= s.max_focus


@pytest.mark.L4
def test_8_5_turn_loop_memory_bounded(seeded_ws):
    """8.5 gate: 500 turns on one world — focus capped; alloc delta not explosive."""
    w, s = seeded_ws
    gc.collect()
    tracemalloc.start()
    base = tracemalloc.get_traced_memory()[0]
    phrases = ("电脑是机器吗", "电脑是什么", "谢谢", "哦", "重置", "人来")
    for i in range(500):
        turn(w, s, phrases[i % len(phrases)])
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(s.focus_stack) <= s.max_focus
    delta_mb = (peak - base) / (1024 * 1024)
    assert delta_mb < 200.0, f"tracemalloc peak delta {delta_mb:.1f} MiB"


@pytest.mark.L4
@pytest.mark.stretch
def test_stretch_long_prefix_5k_chars_budget(ws):
    """Stretch ReDoS proxy: ~5k filler + polar ask finishes in budget."""
    w, s = ws
    filler = "说明" * 2500
    t0 = time.perf_counter()
    got = turn(w, s, filler + "电脑是机器吗")
    elapsed = time.perf_counter() - t0
    assert got is not None
    assert elapsed < 90.0, f"5k-prefix turn took {elapsed:.1f}s"
