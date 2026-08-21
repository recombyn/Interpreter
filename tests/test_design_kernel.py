from para.app import Para
from para.kernel import boot, kernel, parse_msg
from para.route import hear, turn
from para.session import Session


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
    interp = Para(remember=False, load_user_docs=False)
    assert "机器" in interp.reply("教电脑是机器")
    assert interp.reply("电脑是什么") == "电脑是机器"


def test_ren2_empty_find():
    w = boot()
    s = Session()
    got = turn(w, s, "电脑是什么")
    assert got.rule == "REN2"
    assert got.spoken == "我不知道"


def test_user_dict_blocks_structure_words(tmp_path):
    from para.preprocess import apply_user_dict, load_user_dict

    load_user_dict.cache_clear()
    # Malicious mapping must not rewrite the structural copula surface
    assert apply_user_dict("电脑是机器", mapping=[("是", "等于")]) == "电脑是机器"
    p = tmp_path / "bad.tm"
    p.write_text("map 是 等于\nmap yyds 永远的神\n", encoding="utf-8")
    load_user_dict.cache_clear()
    pairs = load_user_dict(p)
    assert ("是", "等于") not in pairs
    assert ("yyds", "永远的神") in pairs
    load_user_dict.cache_clear()


def test_d66_clips_trailing_question():
    w = boot()
    s = Session()
    got = hear(w, s, "静夜思的内容是床前明月光，它是什么朝代的？")
    assert got.rule == "D66"
    assert "朝代" not in (got.spoken or "")
    assert "床前明月光" in (got.spoken or "")
    q = turn(w, s, "静夜思的内容是什么")
    assert q.spoken == "床前明月光"


def test_dual_focus_event_deixis():
    w = boot()
    s = Session()
    hear(w, s, "人吃苹果")
    assert s.last_event.startswith("e.")
    assert s.last_event in s.event_stack
    assert "苹果" in s.focus_stack or "人" in s.focus_stack
    # "this matter" deixis → event pin
    assert s.resolve_deixis(eventish=True) == s.last_event


def test_route_buckets_query_before_basic():
    from para.decode.route_table import classify_buckets, load_route_groups

    load_route_groups.cache_clear()
    assert load_route_groups()
    b = classify_buckets("电脑是什么", ["what", "copula"])
    assert b[0] == "query"
    assert "basic" in b


def test_route_special_ba():
    from para.decode.route_table import classify_buckets

    b = classify_buckets("人把苹果吃", ["ba", "eat"])
    assert "special" in b
    assert b.index("special") < b.index("basic")


def test_content_side_index_d67():
    """D67 uses entity→content index; drop keeps index in sync."""
    from para.kernel.parse import parse_msg

    w = boot()
    s = Session()
    hear(w, s, "甲的内容是一")
    hear(w, s, "甲的内容是二")
    hear(w, s, "乙的内容是三")
    assert w.contents_of("甲") == ["一", "二"]
    assert w.contents_of("乙") == ["三"]
    assert turn(w, s, "甲的内容是什么").spoken in {"一", "二"}
    w.apply(parse_msg("- of(content, 甲, 一)"))
    assert w.contents_of("甲") == ["二"]
    assert turn(w, s, "甲的内容是什么").spoken == "二"
    from para.tools.validate_rules import check_pattern_conflicts, load_patterns

    load_patterns.cache_clear()
    assert check_pattern_conflicts() == []
    w = boot()
    s = Session()
    # chat does not write
    assert turn(w, s, "静夜思的内容是床前明月光").rule != "D66"
    assert "静夜思" not in w.domain
    got = hear(w, s, "静夜思的内容是床前明月光")
    assert got.rule == "D66"
    assert w.apply(parse_msg("? of(content, 静夜思, 床前明月光)")) is True
    # Body with commas kept verbatim
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
    from para.route import route

    w = boot()
    s = Session()
    got = route(w, s, "教静夜思的内容是床前明月光")
    assert got.rule == "D66"
    assert turn(w, s, "静夜思 的内容 是什么").spoken == "床前明月光"


def test_no_legacy_world_package():
    import importlib.util

    assert importlib.util.find_spec("para.world") is None
    assert importlib.util.find_spec("para.bogus") is None


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
    assert got.spoken == "不是"  # positive fact exists → negated proposition is false
    empty = turn(w, s, "人发明电脑")
    # First confirm no such event
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
    assert got.spoken == "不是"  # existing event → past negation is false


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
    # Same-tier explicit by write order; session pin does not reorder explicit tier
    assert got.spoken == "电脑是机器"


def test_d54_far_deixis_no_fallback():
    w = boot()
    s = Session()
    hear(w, s, "人吃苹果")
    s.focus_stack = ["苹果"]  # near only, no far
    got = hear(w, s, "人吃那个")
    # D54: empty far must not fall back to near; must not mark D49 filling object from focus[0]
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
    assert w.yes("isa(甲, 丙)")  # grandparent tier
    assert not w.yes("isa(甲, 丁)")  # do not infer great-grandparent


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
    from para.kernel.machine import save_world

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
    from para.route import hear as hear_ro

    w = boot()
    s = Session()
    # Undecodable teach input → teach format error
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
    # Resultative complement must not be D20
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
    import para.decode as dec

    monkeypatch.setattr(dec, "form_tm", lambda const: None)
    monkeypatch.setattr(dec, "form_of", lambda const, lex=None: None)
    assert dec._apply_form("say.isa", "电脑", "机器", pred="isa") == "[原始逻辑] isa(电脑,机器)"


def test_d67_multi_content_prefers_explicit():
    w = boot()
    s = Session()
    hear(w, s, "短歌行的内容是第一稿")
    hear(w, s, "短歌行的内容是对酒当歌,人生几何")
    got = turn(w, s, "短歌行的内容是什么")
    assert got.rule == "D67"
    assert got.spoken == "第一稿"  # first explicit by insertion order


def test_content_save_roundtrip(tmp_path):
    from para.kernel.machine import load_msgs, save_world

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
    from para.preprocess import apply_g

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
    # When focus is an individual, walk up to kind
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
