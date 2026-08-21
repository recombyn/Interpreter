from datetime import date

from para.kernel import boot, parse_msg
from para.preprocess import (
    apply_f_order,
    apply_g,
    apply_user_dict,
    load_user_dict,
    preprocess,
)
from para.route import hear, turn
from para.session import Session


def test_g_quantity_and_dates():
    today = date(2026, 8, 20)
    assert "100000" in apply_g("粉丝10w", today=today)
    assert "3000" in apply_g("3千", today=today)
    assert "1000000" in apply_g("1m", today=today)
    assert apply_g("昨天", today=today) == "2026-08-19"
    assert apply_g("后天", today=today) == "2026-08-22"
    assert apply_g("下周一", today=today) == "2026-08-24"
    assert "30" in apply_g("几十个")
    assert "3-5" in apply_g("三五个")
    assert "70%" in apply_g("大半")
    assert "5分钟" in apply_g("一小会儿")


def test_user_dict_f_and_h():
    assert "永远的神" in apply_user_dict("yyds")
    assert "什么" in apply_user_dict("神马")
    assert "检查" in apply_user_dict("check一下")
    assert "更新" in apply_user_dict("update")
    assert "打电话" in apply_user_dict("call")
    assert load_user_dict()  # sample dict non-empty


def test_f41_50_order_only_hardcoded():
    assert "有没有" in apply_f_order("有冇电脑")
    assert "正在吃饭" in apply_f_order("紧食饭")
    # F1–40 not hard-coded: without dict, yyds stays as-is
    from para.preprocess import apply_f_order as fo

    assert fo("yyds") == "yyds"


def test_f41_50_guide_examples():
    # F41 guide: dialect "eat first" → "first eat"; includes look-verb dialect
    assert apply_f_order("食先") == "先食"
    assert apply_f_order("睇先") == "先睇"
    assert apply_f_order("吃饭先") == "先吃饭"
    # Do not false-split a two-character verb before "first"
    assert apply_f_order("读写先") == "读写先"
    # F48
    assert apply_f_order("去学校先") == "先去学校"
    # F42
    assert apply_f_order("有吃饭") == "曾吃饭过" or apply_f_order("有吃") == "曾吃过"
    assert apply_f_order("有吃") == "曾吃过"
    assert apply_f_order("有食") == "曾食过"
    # F43 sentence-final punctuation
    assert apply_f_order("给本书我。") == "给我本书。"
    assert apply_f_order("给苹果我") == "给我苹果"
    # F44
    assert apply_f_order("苹果大过橙子") == "苹果比橙子大"
    assert apply_f_order("他高过我很多") == "他比我高很多"
    # F45 / F46
    assert "了" in apply_f_order("食咗")
    assert apply_f_order("系咪机器") == "是不是机器"
    # F47
    assert apply_f_order("紧睇") == "正在看"
    assert apply_f_order("紧食") == "正在吃"
    # F49 source slot
    assert apply_f_order("小明来的") == "小明是从哪里来"
    assert apply_f_order("小明来的？") == "小明是从哪里来？"
    # F50
    assert apply_f_order("讲这件事我知") == "告诉我这件事"
    assert apply_f_order("讲我知") == "告诉我"


def test_g_relative_days_longest_and_week():
    today = date(2026, 8, 20)  # Thursday
    assert apply_g("大后天", today=today) == "2026-08-23"
    assert apply_g("大前天", today=today) == "2026-08-17"
    assert "大" not in apply_g("大后天", today=today)
    assert apply_g("上周三", today=today) == "2026-08-19"
    assert apply_g("这周一", today=today) == "2026-08-17"


def test_i_hardcoded_intercepts():
    w = boot()
    s = Session()
    assert turn(w, s, "谢谢").spoken == "不客气"
    assert turn(w, s, "thx").spoken == "不客气"  # user_dict thx→谢谢 → I1
    assert turn(w, s, "hello").spoken == "你好！"  # user_dict hello→你好 → I2
    assert turn(w, s, "bye").spoken == "再见！"  # user_dict bye→再见 → I3
    assert turn(w, s, "哦").spoken == "我知道了"


def test_no_system_english_lex():
    """System does not load English lex; without dict, pure English does not take greet decode."""
    from para.decode.lex import pick_lex
    from pathlib import Path
    from para.paths import WORLD_DIR

    assert pick_lex("hello").name == "ch"
    assert not (WORLD_DIR / "lex.en.tm").is_file()
    w = boot()
    s = Session()
    # Temp: without hello mapping, pure-English open name must not tag greet
    from para.decode import decode
    from para.preprocess import apply_user_dict

    # Decode English directly (bypass user_dict) → non-greet system path
    got = decode(w, s, "hello", write=False)
    assert got.rule != "greet"


def test_user_dict_does_not_double_expand_prefix():
    """map 试用→试用期 must not turn 试用期 into 试用期期."""
    assert apply_user_dict("试用期六个月合法吗", mapping=[("试用", "试用期")]) == "试用期六个月合法吗"
    assert apply_user_dict("试用六个月", mapping=[("试用", "试用期")]) == "试用期六个月"


def test_i11_poetry_before_d():
    w = boot()
    s = Session()
    msg = "我擅长处理事实性问题，不懂诗词赏析。"
    got = turn(w, s, "床前明月光")
    assert got.rule == "I11"
    assert got.spoken == msg
    # Two 5/7-char verse lines
    assert turn(w, s, "床前明月光，疑是地上霜").rule == "I11"
    # Classical particles
    assert turn(w, s, "学而时习之").rule == "I11"
    # Interrogative present → do not trigger; take query path
    assert turn(w, s, "床前明月光是什么").rule != "I11"
    assert turn(w, s, "电脑是什么").rule != "I11"
    # D66 teach-content not blocked by I11
    assert hear(w, s, "静夜思的内容是床前明月光").rule == "D66"
    # 5-char SVO with modern verb 打 must not be treated as verse
    assert hear(w, s, "小明打小红").rule != "I11"


def test_i4_emoji_via_user_dict_not_auto_mood():
    """😂 becomes literal via dict; kernel no longer attaches mood."""
    w = boot()
    s = Session()
    hear(w, s, "人吃饭😂")
    # Must not auto-attach a mood fact for emoji
    assert w.apply(parse_msg("? of(mood, e.1, 开心)")) is not True


def test_pipeline_user_dict_then_d():
    w = boot()
    s = Session()
    got = hear(w, s, "人update电脑")
    assert got.ok
    assert w.apply(parse_msg("? of(kind, e.1, updatev)")) is True


def test_preprocess_notes_no_i4():
    got = preprocess("人吃饭！！", vocab=set(), known=set())
    assert "I7" in got.notes
    assert got.emphasis == "高"
