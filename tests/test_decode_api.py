"""Contract: in-scope faithful; out-of-scope refuse; never invent."""

from __future__ import annotations

from para import DecodeOutcome, Para


def test_decode_unknown_refuses(tmp_path):
    eng = Para(remember=False, load_user_docs=False, user_dir=tmp_path)
    out = eng.decode("火星上有独角兽吗")
    assert isinstance(out, DecodeOutcome)
    assert out.miss or out.status in {"refuse", "query"}
    assert out.facts_added == ()
    # Must not invent a yes about untaught world
    assert "独角兽" not in (out.spoken or "") or out.miss or out.status == "refuse"


def test_decode_teach_then_query_faithful(tmp_path):
    eng = Para(remember=False, load_user_docs=False, user_dir=tmp_path)
    w = eng.decode("教电脑是机器", write=True)
    assert w.status == "write"
    assert w.ok
    assert any(f.pred == "isa" and f.args == ("电脑", "机器") for f in w.facts_added)

    q = eng.decode("电脑是什么", write=False)
    assert q.status == "query"
    assert not q.miss
    assert "电脑是机器" in q.spoken
    assert q.rule


def test_decode_same_input_same_output(tmp_path):
    eng = Para(remember=False, load_user_docs=False, user_dir=tmp_path)
    eng.decode("教苹果是水果", write=True)
    a = eng.decode("苹果是什么", write=False)
    b = eng.decode("苹果是什么", write=False)
    assert a.spoken == b.spoken
    assert a.rule == b.rule
    assert a.status == b.status


def test_decode_to_dict_host_shape(tmp_path):
    eng = Para(remember=False, load_user_docs=False, user_dir=tmp_path)
    eng.decode("教水是液体", write=True)
    d = eng.decode("水是什么", write=False).to_dict()
    assert set(d) >= {
        "ok",
        "status",
        "rule",
        "text",
        "spoken",
        "facts_added",
        "evidence",
        "miss",
    }
    assert isinstance(d["facts_added"], list)
    assert isinstance(d["evidence"], list)
