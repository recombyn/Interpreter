# out templates: const → surface. Missing → REN1 bare logic.
out greet 你好
out yes 是的
out no 不是
out unknown_q 我不知道
out unknown_info 我不了解这个信息
out teach_err 教学格式错误
out rhetorical 我不知道
out count 有{0}个
out ambig 这句话可能有多种理解。请说得更具体一些。
out judge_ask 请问具体数值是多少？

form isa {
  out say.isa {0}是{1}
}
form located {
  out say.located {0}在{1}
}
form has {
  out say.has {0}有{1}
}
form identity {
  out say.identity {0}是{1}
}
form event {
  out say.event {0}{1}{2}
}
