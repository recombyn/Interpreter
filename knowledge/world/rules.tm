# Rule set for forward inference (isa/of only).
# Syntax:
#   rule <name>: ATOM ∧ ATOM => ATOM
#   Variables start with ? and are shared by exact name.

rule isa.trans: isa(?a, ?b) ∧ isa(?b, ?c) => isa(?a, ?c)
