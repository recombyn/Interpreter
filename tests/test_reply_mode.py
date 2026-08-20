"""User reply_mode / form.tm overrides for polar yes/no surfaces."""

from __future__ import annotations

from pathlib import Path

from cni.kernel import boot
from cni.render.forms import clear_forms_cache, form, load_forms
from cni.user_config import reply_mode as load_reply_mode
from cni.route import hear, turn
from cni.session import Session


def test_reply_mode_bool_maps_yes_no(tmp_path: Path):
    clear_forms_cache()
    cfg = tmp_path / "config.tm"
    cfg.write_text("reply_mode bool\n", encoding="utf-8")
    world = Path(__file__).resolve().parents[1] / "src" / "cni" / "data" / "world" / "form.tm"
    user = tmp_path / "form.tm"
    user.write_text("", encoding="utf-8")
    assert load_reply_mode(str(cfg)) == "bool"
    forms = load_forms(world, user_path=user, reply_mode="bool")
    assert forms["yes"] == "true"
    assert forms["no"] == "false"
    clear_forms_cache()


def test_reply_mode_zh_bool(tmp_path: Path):
    clear_forms_cache()
    world = Path(__file__).resolve().parents[1] / "src" / "cni" / "data" / "world" / "form.tm"
    forms = load_forms(world, user_path=tmp_path / "missing.tm", reply_mode="zh_bool")
    assert forms["yes"] == "是"
    assert forms["no"] == "否"
    clear_forms_cache()


def test_user_form_overrides_out(tmp_path: Path):
    clear_forms_cache()
    world = Path(__file__).resolve().parents[1] / "src" / "cni" / "data" / "world" / "form.tm"
    user = tmp_path / "form.tm"
    user.write_text("out yes YES\nout no NO\n", encoding="utf-8")
    forms = load_forms(world, user_path=user, reply_mode="default")
    assert forms["yes"] == "YES"
    assert forms["no"] == "NO"
    # bool mode still wins for yes/no
    forms_b = load_forms(world, user_path=user, reply_mode="bool")
    assert forms_b["yes"] == "true"
    clear_forms_cache()


def test_polar_question_bool_mode(monkeypatch, tmp_path: Path):
    clear_forms_cache()
    world = Path(__file__).resolve().parents[1] / "src" / "cni" / "data" / "world" / "form.tm"
    user = tmp_path / "form.tm"
    user.write_text("", encoding="utf-8")

    def _forms(**_kwargs):
        return load_forms(world, user_path=user, reply_mode="bool")

    monkeypatch.setattr("cni.render.forms.load_forms", lambda *a, **k: _forms())
    monkeypatch.setattr("cni.render.forms.form", lambda c: _forms().get(c))

    from cni.decode import _no, _yes

    assert _yes() == "true"
    assert _no() == "false"

    w, s = boot(), Session()
    hear(w, s, "人能吃苹果")
    got = turn(w, s, "人能不能吃苹果")
    assert got.spoken == "true"
    clear_forms_cache()
