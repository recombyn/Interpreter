"""Shared fixtures for Para master suite."""

from __future__ import annotations

import pytest

from para.judge import clear_judge_cache
from para.kernel import boot
from para.knowledge.text_doc import load_user_memories
from para.route import hear
from para.session import Session
from para.user_config import clear_user_config_cache


@pytest.fixture
def world():
    return boot()


@pytest.fixture
def session():
    return Session()


@pytest.fixture
def ws(world, session):
    return world, session


@pytest.fixture
def judge_ws():
    """Boot + labor memories with judge/config caches cleared."""
    clear_judge_cache()
    clear_user_config_cache()
    w, s = boot(), Session()
    load_user_memories(w)
    return w, s


@pytest.fixture
def seeded_ws(ws):
    """World with 电脑是机器 + 人买电脑 for hot-path benches."""
    w, s = ws
    hear(w, s, "电脑是机器")
    hear(w, s, "人买电脑")
    return w, s
