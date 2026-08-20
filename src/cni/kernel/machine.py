"""Machine world store. WC1–WC3, QP2 (infer_depth=2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cni.kernel.parse import (
    Atom,
    FindResult,
    Goal,
    Msg,
    Pred,
    Rule,
    WorldLang,
    load_lang,
    load_rules,
    parse_msg,
)
from cni.kernel.tmutil import clean
from cni.paths import RUNTIME_DIR, WORLD_DIR

LANG_PATH = WORLD_DIR / "lang.tm"
BASE_PATH = WORLD_DIR / "base.tm"
RULES_PATH = WORLD_DIR / "rules.tm"
MEMORY_PATH = RUNTIME_DIR / "world.tm"


@dataclass
class MachineWorld:
    lang: WorldLang
    domain: dict[str, str] = field(default_factory=dict)
    facts: set[Atom] = field(default_factory=set)
    inferred: set[Atom] = field(default_factory=set)
    rules: tuple[Rule, ...] = ()
    infer_depth: int = 2
    inferred_count: int = 0

    def apply(self, msg: Msg) -> bool | FindResult | None:
        if msg.act == "intro":
            self._intro(msg.const, msg.sort)
            return None
        if msg.act == "tell":
            atom = self._atom(msg)
            if atom not in self.facts:  # WC1
                self.facts.add(atom)
                self.inferred.discard(atom)
                self._infer_forward()
            return None
        if msg.act == "drop":  # WC3
            atom = self._atom(msg)
            self.facts.discard(atom)
            self.inferred.discard(atom)
            return None
        if msg.act == "yesno":
            return self._atom(msg) in self.facts
        if msg.act == "find":
            return self._find(msg)
        raise ValueError(f"unknown act: {msg.act}")

    def tell(self, text: str) -> None:
        self.apply(parse_msg(f"+ {text}"))

    def drop(self, text: str) -> None:
        self.apply(parse_msg(f"- {text}"))

    def yes(self, text: str) -> bool:
        got = self.apply(parse_msg(f"? {text}"))
        return bool(got)

    def find(self, text: str) -> FindResult:
        msg = parse_msg(text if text.startswith("?") or text.startswith("find") else f"?x {text}")
        if msg.act != "find":
            raise ValueError("find needs a find message")
        return self._find(msg)

    def ensure(self, name: str, sort: str = "e") -> None:
        if name not in self.domain:
            self._intro(name, sort)

    def _intro(self, const: str, sort: str) -> None:
        if sort not in self._sorts():
            raise ValueError(f"unknown sort: {sort}")
        have = self.domain.get(const)
        if have and have != sort:
            raise ValueError(f"const already sorted: {const}")
        self.domain[const] = sort

    def _atom(self, msg: Msg) -> Atom:
        spec = self._pred(msg.pred)
        if spec is None:
            raise ValueError(f"unknown pred: {msg.pred}")
        if len(spec.args) != len(msg.args):
            raise ValueError(f"wrong arity: {msg.pred}")
        for arg, need in zip(msg.args, spec.args, strict=True):
            actual = self.domain.get(arg)
            if actual is None:
                raise ValueError(f"unknown const: {arg}")
            if not self._fits(actual, need):
                raise ValueError(f"wrong sort for {msg.pred}: {arg}")
        return Atom(msg.pred, tuple(msg.args))

    def _goals(self, msg: Msg) -> list[Goal]:
        return msg.goals or [Goal(msg.pred, list(msg.args))]

    def _find(self, msg: Msg) -> FindResult:
        goals = self._goals(msg)
        if not goals:
            raise ValueError("find needs a pred")
        if not any(msg.var in goal.args for goal in goals):
            raise ValueError("find variable not used")
        for goal in goals:
            spec = self._pred(goal.pred)
            if spec is None:
                raise ValueError(f"unknown pred: {goal.pred}")
            if len(spec.args) != len(goal.args):
                raise ValueError(f"wrong arity: {goal.pred}")
        hits: list[str] = []
        for cand in self._candidates(msg, goals):
            env = {msg.var: cand}
            if all(self._holds(goal, env) for goal in goals):
                hits.append(cand)
        # QP1: explicit > inferred; within tier, non-events before event log
        explicit = [h for h in hits if not self._value_only_inferred(msg, goals, h)]
        inferred = [h for h in hits if h not in explicit]

        def _tier(vals: list[str]) -> list[str]:
            non_ev = [v for v in vals if not v.startswith("e.")]
            ev = [v for v in vals if v.startswith("e.")]
            return [*non_ev, *ev]

        ordered = list(dict.fromkeys([*_tier(explicit), *_tier(inferred)]))
        return FindResult(var=msg.var, values=tuple(ordered))

    def _value_only_inferred(self, msg: Msg, goals: list[Goal], value: str) -> bool:
        env = {msg.var: value}
        for goal in goals:
            resolved = tuple(env.get(a, a) for a in goal.args)
            atom = Atom(goal.pred, resolved)
            if atom in self.facts and atom not in self.inferred:
                return False
        return True

    def _candidates(self, msg: Msg, goals: list[Goal]) -> list[str]:
        found: list[str] = []
        for goal in goals:
            if msg.var not in goal.args:
                continue
            spec = self._pred(goal.pred)
            if spec is None:
                continue
            for fact in self.facts:
                if fact.pred != goal.pred:
                    continue
                bound = ""
                ok = True
                for got, pat, need in zip(fact.args, goal.args, spec.args, strict=True):
                    if pat == msg.var:
                        if not self._fits(self.domain.get(got, ""), msg.var_sort or need):
                            ok = False
                            break
                        if bound and bound != got:
                            ok = False
                            break
                        bound = got
                    elif got != pat:
                        ok = False
                        break
                if ok and bound:
                    found.append(bound)
        return list(dict.fromkeys(found))

    def _holds(self, goal: Goal, env: dict[str, str]) -> bool:
        resolved: list[str] = []
        for arg in goal.args:
            name = env.get(arg, arg)
            if name not in self.domain:
                return False
            resolved.append(name)
        return Atom(goal.pred, tuple(resolved)) in self.facts

    def _infer_forward(self) -> None:
        if not self.rules or self.infer_depth <= 0:
            return
        for _ in range(self.infer_depth):  # QP2
            added = False
            for rule in self.rules:
                for env in self._rule_envs(rule.lhs):
                    atom = self._rule_atom(rule.rhs, env)
                    if atom is None or atom in self.facts:
                        continue
                    self.facts.add(atom)
                    self.inferred.add(atom)
                    self.inferred_count += 1
                    added = True
            if not added:
                break

    def _rule_envs(self, lhs: tuple[Goal, ...]) -> list[dict[str, str]]:
        envs: list[dict[str, str]] = [{}]
        for goal in lhs:
            next_envs: list[dict[str, str]] = []
            for env in envs:
                next_envs.extend(self._match_goal(goal, env))
            envs = next_envs
            if not envs:
                break
        return envs

    def _match_goal(self, goal: Goal, env: dict[str, str]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for fact in self.facts:
            if fact.pred != goal.pred:
                continue
            trial = dict(env)
            ok = True
            for pat, got in zip(goal.args, fact.args, strict=True):
                if pat.startswith("?"):
                    prev = trial.get(pat)
                    if prev is None:
                        trial[pat] = got
                    elif prev != got:
                        ok = False
                        break
                elif pat != got:
                    ok = False
                    break
            if ok:
                out.append(trial)
        return out

    def _rule_atom(self, goal: Goal, env: dict[str, str]) -> Atom | None:
        args: list[str] = []
        for token in goal.args:
            if token.startswith("?"):
                bound = env.get(token)
                if bound is None:
                    return None
                args.append(bound)
            else:
                args.append(token)
        return self._atom(Msg(act="tell", pred=goal.pred, args=args))

    def _pred(self, name: str) -> Pred | None:
        return next((pred for pred in self.lang.preds if pred.name == name), None)

    def _sorts(self) -> dict[str, str]:
        return {sort.name: sort.parent for sort in self.lang.sorts}

    def _fits(self, actual: str, need: str) -> bool:
        current = actual
        seen: set[str] = set()
        parents = self._sorts()
        while current and current not in seen:
            if current == need:
                return True
            seen.add(current)
            current = parents.get(current, "")
        return False


def load_msgs(machine: MachineWorld, path: Path) -> None:
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = clean(raw)
        if line:
            machine.apply(parse_msg(line, filename=str(path), line=line_no))


def boot(
    path: Path | None = None,
    memory_path: Path | None = None,
    rules_path: Path | None = None,
    infer_depth: int = 2,
) -> MachineWorld:
    machine = MachineWorld(
        load_lang(path or LANG_PATH),
        rules=load_rules(rules_path or RULES_PATH),
        infer_depth=infer_depth,
    )
    load_msgs(machine, BASE_PATH)
    if memory_path is not None and memory_path.exists():
        load_msgs(machine, memory_path)
    return machine


def save_world(machine: MachineWorld, path: Path | None = None) -> None:
    path = path or MEMORY_PATH
    kernel: set[str] = set()
    stock: set[str] = set()
    for raw in BASE_PATH.read_text(encoding="utf-8").splitlines():
        line = clean(raw)
        if line.startswith("!"):
            kernel.add(line[1:].split(":", 1)[0].strip())
        elif line.startswith("+"):
            stock.add(line)
    lines = ["# remembered world"]
    for name, sort in machine.domain.items():
        if name not in kernel:
            lines.append(f"! {name} : {sort}")
    for fact in sorted(machine.facts, key=lambda item: (item.pred, item.args)):
        if fact.pred == "isa":
            told = f"+ isa({fact.args[0]}, {fact.args[1]})"
        elif fact.pred == "of":
            told = f"+ of({', '.join(fact.args)})"
        else:
            continue
        if told in stock:
            continue
        lines.append(told)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def kernel(path: Path | None = None) -> WorldLang:
    return load_lang(path or LANG_PATH)
