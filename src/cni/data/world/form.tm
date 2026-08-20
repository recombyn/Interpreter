# 系统默认话术。用户覆盖：knowledge/user/form.tm

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

out polar.mode clause
out polar.default.yes {clause}{pred}
out polar.default.no {clause}{pred}
out polar.affix.neg 不
out polar.neg.有 没有
out polar.neg.没 没有
out polar.neg.是 不是
out polar.neg.会 不会
out polar.neg.能 不能
out polar.neg.该 不该
out polar.neg.愿 不愿
out polar.neg.肯 不肯
out polar.neg.敢 不敢

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
