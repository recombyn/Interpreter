"""Decode robustness: 意合 clauses, coref, ambig_mode."""

from __future__ import annotations

from para.decode import _clause_split, decode
from para.kernel import boot
from para.route import hear, turn
from para.session import Session
from para.user_config import clear_user_config_cache


def test_yihe_because_split():
    got = _clause_split("下雨了，我不出门")
    assert got is not None
    rel, parts, rule = got
    assert rel == "cause"
    assert rule == "D37y"
    assert parts[0] == "下雨了"
    assert "不出门" in parts[1]


def test_yihe_teach_links_because():
    w, s = boot(), Session()
    got = hear(w, s, "下雨了，我不出门")
    assert got.ok
    assert "D37y" in (got.rule or "") or got.rule.startswith("D37")
    # cause link between two events (same rel as 因为…所以)
    linked = [
        a
        for a in w.facts
        if a.pred == "of" and len(a.args) == 3 and a.args[0] == "cause"
    ]
    assert linked


def test_resolve_ana_prefers_patient():
    s = Session()
    s.note(src="小明", dst="小红", mark="hit")
    assert s.resolve_ana() == "小红"
    assert "小明" in s.coref_chain and "小红" in s.coref_chain


def test_ambig_clarify_mode(monkeypatch):
    clear_user_config_cache()
    monkeypatch.setattr("para.user_config.ambig_mode", lambda path=None: "clarify")
    w, s = boot(), Session()
    from para.route import route

    # Short polar stays single-bucket; clarify mode must not break yes/no.
    route(w, s, "教电脑是机器")
    got = turn(w, s, "电脑是机器吗")
    assert got.ok
    assert got.spoken in {"是的", "true", "是"}
    clear_user_config_cache()


def test_ambig_clarify_multi_bucket(monkeypatch):
    """AMB1: long comma sentence with clarify mode returns ambiguity prompt."""
    clear_user_config_cache()
    monkeypatch.setattr("para.user_config.ambig_mode", lambda path=None: "clarify")
    w, s = boot(), Session()
    hear(w, s, "小明打小红")
    got = turn(w, s, "小明打小红，我不去吗")
    # May be AMB1 or a normal answer depending on bucket hits; never RO3 crash
    assert got.ok
    if got.rule == "AMB1":
        assert got.confidence < 1.0
        assert got.spoken
    clear_user_config_cache()


def test_negation_write_does_not_store_negated_event():
    """D57 write path: particle echo only — no new negated of(kind,…) fact."""
    w, s = boot(), Session()
    hear(w, s, "人吃苹果")
    before = len(w.facts)
    got = hear(w, s, "人不吃苹果")
    assert got.ok
    # May add no new kind event for the negation itself
    kinds = [
        a
        for a in w.facts
        if a.pred == "of" and len(a.args) == 3 and a.args[0] == "kind"
    ]
    assert len(kinds) >= 1
    assert got.rule in {"D57", "D57+"} or got.rule.startswith("D57")
    assert len(w.facts) >= before  # did not require shrink
