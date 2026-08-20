# Forward rules. QP2: MachineWorld.infer_depth defaults to 2.
rule isa.trans: isa(?a, ?b) ∧ isa(?b, ?c) => isa(?a, ?c)
