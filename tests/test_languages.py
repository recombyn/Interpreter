from cni.interpreter import Interpreter


def test_chinese_hello_world():
    reply = Interpreter().reply("你好")
    assert reply == "你好"
