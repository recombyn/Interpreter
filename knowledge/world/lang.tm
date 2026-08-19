# World-Lang kernel. This file is the grammar. Human lex is ch.tm / en.tm.
#
# Sort
#   one sort: e
#   every constant is introduced as `! NAME : e`
#
# Predicates (only these two)
#   isa(x, y)           x is a y
#   of(rel, src, dst)   src stands in relation rel to dst
#   rel itself is a constant. New relations are names in base.tm, not new preds.
#
# Acts (wire form)
#   intro   ! NAME : e
#   tell    + isa(...)     or  + of(...)
#   drop    - isa(...)     or  - of(...)
#   yesno   ? isa(...)     or  ? of(...)
#   find    ?x:e ATOM      or  ?x ATOM     (sort defaults to e)
#   find    find(?x[:e], ATOM ∧ ATOM ∧ ...)
#   find binds one variable. Multi-condition uses conjunction, not new predicates.
#
# Variables
#   ?x or ?X in find. Same name in the atom marks the hole.
#   Example: ?x isa(x, invent)
#   Example: ?x:e of(to, e.1, x)
#
# Names
#   ordinary   any intro'd constant (电脑, zhang.1, y.1946)
#   event      e.n  n = 1,2,3...   intro then isa(e.n, KIND) then of(...)
#   year       y.DIGITS            spoken as DIGITS
#   closed     names listed in base.tm
#
# Default content (no learning)
#   greet              你好 / hello
#   isa(me, 机器语言TM) 你是谁 / who are you → 我是机器语言TM
#   Closed names and rels in base.tm are grammar, not taught facts.
#
# Event paradigm (verbs and speech acts)
#   ! e.1 : e
#   + isa(e.1, invent)
#   + of(do, e.1, 人)
#   + of(to, e.1, 电脑)
#   + of(when, e.1, y.1946)
#   Do not invent a third predicate for events.
#
# Session pegs (facts, not Python fields)
#   of(to, focus, X)
#   of(from, last, X)  of(to, last, Y)  of(with, last, MARK)
#   polar ask: of(with, e.n, polar) and of(pol, e.n, yes|no)
#
# Polarity is not logical negation
#   drop  - isa(x, y)     forget the fact (the world no longer has it)
#   of(pol, e.n, no)      this speech event was negative; the fact may still exist
#   These are not ¬isa(x, y).
#
# Event grain
#   One clause → one event e.n. Do not nest attitude verbs as extra events.
#
# Human fuzz (pre-decode, not kernel)
#   Typos / extra or missing chars / closed-class homophones: repair toward
#   lex forms and already-known names, then decode exact.
#   Repair is a front-end convenience; kernel remains isa/of only.
#
# Rules (in rules.tm, still isa/of only)
#   rule r1: isa(?a, ?b) ∧ isa(?b, ?c) => isa(?a, ?c)
#   Added facts trigger bounded forward chaining.
#
# Out of scope (do not add to the kernel)
#   ¬  ∨  ∀  ∃, backward proof, OWL-style role checks, nested event stacks.
#   Unknown human syntax stays world-miss.

lang mwl {

  sort e

  pred isa(e, e)
  pred of(e, e, e)

  act tell
  act drop
  act yesno
  act find
  act intro

}
