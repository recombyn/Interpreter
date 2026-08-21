"""Shared fixtures for Para master suite."""

from __future__ import annotations

import pytest

from para.kernel import boot
from para.session import Session


@pytest.fixture
def world():
    return boot()


@pytest.fixture
def session():
    return Session()


@pytest.fixture
def ws(world, session):
    return world, session
