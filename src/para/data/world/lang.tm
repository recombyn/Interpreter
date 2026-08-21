# Kernel grammar. Human surface forms live in lex.*.tm.
#
# Wire predicates (设计落盘，与 D 表右值一致):
#   isa(e, e)
#   of(e, e, e)       — 角色/链接：agent object kind cause …
#   located(e, e)     — 处所（不再写成 of(located,…)）
#   has(e, e)         — 领属（不再写成 of(has,…)）
#
# event(e)            — ! e.n : e，再挂 of(kind|agent|object, …)
# yesno / find / count / forbid — 动作或查询，不是 pred
#
# Chat never writes; teach/hear writes (RO1–RO3).

lang mwl {

  sort e

  pred isa(e, e)
  pred of(e, e, e)
  pred located(e, e)
  pred has(e, e)

  act tell
  act drop
  act yesno
  act find
  act intro

}
