from cni.interpreter import Interpreter
from cni.text.utf8 import as_text, as_utf8
from cni.world.lang import parse_msg, save_world
from cni.world.translate import _lex_for, decode, hear, speak


def teach(interp: Interpreter, text: str) -> str | None:
    senses = decode(text)
    assert senses is not None
    assert hear(interp.speech, senses) is True
    spoken = speak(interp.speech, _lex_for(text))
    if interp.remember:
        save_world(interp.speech, interp.memory_path)
    return spoken


def test_hello_goes_through_world_then_back():
    result = Interpreter().interpret("你好")
    assert "world" in result.notes
    assert result.reply == "你好"


def test_loc_roundtrip():
    result = Interpreter().interpret("我在这")
    assert result.reply == ""
    assert result.notes == ["world-miss"]


def test_open_name_电脑():
    interp = Interpreter()
    result = interp.interpret("电脑")
    assert result.notes == ["world-miss"]
    assert result.reply == ""
    result = interp.interpret("这是电脑")
    assert result.reply == ""


def test_correct_isa_in_same_world():
    interp = Interpreter()
    teach(interp, "电脑是机器")
    reply = interp.reply("电脑不是机器是人名")
    assert reply == "电脑是机器"


def test_ask_what_after_teach():
    interp = Interpreter()
    teach(interp, "电脑是机器")
    assert interp.reply("电脑是什么") == "电脑是机器"


def test_ask_without_fact_is_world_miss():
    result = Interpreter().interpret("电脑是什么")
    assert result.notes == ["world-miss"]
    assert result.reply == ""


def test_unknown_utterance_stays_world_miss():
    result = Interpreter().interpret("blorptoken")
    assert result.notes == ["world-miss"]
    assert result.reply == ""
    result = Interpreter().interpret("为什么电脑是机器")
    assert result.notes == ["world-miss"]
    assert result.reply == ""
    result = Interpreter().interpret("why is computer machine")
    assert result.notes == ["world-miss"]
    assert result.reply == ""


def test_remember_reload(tmp_path):
    path = tmp_path / "world.tm"
    first = Interpreter(remember=True, memory_path=path)
    teach(first, "电脑是机器")
    second = Interpreter(remember=True, memory_path=path)
    assert second.reply("电脑是什么") == "电脑是机器"
    assert Interpreter().reply("电脑是什么") == ""


def test_polar_and_english_through_interpreter():
    interp = Interpreter()
    teach(interp, "电脑是机器")
    assert interp.reply("电脑是机器吗") == "电脑是机器"
    interp = Interpreter()
    teach(interp, "computer is machine")
    assert interp.reply("what is computer") == "computer is machine"


def test_remember_keeps_topic(tmp_path):
    path = tmp_path / "world.tm"
    first = Interpreter(remember=True, memory_path=path)
    teach(first, "电脑是机器")
    second = Interpreter(remember=True, memory_path=path)
    assert second.reply("它是东西") == "电脑是机器"


def test_remember_restores_session_pegs(tmp_path):
    path = tmp_path / "world.tm"
    first = Interpreter(remember=True, memory_path=path)
    teach(first, "电脑是机器")
    first.reply("电脑是机器吗")

    second = Interpreter(remember=True, memory_path=path)
    # focus/last should survive restart.
    assert second.speech.apply(parse_msg("? of(to, focus, 电脑)")) is True
    assert second.speech.apply(parse_msg("? of(from, last, 电脑)")) is True
    assert second.speech.apply(parse_msg("? of(to, last, 机器)")) is True
    assert second.speech.apply(parse_msg("? of(with, last, copula)")) is True
    # polar ask metadata should also survive.
    asks = second.speech.apply(parse_msg("?X:e isa(X, ask)"))
    assert asks is not None and len(asks.values) > 0
    latest = asks.values[-1]
    assert second.speech.apply(parse_msg(f"? of(with, {latest}, polar)")) is True


def test_interpreter_can_disable_inference(tmp_path):
    empty_rules = tmp_path / "empty-rules.tm"
    empty_rules.write_text("", encoding="utf-8")
    interp = Interpreter(rules_path=empty_rules, infer_depth=0)
    interp.speech.apply(parse_msg("! 张三 : e"))
    interp.speech.apply(parse_msg("! 人 : e"))
    interp.speech.apply(parse_msg("! 生物 : e"))
    interp.speech.apply(parse_msg("+ isa(张三, 人)"))
    interp.speech.apply(parse_msg("+ isa(人, 生物)"))
    assert interp.speech.apply(parse_msg("? isa(张三, 生物)")) is not True


def test_reply_accepts_utf8_bytes():
    interp = Interpreter()
    reply = interp.reply("你好".encode("utf-8"))
    assert isinstance(reply, str)
    assert "你好" in reply


def test_readme_pipeline_teach_ask_infer():
    interp = Interpreter()
    assert teach(interp, "电脑是机器") == "电脑是机器"
    assert interp.reply("电脑是什么") == "电脑是机器"
    assert teach(interp, "机器是设备") == "机器是设备"
    assert interp.speech.inferred_count >= 1
    assert interp.reply("电脑是什么") == "电脑是机器"
    assert interp.speech.apply(parse_msg("? isa(电脑, 设备)")) is True


def test_trace_notes_inference():
    interp = Interpreter()
    first = interp.interpret("电脑是机器")
    assert first.notes == ["world-miss"]
    teach(interp, "电脑是机器")
    teach(interp, "机器是设备")
    second = interp.interpret("电脑是什么")
    assert "world" in second.notes
    assert interp.speech.apply(parse_msg("? isa(电脑, 设备)")) is True


def test_wo_is_utf8_bytes():
    assert "我".encode("utf-8") == bytes.fromhex("e68891")
    assert as_text(b"\xe6\x88\x91") == "我"
    assert as_utf8("我") == b"\xe6\x88\x91"
