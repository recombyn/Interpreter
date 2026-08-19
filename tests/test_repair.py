from cni.world.lang import boot
from cni.world.translate import decode, hear, turn


def _seed(text: str):
    world = boot()
    senses = decode(text)
    assert senses is not None
    assert hear(world, senses) is True
    return world


def test_homophone_copula_after_seed():
    world = _seed("电脑是机器")
    assert turn(world, "电脑时机器") == "电脑是机器"


def test_near_name_after_seed():
    world = _seed("电脑是机器")
    assert turn(world, "电脑是机气") == "电脑是机器"


def test_wrong_kind_does_not_write():
    world = _seed("电脑是机器")
    assert turn(world, "电脑是桥梁") == "电脑是机器"
    assert "桥梁" not in world.domain


def test_loc_homophone_and_near_place():
    world = _seed("电脑在桌上")
    assert turn(world, "电脑再桌上") == "电脑在桌上"
    assert turn(world, "电脑在卓上") == "电脑在桌上"


def test_repair_does_not_invent_on_empty_world():
    world = boot()
    assert turn(world, "电脑时机器") is None
    assert turn(world, "电脑是机气") is None


def test_repair_negative_extra_and_missing_and_pinyin():
    world = _seed("电脑是机器")
    assert turn(world, "电电脑是机器") is None
    assert turn(world, "电脑机器") is None
    assert turn(world, "diannao是机器") is None
