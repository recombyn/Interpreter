# Forward rules. QP2: one forward pass ⇒ 子→父→祖父 only (infer_depth=1).
rule isa.trans: isa(?a, ?b) ∧ isa(?b, ?c) => isa(?a, ?c)
