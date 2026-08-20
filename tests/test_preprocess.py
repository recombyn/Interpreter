from datetime import date

from cni.kernel import boot, parse_msg
from cni.preprocess import (
    apply_f_order,
    apply_g,
    apply_user_dict,
    load_user_dict,
    preprocess,
)
from cni.route import hear, turn
from cni.session import Session


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
    assert load_user_dict()  # 示例词典非空


def test_f41_50_order_only_hardcoded():
    assert "有没有" in apply_f_order("有冇电脑")
    assert "正在吃饭" in apply_f_order("紧食饭")
    # F1–40 不在硬编码里：无词典时 yyds 原样
    from cni.preprocess import apply_f_order as fo

    assert fo("yyds") == "yyds"


def test_i_hardcoded_intercepts():
    w = boot()
    s = Session()
    assert turn(w, s, "谢谢").spoken == "不客气"
    assert turn(w, s, "thx").spoken == "不客气"  # user_dict thx→谢谢 → I1
    assert turn(w, s, "hello").spoken == "你好！"
    assert turn(w, s, "bye").spoken == "再见！"
    assert turn(w, s, "哦").spoken == "我知道了"


def test_i11_poetry_before_d():
    w = boot()
    s = Session()
    msg = "我擅长处理事实性问题，不懂诗词赏析。"
    got = turn(w, s, "床前明月光")
    assert got.rule == "I11"
    assert got.spoken == msg
    # 五七言两句
    assert turn(w, s, "床前明月光，疑是地上霜").rule == "I11"
    # 之乎者也
    assert turn(w, s, "学而时习之").rule == "I11"
    # 有疑问词 → 不触发，走查询
    assert turn(w, s, "床前明月光是什么").rule != "I11"
    assert turn(w, s, "电脑是什么").rule != "I11"
    # D66 教内容不受 I11 挡
    assert hear(w, s, "静夜思的内容是床前明月光").rule == "D66"


def test_i4_emoji_via_user_dict_not_auto_mood():
    """😂 经词典变成「开心」字面，不再内核挂 mood。"""
    w = boot()
    s = Session()
    hear(w, s, "人吃饭😂")
    # 不应再自动 of(mood, e.1, 开心)
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
