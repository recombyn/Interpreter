"""Registry completeness — 42 modules, no silent drop."""

from __future__ import annotations

from pathlib import Path

import pytest

from .registry import MODULES, by_status

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.L1
def test_registry_has_exactly_42_modules():
    assert len(MODULES) == 42
    ids = [m.id for m in MODULES]
    assert len(ids) == len(set(ids))


@pytest.mark.L1
def test_registry_statuses_known():
    allowed = {"GREEN", "PARTIAL", "GAP", "N/A", "STRETCH"}
    for m in MODULES:
        assert m.status in allowed, m


@pytest.mark.L1
def test_green_owners_exist():
    missing: list[str] = []
    for m in MODULES:
        if m.status not in {"GREEN", "PARTIAL"}:
            continue
        for owner in m.owners:
            path = ROOT / owner
            if not path.is_file():
                missing.append(f"{m.id}:{owner}")
    assert not missing, missing


@pytest.mark.L1
def test_status_summary_printable():
    summary = {k: len(v) for k, v in by_status().items()}
    assert summary.get("GREEN", 0) == 42
    assert summary.get("PARTIAL", 0) + summary.get("GAP", 0) == 0
