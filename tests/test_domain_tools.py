"""User-side domain scaffold + validate (no system world writes)."""

from __future__ import annotations

from pathlib import Path

import pytest

from para.tools.init_domain import scaffold
from para.tools.validate_domain import validate_domain_dir, validate_user_tree


@pytest.mark.L4
def test_init_and_validate_empty_template(tmp_path: Path):
    dest = scaffold("示范领域", tmp_path)
    assert (dest / "rules.tm").is_file()
    assert (dest / "limits.tm").is_file()
    rep = validate_domain_dir(dest)
    assert rep.ok
    assert rep.rules == 0
    assert any("no parsed rule" in w for w in rep.warns)


@pytest.mark.L4
def test_validate_catches_missing_limit(tmp_path: Path):
    d = tmp_path / "坏包"
    d.mkdir()
    (d / "rules.tm").write_text(
        "rule 加班 le 上限 合法吗|合规吗\n",
        encoding="utf-8",
    )
    (d / "limits.tm").write_text("# empty\n", encoding="utf-8")
    rep = validate_domain_dir(d)
    assert not rep.ok
    assert any("of(上限, 加班" in e for e in rep.errors)


@pytest.mark.L4
def test_validate_labor_law_pack():
    from para.paths import USER_DIR

    labor = USER_DIR / "劳动法"
    if not (labor / "rules.tm").is_file():
        pytest.skip("劳动法 pack missing")
    rep = validate_domain_dir(labor)
    assert rep.ok, rep.errors
    assert rep.rules >= 1


@pytest.mark.L4
def test_validate_all_finds_labor():
    from para.paths import USER_DIR

    reports = validate_user_tree(USER_DIR)
    names = {r.domain for r in reports}
    assert "劳动法" in names or any(r.rules for r in reports)
