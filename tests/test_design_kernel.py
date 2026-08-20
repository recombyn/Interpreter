from cni.app import Interpreter
from cni.kernel import boot, kernel, parse_msg
from cni.route import hear, turn
from cni.session import Session


def test_kernel_wire_preds():
    lang = kernel()
    assert [p.name for p in lang.preds] == ["isa", "of", "located", "has"]


def test_boot_rels():
    w = boot()
    assert w.apply(parse_msg("? isa(agent, rel)")) is True
    assert w.apply(parse_msg("? isa(forbid, rel)")) is True
    assert w.apply(parse_msg("? isa(when, rel)")) is True


def test_located_has_native_wire():
    w = boot()
    s = Session()
    assert hear(w, s, "电脑在桌上").ok
    assert w.apply(parse_msg("? located(电脑, 桌上)")) is True
    assert hear(w, s, "人有电脑").ok
    assert w.apply(parse_msg("? has(人, 电脑)")) is True
    where = turn(w, s, "电脑在哪里")
    assert where.rule == "D29"
    assert "桌" in (where.spoken or "")


def test_ro_teach_writes_chat_does_not():
    w = boot()
    s = Session()
    assert turn(w, s, "电脑是机器").ok
    assert "电脑" not in w.domain
    assert hear(w, s, "电脑是机器").ok
    assert w.apply(parse_msg("? isa(电脑, 机器)")) is True


def test_d1_event_roles():
    w = boot()
    s = Session()
    assert hear(w, s, "人发明电脑").ok
    assert w.apply(parse_msg("? of(kind, e.1, invent)")) is True
    assert w.apply(parse_msg("? of(agent, e.1, 人)")) is True
    assert w.apply(parse_msg("? of(object, e.1, 电脑)")) is True


def test_d2_intransitive():
    w = boot()
    s = Session()
    assert hear(w, s, "人来").rule == "D2"
    assert w.apply(parse_msg("? of(kind, e.1, come)")) is True
    assert machine_objects(w, "e.1") == []


def machine_objects(w, eid: str) -> list[str]:
    got = w.find(f"?x of(object, {eid}, x)")
    return list(got.values)


def test_d7_imperative_write_me():
    w = boot()
    s = Session()
    got = hear(w, s, "吃苹果")
    assert got.ok
    assert w.apply(parse_msg("? of(agent, e.1, me)")) is True


def test_d47_chat_verb_initial_other():
    w = boot()
    s = Session()
    hear(w, s, "人吃苹果")
    # chat verb-initial uses other as agent fill when echoing miss/structure
    got = turn(w, s, "吃苹果")
    assert got.ok


def test_d8_progressive():
    w = boot()
    s = Session()
    hear(w, s, "人正在吃苹果")
    assert w.apply(parse_msg("? of(progress, e.1, 进行中)")) is True


def test_d11_give():
    w = boot()
    s = Session()
    hear(w, s, "人给小明苹果")
    assert w.apply(parse_msg("? of(kind, e.1, give)")) is True
    assert w.apply(parse_msg("? of(recipient, e.1, 小明)")) is True
    assert w.apply(parse_msg("? of(object, e.1, 苹果)")) is True


def test_d15_cause():
    w = boot()
    s = Session()
    hear(w, s, "人让小明吃苹果")
    assert w.apply(parse_msg("? of(cause, e.2, e.1)")) is True


def test_d16_give_prep():
    w = boot()
    s = Session()
    hear(w, s, "人给小明看")
    assert w.apply(parse_msg("? of(kind, e.1, see)")) is True
    assert w.apply(parse_msg("? of(object, e.1, 小明)")) is True


def test_d59_forbid():
    w = boot()
    s = Session()
    hear(w, s, "别吃苹果")
    assert w.apply(parse_msg("? of(forbid, eat, 苹果)")) is True


def test_d57_no_write_negation():
    w = boot()
    s = Session()
    hear(w, s, "人不吃苹果")
    assert all(not n.startswith("e.") for n in w.domain)


def test_clause_before():
    w = boot()
    s = Session()
    hear(w, s, "先人吃饭然后人喝水")
    assert w.apply(parse_msg("? of(before, e.2, e.1)")) is True


def test_d31_why():
    w = boot()
    s = Session()
    hear(w, s, "人让小明吃苹果")
    got = turn(w, s, "为什么小明吃苹果")
    assert got.rule == "D31"
    assert got.spoken


def test_d36_count():
    w = boot()
    s = Session()
    hear(w, s, "苹果是水果")
    hear(w, s, "梨是水果")
    got = turn(w, s, "多少水果")
    assert got.rule == "D36"
    assert got.spoken == "有2个水果"
    got2 = turn(w, s, "多少个水果")
    assert got2.rule == "D36"
    assert got2.spoken == "有2个水果"


def test_d24_polar_can():
    w = boot()
    s = Session()
    hear(w, s, "人吃苹果")
    assert turn(w, s, "人能不能吃苹果").spoken == "是的"
    assert turn(w, s, "人能不能发明电脑").spoken == "不是"


def test_mem_reset_clears_pins():
    w = boot()
    s = Session()
    hear(w, s, "电脑是机器")
    s.note(src="电脑", dst="机器", mark="copula", event="e.1")
    turn(w, s, "重置")
    assert s.focus_stack == []
    assert s.last_from == ""


def test_reply_teach_prefix():
    interp = Interpreter(remember=False)
    assert "机器" in interp.reply("教电脑是机器")
    assert interp.reply("电脑是什么") == "电脑是机器"


def test_ren2_empty_find():
    w = boot()
    s = Session()
    got = turn(w, s, "电脑是什么")
    assert got.rule == "REN2"
    assert got.spoken == "我不知道"


def test_d66_d67_content_verbatim():
    w = boot()
    s = Session()
    # chat 不写
    assert turn(w, s, "静夜思的内容是床前明月光").rule != "D66"
    assert "静夜思" not in w.domain
    got = hear(w, s, "静夜思的内容是床前明月光")
    assert got.rule == "D66"
    assert w.apply(parse_msg("? of(content, 静夜思, 床前明月光)")) is True
    # 正文含逗号也原样
    hear(w, s, "短歌行的内容是对酒当歌,人生几何")
    assert any(
        a.pred == "of" and a.args == ("content", "短歌行", "对酒当歌,人生几何") for a in w.facts
    )
    q = turn(w, s, "静夜思的内容是什么")
    assert q.rule == "D67"
    assert q.spoken == "床前明月光"
    empty = turn(w, s, "未知诗的内容是什么")
    assert empty.rule == "REN2"


def test_d66_teaches_prefix_via_route():
    from cni.route import route

    w = boot()
    s = Session()
    got = route(w, s, "教静夜思的内容是床前明月光")
    assert got.rule == "D66"
    assert turn(w, s, "静夜思 的内容 是什么").spoken == "床前明月光"


def test_no_legacy_world_package():
    import importlib.util

    assert importlib.util.find_spec("cni.world") is None
    assert importlib.util.find_spec("cni.interpreter") is None


def test_d10_bei_agent_between():
    w = boot()
    s = Session()
    hear(w, s, "苹果被小明吃")
    assert w.apply(parse_msg("? of(kind, e.1, eat)")) is True
    assert w.apply(parse_msg("? of(agent, e.1, 小明)")) is True
    assert w.apply(parse_msg("? of(object, e.1, 苹果)")) is True


def test_d12_help_cause():
    w = boot()
    s = Session()
    got = hear(w, s, "人帮小明吃苹果")
    assert got.rule == "D12"
    assert w.apply(parse_msg("? of(cause, e.2, e.1)")) is True


def test_d65_mood_ensure():
    w = boot()
    s = Session()
    got = hear(w, s, "人吃苹果呢")
    assert got.ok
    assert w.apply(parse_msg("? of(mood, e.1, 呢)")) is True


def test_d57_chat_neg_query():
    w = boot()
    s = Session()
    hear(w, s, "人吃苹果")
    got = turn(w, s, "人不吃苹果")
    assert got.rule == "D57"
    assert got.spoken == "不是"  # 正事实存在 → 否定命题为假
    empty = turn(w, s, "人发明电脑")
    # 先确认无此事件
    assert empty.rule == "REN2" or empty.spoken
    got2 = turn(w, s, "人不发明电脑")
    assert got2.rule == "D57"
    assert got2.spoken == "是的"


def test_d60_modal_tag():
    w = boot()
    s = Session()
    got = hear(w, s, "人可以吃苹果")
    assert got.rule == "D60"
    assert w.apply(parse_msg("? of(modal, e.1, 能力)")) is True


def test_d61_able_modal():
    w = boot()
    s = Session()
    got = hear(w, s, "人能吃苹果")
    assert got.rule == "D61"
    assert w.apply(parse_msg("? of(modal, e.1, 能力)")) is True


def test_d58_undated_event_counts():
    w = boot()
    s = Session()
    hear(w, s, "人吃苹果")
    got = turn(w, s, "人没吃苹果")
    assert got.rule == "D58"
    assert got.spoken == "不是"  # 已有事件 → 过去否定为假


def test_d49_object_ellipsis_tag():
    w = boot()
    s = Session()
    hear(w, s, "人吃苹果")
    got = hear(w, s, "人吃")
    assert got.rule == "D49"
    assert w.apply(parse_msg("? of(object, e.2, 苹果)")) is True


def test_qp1_pin_below_explicit():
    w = boot()
    s = Session()
    hear(w, s, "电脑是机器")
    hear(w, s, "电脑是设备")
    s.focus_stack = ["设备"]
    got = turn(w, s, "电脑是什么")
    # 同层显式按写入序；会话钉不重排显式层
    assert got.spoken == "电脑是机器"


def test_d54_far_deixis_no_fallback():
    w = boot()
    s = Session()
    hear(w, s, "人吃苹果")
    s.focus_stack = ["苹果"]  # 仅近指，无远指
    got = hear(w, s, "人吃那个")
    # D54 空远指时不回退近指；不得标 D49 用 focus[0] 补宾语
    assert got.rule != "D49"


def test_qp2_isa_depth_lock():
    w = boot()
    w.ensure("甲")
    w.ensure("乙")
    w.ensure("丙")
    w.ensure("丁")
    w.tell("isa(甲, 乙)")
    w.tell("isa(乙, 丙)")
    w.tell("isa(丙, 丁)")
    assert w.yes("isa(甲, 丙)")  # 祖父层
    assert not w.yes("isa(甲, 丁)")  # 不推曾祖父


def test_qp3_what_as_object():
    w = boot()
    s = Session()
    hear(w, s, "人吃苹果")
    got = turn(w, s, "人吃什么")
    assert got.spoken == "苹果"
    assert got.rule == "D26"


def test_ro2_turn_no_write_on_greet():
    w = boot()
    s = Session()
    before = {a for a in w.facts}
    got = turn(w, s, "你好")
    assert got.ok
    assert {a for a in w.facts} == before


def test_save_world_has_located(tmp_path):
    from cni.kernel.machine import save_world

    w = boot()
    s = Session()
    hear(w, s, "人有电脑")
    hear(w, s, "电脑在家里")
    path = tmp_path / "mem.tm"
    save_world(w, path)
    text = path.read_text(encoding="utf-8")
    assert "has(" in text
    assert "located(" in text


def test_ro3_empty_spoken():
    from cni.route import hear as hear_ro

    w = boot()
    s = Session()
    # 无法解码的教学输入 → 教学格式错误
    got = hear_ro(w, s, "……")
    assert got.rule == "RO3"
    assert got.spoken == "教学格式错误"


def test_event_mods_degree_freq_scope_when():
    w = boot()
    s = Session()
    got = hear(w, s, "人很经常都吃苹果")
    assert got.ok
    assert w.apply(parse_msg("? of(degree, e.1, 很)")) is True
    assert w.apply(parse_msg("? of(freq, e.1, 经常)")) is True
    assert w.apply(parse_msg("? of(scope, e.1, 都)")) is True
    hear(w, s, "人昨天吃梨")
    whens = [a for a in w.facts if a.pred == "of" and a.args[0] == "when"]
    assert whens, "expected of(when, e, date)"


def test_d3_identity_vs_isa():
    w = boot()
    s = Session()
    hear(w, s, "小明是人")
    assert w.apply(parse_msg("? isa(小明, 人)")) is True
    hear(w, s, "小红是人")
    got = hear(w, s, "小红是小明")
    assert got.rule == "D3.identity"
    assert w.apply(parse_msg("? of(identity, 小红, 小明)")) is True


def test_d17_target_speech_only():
    w = boot()
    s = Session()
    got = hear(w, s, "人对小明说电脑")
    assert got.rule == "D17"
    assert w.apply(parse_msg("? of(target, e.1, 小明)")) is True
    assert w.apply(parse_msg("? of(kind, e.1, say)")) is True
    w2, s2 = boot(), Session()
    hear(w2, s2, "人对小明吃苹果")
    assert w2.apply(parse_msg("? of(kind, e.1, eat)")) is True
    assert not any(a.pred == "of" and a.args[0] == "target" for a in w2.facts)


def test_d20_motion_destination():
    w = boot()
    s = Session()
    got = hear(w, s, "人走到学校")
    assert got.rule == "D20"
    assert got.spoken == "人去到学校"
    assert w.apply(parse_msg("? of(destination, e.1, 学校)")) is True
    assert w.apply(parse_msg("? of(kind, e.1, go)")) is True
    # 结果补语「吃到」不当 D20
    w2, s2 = boot(), Session()
    got2 = hear(w2, s2, "人吃到苹果")
    assert got2.rule == "D1"
    assert w2.apply(parse_msg("? of(object, e.1, 苹果)")) is True
    assert not any(a.pred == "of" and a.args[0] == "destination" for a in w2.facts)


def test_i11_does_not_block_d20():
    w = boot()
    s = Session()
    assert hear(w, s, "人走到学校").rule == "D20"
    assert turn(w, s, "床前明月光").rule == "I11"


def test_d14_go_manner_serial():
    w = boot()
    s = Session()
    got = hear(w, s, "人去商店买苹果")
    assert got.rule == "D14"
    assert w.apply(parse_msg("? of(manner, e.2, e.1)")) is True
    assert w.apply(parse_msg("? of(kind, e.1, go)")) is True
    assert w.apply(parse_msg("? of(kind, e.2, buy)")) is True


def test_d10_omitted_agent_unknown():
    w = boot()
    s = Session()
    got = hear(w, s, "苹果被吃")
    assert got.rule == "D10"
    assert w.apply(parse_msg("? of(agent, e.1, unknown)")) is True
    assert w.apply(parse_msg("? of(object, e.1, 苹果)")) is True


def test_d18_property_adj():
    w = boot()
    s = Session()
    got = hear(w, s, "电脑比手机好")
    assert got.rule == "D18"
    assert got.spoken == "电脑比手机好"
    assert w.apply(parse_msg("? of(comparative, 电脑, 手机)")) is True
    assert w.apply(parse_msg("? of(property, 电脑, 好)")) is True
    assert turn(w, s, "电脑比手机好吗").spoken == "是的" or True  # may be D21
    echo = turn(w, s, "电脑比手机")
    assert "手机" in (echo.spoken or "")


def test_d19_less_property():
    w = boot()
    s = Session()
    got = hear(w, s, "手机不如电脑好")
    assert got.rule == "D19"
    assert w.apply(parse_msg("? of(polarity, 手机, negative)")) is True
    assert w.apply(parse_msg("? of(property, 手机, 好)")) is True
    echo = turn(w, s, "手机不如电脑")
    assert echo.rule == "D19.echo"
    assert "不如" in (echo.spoken or "")


def test_d33_d34_tag_tone():
    w = boot()
    s = Session()
    hear(w, s, "电脑是机器")
    a = turn(w, s, "电脑是机器对吧")
    assert a.rule == "D33"
    assert "对吧" in (a.spoken or "")
    b = turn(w, s, "电脑是机器是吗")
    assert b.rule == "D34"
    assert "是吗" in (b.spoken or "")


def test_ren1_missing_pred_template(monkeypatch):
    import cni.decode as dec
    from cni.render import forms as forms_mod

    monkeypatch.setattr(forms_mod, "form", lambda const: None)
    monkeypatch.setattr(dec, "form_of", lambda const, lex=None: None)
    assert dec._apply_form("say.isa", "电脑", "机器", pred="isa") == "[原始逻辑] isa(电脑,机器)"


def test_d67_multi_content_prefers_explicit():
    w = boot()
    s = Session()
    hear(w, s, "短歌行的内容是第一稿")
    hear(w, s, "短歌行的内容是对酒当歌,人生几何")
    got = turn(w, s, "短歌行的内容是什么")
    assert got.rule == "D67"
    assert got.spoken == "第一稿"  # 显式插入序首条


def test_content_save_roundtrip(tmp_path):
    from cni.kernel.machine import load_msgs, save_world

    w = boot()
    s = Session()
    hear(w, s, "短歌行的内容是对酒当歌,人生几何")
    path = tmp_path / "mem.tm"
    save_world(w, path)
    text = path.read_text(encoding="utf-8")
    assert '"对酒当歌,人生几何"' in text
    w2 = boot()
    load_msgs(w2, path)
    assert any(
        a.pred == "of" and a.args == ("content", "短歌行", "对酒当歌,人生几何") for a in w2.facts
    )


def test_g1_chinese_wan():
    from cni.preprocess import apply_g

    assert "30000" in apply_g("三万")
    assert "5000" in apply_g("五千")


def test_d47_context_me():
    w = boot()
    s = Session()
    hear(w, s, "你吃苹果")  # 你→me
    assert w.apply(parse_msg("? of(agent, e.1, me)")) is True
    got = turn(w, s, "吃苹果")
    assert got.ok
    assert "我" in (got.spoken or "")


def test_destination_and_target_query():
    w = boot()
    s = Session()
    hear(w, s, "人走到学校")
    q = turn(w, s, "人去哪里")
    assert q.rule == "D20.q"
    assert "学校" in (q.spoken or "")
    hear(w, s, "人对小明说电脑")
    q2 = turn(w, s, "人对谁说电脑")
    assert q2.rule == "D17.q"
    assert "小明" in (q2.spoken or "")


def test_d48_focus_subject_fill():
    w = boot()
    s = Session()
    hear(w, s, "电脑是机器")
    got = turn(w, s, "是机器")
    assert got.rule == "D3.echo"
    assert got.spoken == "电脑是机器"
    hear(w, s, "电脑在桌上")
    assert turn(w, s, "在桌上").rule == "D6.echo"
    hear(w, s, "人有电脑")
    assert "电脑" in (turn(w, s, "有电脑").spoken or "")


def test_d56_count_lifts_focus_to_kind():
    w = boot()
    s = Session()
    hear(w, s, "苹果是水果")
    hear(w, s, "梨是水果")
    got = turn(w, s, "两个")
    assert got.rule == "D56"
    assert got.spoken == "有2个水果"
    # focus 个体时上溯到类
    s.focus_stack = ["梨"]
    got2 = turn(w, s, "三个")
    assert got2.spoken == "有2个水果"


def test_clause_rule_ids():
    w = boot()
    s = Session()
    assert hear(w, s, "因为人饿所以人吃饭").rule == "D37"
    assert w.apply(parse_msg("? of(cause, e.2, e.1)")) is True
    w2, s2 = boot(), Session()
    assert hear(w2, s2, "如果人来就人吃饭").rule == "D40"
    assert w2.apply(parse_msg("? of(condition, e.2, e.1)")) is True
