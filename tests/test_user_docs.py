"""User-layer text → .tm + content store; D67 line Q&A; MEM4 short-ask."""

from __future__ import annotations

from cni.app import Interpreter
from cni.knowledge.content_store import ContentStore, default_content_root
from cni.knowledge.text_doc import parse_user_text, sync_user_text
from cni.paths import USER_DIR
from cni.preprocess import apply_doc_query
from cni.session import Session


def test_text_suffixes_supported():
    from cni.knowledge.text_doc import TEXT_SUFFIXES

    for suf in (".text", ".txt", ".md", ".mk", ".markdown"):
        assert suf in TEXT_SUFFIXES


def test_apply_doc_query_line_only():
    assert apply_doc_query("第20行有什么") == "第20行的内容是什么"
    assert apply_doc_query("劳动法第20行有什么") == "劳动法第20行的内容是什么"
    assert apply_doc_query("第一条是什么") == "第一条是什么"


def test_parse_user_text_is_lines_only():
    path = USER_DIR / "劳动法.text"
    if not path.is_file():
        return
    doc = parse_user_text(path)
    assert doc.lines
    assert doc.lines[19].no == 20


def test_sync_writes_tm_and_content_store():
    path = USER_DIR / "劳动法.text"
    if not path.is_file():
        return
    tm = sync_user_text(path, force=True)
    assert tm is not None
    blob = tm.read_text(encoding="utf-8")
    assert "第20行" in blob
    store = ContentStore(default_content_root(USER_DIR))
    bodies = store.get("劳动法第20行")
    assert bodies
    assert "完善劳动合同制度" in bodies[0] or "劳动合同" in bodies[0]


def test_sync_and_query_line_d67():
    path = USER_DIR / "劳动法.text"
    if not path.is_file():
        return
    sync_user_text(path, force=True)
    interp = Interpreter(remember=False, load_user_docs=True)
    r = interp.reply("第20行的内容是什么")
    assert "完善劳动合同制度" in r
    r3 = interp.reply("第20行有什么")
    assert "完善劳动合同制度" in r3


def test_mem4_short_ask_reuses_entity_d67():
    path = USER_DIR / "劳动法.text"
    if not path.is_file():
        return
    sync_user_text(path, force=True)
    interp = Interpreter(remember=False, load_user_docs=True)
    r1 = interp.interpret("第20行的内容是什么")
    assert r1.rule == "D67"
    assert "完善劳动合同制度" in r1.reply
    assert interp.session.focus(0)
    r2 = interp.interpret("那呢")
    assert r2.rule == "D67"
    assert "完善劳动合同制度" in r2.reply


def test_session_expand_short_ask():
    s = Session()
    assert s.expand_short_ask("那呢") is None
    s.push("劳动法第20行")
    assert s.expand_short_ask("那呢") == "劳动法第20行的内容是什么"
    assert s.doc_focus == "劳动法"


def test_doc_focus_qualifies_bare_line_entity():
    s = Session()
    s.set_doc("劳动法")
    domain = {"第20行", "劳动法第20行"}
    assert s.qualify_entity("第20行", domain) == "劳动法第20行"
    s.push("第20行")
    # pin stays bare until qualify; expand uses qualify against domain
    assert s.expand_short_ask("那呢", domain) == "劳动法第20行的内容是什么"
