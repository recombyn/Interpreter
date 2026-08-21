"""Labor-law case: decode API + user knowledge pack."""

from __future__ import annotations

from para import Para
from para.paths import USER_DIR


def test_labor_concept_query():
    eng = Para(remember=False, load_user_docs=True, user_dir=USER_DIR)
    out = eng.decode("员工是什么", write=False)
    assert out.ok
    assert out.status == "query"
    assert not out.miss
    assert "员工是人" in out.spoken


def test_labor_d69_probation():
    eng = Para(remember=False, load_user_docs=True, user_dir=USER_DIR)
    ok = eng.decode("试用期六个月合法吗", write=False)
    assert ok.status == "query"
    assert ok.rule == "D69"
    assert "合法" in ok.spoken
    assert "不合法" not in ok.spoken
    # Conditional: must not be bare absolute yes without tier bands
    assert any(x in ok.spoken for x in ("三年", "不得超过", "情况", "不满"))
    assert ok.evidence
    # cite and/or condition evidence
    texts = " ".join(e.text for e in ok.evidence)
    assert "第十九条" in texts or "不得超过" in texts or "三年" in texts

    bad = eng.decode("试用期七个月合法吗", write=False)
    assert bad.rule == "D69"
    assert "不合法" in bad.spoken
    assert bad.evidence

    expl = eng.decode("什么情况下试用期六个月不违法", write=False)
    assert expl.rule == "D69"
    assert any(x in expl.spoken for x in ("三年", "不得超过", "情况"))

    inv = eng.decode("试用期六个月违法吗", write=False)
    assert inv.rule == "D69"
    assert "不违法" in inv.spoken or ("合法" in inv.spoken and "不合法" not in inv.spoken)

    # focus pin → bare duration+legality
    eng.decode("试用期合法吗", write=False)
    bare = eng.decode("六个月不违法", write=False)
    assert bare.rule == "D69"
    assert any(x in bare.spoken for x in ("三年", "不得超过", "合法", "不违法"))

    tier = eng.decode("合同一年试用期二个月合法吗", write=False)
    assert tier.rule == "D69"
    assert "合法" in tier.spoken
    assert "不合法" not in tier.spoken


def test_labor_d69_ask_includes_related_content():
    eng = Para(remember=False, load_user_docs=True, user_dir=USER_DIR)
    out = eng.decode("试用期合法吗", write=False)
    assert out.rule == "D69.ask"
    assert "几个月" in out.spoken
    assert out.evidence
    assert "第十九条" in out.evidence[0].text or "不得超过" in out.evidence[0].text


def test_labor_teach_then_query(tmp_path):
    # Still use real user_dir so rules/limits load; write is session-local (remember=False).
    eng = Para(remember=False, load_user_docs=True, user_dir=USER_DIR)
    w = eng.decode("教实习是工作", write=True)
    assert w.status == "write"
    assert w.ok
    q = eng.decode("实习是什么", write=False)
    assert "实习是工作" in q.spoken


def test_labor_unknown_refuses():
    eng = Para(remember=False, load_user_docs=True, user_dir=USER_DIR)
    out = eng.decode("独角兽有加班费吗", write=False)
    assert out.miss or out.status == "refuse" or "不知道" in (out.spoken or "")


def test_labor_long_prefix():
    eng = Para(remember=False, load_user_docs=True, user_dir=USER_DIR)
    out = eng.decode("请问一下我们公司约定试用期六个月合法吗", write=False)
    assert out.rule == "D69"
    assert "合法" in out.spoken
    assert "不合法" not in out.spoken
    assert any(x in out.spoken for x in ("三年", "不得超过", "情况", "不满"))
    assert out.evidence


def test_labor_multi_two_d69():
    eng = Para(remember=False, load_user_docs=True, user_dir=USER_DIR)
    out = eng.decode("试用期六个月合法吗竞业限制二年合法吗", write=False)
    assert "；" in out.spoken
    assert "试用期" in out.spoken
    assert "竞业" in out.spoken
    assert "合法" in out.spoken
    assert out.evidence


def test_labor_multi_long_also():
    eng = Para(remember=False, load_user_docs=True, user_dir=USER_DIR)
    out = eng.decode(
        "员工入职签一年合同试用期两个月合法吗另外竞业限制两年合法吗",
        write=False,
    )
    assert "；" in out.spoken
    assert "合法" in out.spoken
    assert out.evidence
