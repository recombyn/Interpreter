import pytest

from cni.world.lang import FindResult, MachineWorld, boot, kernel, load_rules, parse_msg
from cni.world.parser import WorldParseError
from cni.world.translate import _lex_for, decode, hear, load_lex, speak, turn


def teach(machine, text: str) -> str | None:
    senses = decode(text)
    assert senses is not None
    assert hear(machine, senses) is True
    return speak(machine, _lex_for(text))


def test_kernel_is_only_isa_and_of():
    lang = kernel()
    assert lang.name == "mwl"
    assert [sort.name for sort in lang.sorts] == ["e"]
    assert [pred.name for pred in lang.preds] == ["isa", "of"]
    assert lang.acts == ["tell", "drop", "yesno", "find", "intro"]


def test_boot_intros_closed_names():
    world = boot()
    assert world.domain["me"] == "e"
    assert world.domain["greet"] == "e"
    assert world.domain["do"] == "e"
    assert world.apply(parse_msg("? isa(do, rel)")) is True
    assert world.apply(parse_msg("? isa(cause, rel)")) is True
    assert world.apply(parse_msg("? isa(invent, verb)")) is True


def test_find_var_defaults_to_sort_e():
    world = boot()
    world.apply(parse_msg("! e.1 : e"))
    world.apply(parse_msg("+ isa(e.1, greet)"))
    got = world.apply(parse_msg("?x isa(x, greet)"))
    assert isinstance(got, FindResult)
    assert list(got.values) == ["e.1"]
    got = world.apply(parse_msg("?x:e isa(x, greet)"))
    assert isinstance(got, FindResult)
    assert list(got.values) == ["e.1"]


def test_find_supports_conjunction():
    world = boot()
    world.apply(parse_msg("! e.1 : e"))
    world.apply(parse_msg("! e.2 : e"))
    world.apply(parse_msg("! 人 : e"))
    world.apply(parse_msg("! 电脑 : e"))
    world.apply(parse_msg("+ isa(e.1, invent)"))
    world.apply(parse_msg("+ isa(e.2, invent)"))
    world.apply(parse_msg("+ of(do, e.1, 人)"))
    world.apply(parse_msg("+ of(do, e.2, 人)"))
    world.apply(parse_msg("+ of(to, e.1, 电脑)"))
    got = world.apply(
        parse_msg("find(?x, isa(x, invent) ∧ of(do, x, 人) ∧ of(to, x, 电脑))")
    )
    assert isinstance(got, FindResult)
    assert list(got.values) == ["e.1"]
    assert got.rows == [{"x": "e.1"}]


def test_forward_rule_infers_transitive_isa():
    world = boot()
    world.apply(parse_msg("! 张三 : e"))
    world.apply(parse_msg("! 人 : e"))
    world.apply(parse_msg("! 生物 : e"))
    world.apply(parse_msg("+ isa(张三, 人)"))
    world.apply(parse_msg("+ isa(人, 生物)"))
    assert world.apply(parse_msg("? isa(张三, 生物)")) is True
    assert world.inference_stats()["inferred_facts"] >= 1


def test_forward_rule_depth_cap():
    world = MachineWorld(kernel(), rules=load_rules(), infer_depth=0)
    world.apply(parse_msg("! 甲 : e"))
    world.apply(parse_msg("! 乙 : e"))
    world.apply(parse_msg("! 丙 : e"))
    world.apply(parse_msg("! 丁 : e"))
    world.apply(parse_msg("+ isa(甲, 乙)"))
    world.apply(parse_msg("+ isa(乙, 丙)"))
    world.apply(parse_msg("+ isa(丙, 丁)"))
    # depth=0 disables forward inference.
    assert world.apply(parse_msg("? isa(甲, 丙)")) is not True
    assert world.apply(parse_msg("? isa(甲, 丁)")) is not True


def test_rule_loader_rejects_non_kernel_predicate(tmp_path):
    bad = tmp_path / "rules.tm"
    bad.write_text(
        "rule bad: likes(?a, ?b) => isa(?a, ?b)\n",
        encoding="utf-8",
    )
    with pytest.raises(WorldParseError):
        load_rules(bad)


def test_boot_accepts_custom_rules_and_depth(tmp_path):
    empty = tmp_path / "empty-rules.tm"
    empty.write_text("", encoding="utf-8")
    world = boot(rules_path=empty, infer_depth=0)
    assert world.inference_stats() == {"rules": 0, "inferred_facts": 0}


def test_hello_is_a_greet_act():
    senses = decode("你好")
    assert senses is not None
    assert [sense.name for sense in senses] == ["addr", "greet"]
    world = boot()
    assert hear(world, senses) is True
    acts = world.apply(parse_msg("?X:e isa(X, greet)"))
    assert isinstance(acts, FindResult)
    assert list(acts.values) == ["e.1"]
    assert world.apply(parse_msg("? of(do, e.1, other)")) is True
    assert world.apply(parse_msg("? of(to, e.1, me)")) is True
    assert turn(boot(), "你好") == "你好"


def test_greet_speak_uses_to_and_kind():
    world = boot()
    world.apply(parse_msg("! e.2 : e"))
    world.apply(parse_msg("+ isa(e.2, greet)"))
    world.apply(parse_msg("+ of(do, e.2, me)"))
    world.apply(parse_msg("+ of(to, e.2, other)"))
    assert speak(world) == "你好"


def test_closed_copula_have_loc():
    world = boot()
    assert hear(world, decode("你是我")) is True
    assert world.apply(parse_msg("? isa(me, other)")) is True
    assert teach(boot(), "你是我") == "我是你"
    world = boot()
    assert hear(world, decode("我有你")) is True
    assert world.apply(parse_msg("? of(has, other, me)")) is True
    assert teach(boot(), "我有你") == "你有我"
    world = boot()
    assert hear(world, decode("我在这")) is True
    assert world.apply(parse_msg("? of(at, other, this)")) is True
    assert teach(boot(), "我在这") == "你在这"


def test_open_name_intros_and_copula():
    lex = load_lex()
    forms = {form for form, _sense in lex.ins}
    assert "电脑" not in forms
    senses = decode("电脑")
    assert senses is not None
    assert [sense.name for sense in senses] == ["电脑"]
    assert senses[0].open is True
    world = boot()
    assert hear(world, senses) is True
    assert world.domain["电脑"] == "e"
    assert world.apply(parse_msg("? of(at, 电脑, here)")) is not True
    assert turn(world, "电脑") is None
    world = boot()
    assert hear(world, decode("这是电脑")) is True
    assert world.apply(parse_msg("? isa(this, 电脑)")) is True
    assert teach(boot(), "这是电脑") == "这是电脑"


def test_not_copula_drops_then_tells():
    world = boot()
    assert hear(world, decode("电脑是机器")) is True
    assert world.apply(parse_msg("? isa(电脑, 机器)")) is True
    assert hear(world, decode("电脑不是机器是人名")) is True
    assert world.apply(parse_msg("? isa(电脑, 机器)")) is not True
    assert world.apply(parse_msg("? isa(电脑, 人名)")) is True
    assert speak(world) == "电脑是人名"


def test_which_year_stays_one_sense():
    names = [sense.name for sense in decode("电脑是哪年发明的")]
    assert "whenq" in names
    assert "where" not in names
    assert "年发明" not in names


def test_ask_uses_taught_isa():
    world = boot()
    hear(world, decode("电脑是机器"))
    hear(world, decode("机器是设备"))
    assert turn(world, "电脑是什么") == "电脑是机器"
    assert turn(world, "电脑是谁") is None
    world = boot()
    teach(world, "我叫小明")
    assert turn(world, "我是谁") == "你叫小明"


def test_ask_where_uses_at():
    world = boot()
    hear(world, decode("电脑在桌上"))
    assert world.apply(parse_msg("? of(at, 电脑, 桌上)")) is True
    assert turn(world, "电脑在哪") == "电脑在桌上"


def test_nohave_and_not_loc_drop():
    world = boot()
    hear(world, decode("我有电脑"))
    assert world.apply(parse_msg("? of(has, other, 电脑)")) is True
    hear(world, decode("我没有电脑"))
    assert world.apply(parse_msg("? of(has, other, 电脑)")) is not True
    world = boot()
    hear(world, decode("电脑在这"))
    assert world.apply(parse_msg("? of(at, 电脑, this)")) is True
    hear(world, decode("电脑不在这"))
    assert world.apply(parse_msg("? of(at, 电脑, this)")) is not True


def test_ask_when_finds_told_year():
    world = boot()
    world.apply(parse_msg("! 电脑 : e"))
    world.apply(parse_msg("! e.1 : e"))
    world.apply(parse_msg("! y.1946 : e"))
    world.apply(parse_msg("+ isa(e.1, invent)"))
    world.apply(parse_msg("+ of(to, e.1, 电脑)"))
    world.apply(parse_msg("+ of(when, e.1, y.1946)"))
    assert turn(world, "电脑是哪年发明的") == "电脑是1946年"


def test_verb_event_and_year():
    world = boot()
    assert teach(world, "人发明电脑") == "人发明电脑"
    assert world.apply(parse_msg("? of(to, e.1, 电脑)")) is True
    world = boot()
    assert teach(world, "人1946年发明电脑") == "人1946年发明电脑"
    assert turn(world, "电脑是哪年发明的") == "电脑是1946年"
    world = boot()
    teach(world, "人发明电脑")
    assert turn(world, "人发明电脑") == "人发明电脑"
    assert turn(world, "人怎么发明电脑") == "人发明电脑"


def test_aspect_from_to_ba_and_with():
    world = boot()
    assert teach(world, "我正在喝水") == "你正在喝水"
    assert world.apply(parse_msg("? of(with, e.1, prog)")) is True
    world = boot()
    assert teach(world, "我不喝水") == "你不喝水"
    world = boot()
    spoken = teach(world, "从北京到上海")
    assert "北京" in spoken and "上海" in spoken
    world = boot()
    assert teach(world, "我把水杯放桌上") == "你把水杯放到桌上"
    world = boot()
    spoken = teach(world, "水杯被我放桌上")
    assert spoken == "你把水杯放到桌上"
    assert world.apply(parse_msg("? of(do, e.1, other)")) is True
    assert world.apply(parse_msg("? of(to, e.1, 水杯)")) is True
    world = boot()
    assert teach(world, "我给你苹果") == "你给我苹果"
    world = boot()
    assert "和" in teach(world, "我和你")


def test_de_num_ana_clause_english_hello():
    world = boot()
    assert "电脑" in teach(world, "我的电脑")
    world = boot()
    spoken = teach(world, "三个苹果")
    assert "三" in spoken and "苹果" in spoken
    world = boot()
    teach(world, "电脑是机器")
    assert turn(world, "它是东西") == "电脑是机器"
    assert "东西" not in world.domain
    world = boot()
    teach(world, "电脑是机器")
    spoken = teach(world, "电脑在桌上")
    assert spoken == "电脑在桌上"
    assert turn(boot(), "hello") == "hello"


def test_polar_have_what_call_than_de_num():
    world = boot()
    hear(world, decode("电脑是机器"))
    assert turn(world, "电脑是机器吗") == "电脑是机器"
    assert turn(world, "电脑是石头吗") == "电脑不是石头"
    assert turn(world, "电脑是不是机器") == "电脑是机器"
    world = boot()
    hear(world, decode("电脑比手机"))
    assert turn(world, "电脑比手机吗") == "电脑比手机"
    assert turn(world, "电脑比西瓜吗") == "电脑不比西瓜"
    world = boot()
    hear(world, decode("我和你"))
    assert turn(world, "我和你吗") == "你和我"
    assert turn(world, "我和他吗") == "不是"
    world = boot()
    hear(world, decode("电脑有屏幕"))
    assert turn(world, "电脑有什么") == "电脑有屏幕"
    assert turn(world, "电脑有屏幕吗") == "电脑有屏幕"
    assert turn(world, "电脑有键盘吗") == "电脑没有键盘"
    world = boot()
    hear(world, decode("电脑在桌上"))
    assert turn(world, "电脑在桌上吗") == "电脑在桌上"
    assert turn(world, "电脑在床上吗") == "电脑不在床上"
    world = boot()
    assert teach(world, "我叫小明") == "你叫小明"
    world = boot()
    assert teach(world, "电脑比手机") == "电脑比手机"
    world = boot()
    assert teach(world, "我的电脑") == "你的电脑"
    world = boot()
    assert teach(world, "三个苹果") == "三个苹果"
    world = boot()
    assert "要" in teach(world, "我要水")


def test_session_pegs_update_on_ask_and_greet():
    world = boot()
    teach(world, "电脑是机器")
    assert world.apply(parse_msg("? of(to, focus, 电脑)")) is True
    assert world.apply(parse_msg("? of(from, last, 电脑)")) is True
    assert world.apply(parse_msg("? of(to, last, 机器)")) is True
    assert world.apply(parse_msg("? of(with, last, copula)")) is True

    turn(world, "电脑是机器吗")
    assert world.apply(parse_msg("? of(to, focus, 电脑)")) is True
    assert world.apply(parse_msg("? of(from, last, 电脑)")) is True
    assert world.apply(parse_msg("? of(to, last, 机器)")) is True
    assert world.apply(parse_msg("? of(with, last, copula)")) is True

    asks = world.apply(parse_msg("?X:e isa(X, ask)"))
    assert isinstance(asks, FindResult)
    latest = asks.values[-1]
    assert world.apply(parse_msg(f"? of(with, {latest}, polar)")) is True
    assert world.apply(parse_msg(f"? of(with, {latest}, copula)")) is True

    world = boot()
    turn(world, "你好")
    assert world.apply(parse_msg("? of(to, focus, other)")) is True


def test_english_teach_ask_and_loc():
    world = boot()
    assert teach(world, "computer is machine") == "computer is machine"
    assert turn(world, "what is computer") == "computer is machine"
    world = boot()
    teach(world, "computer have screen")
    assert turn(world, "does computer have screen") == "computer have screen"
    assert turn(world, "does computer have keyboard") == "computer do not have keyboard"
    world = boot()
    spoken = teach(world, "computer is in room")
    assert "computer" in spoken and "room" in spoken
    world = boot()
    assert teach(world, "three apples") == "three apples"


def test_plain_turn_does_not_write_isa():
    world = boot()
    teach(world, "电脑是机器")
    assert turn(world, "电脑是桥梁") == "电脑是机器"
    assert world.apply(parse_msg("? isa(电脑, 机器)")) is True
    assert "桥梁" not in world.domain
    assert turn(world, "电脑时机器") == "电脑是机器"
    assert teach(world, "电脑是桥梁") == "电脑是桥梁"
    assert world.apply(parse_msg("? isa(电脑, 桥梁)")) is True
    assert world.apply(parse_msg("? isa(电脑, 机器)")) is not True

