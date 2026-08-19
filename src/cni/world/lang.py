"""Machine world language: sorts, preds, acts. Not human syntax."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from cni.paths import RUNTIME_DIR, WORLD_DIR
from cni.world.parser import WorldParseError, _clean, _closed_at, _split_args

LANG_PATH = WORLD_DIR / "lang.tm"
BASE_PATH = WORLD_DIR / "base.tm"
RULES_PATH = WORLD_DIR / "rules.tm"
MEMORY_PATH = RUNTIME_DIR / "world.tm"

_ATOM = re.compile(r"^(\S+)\(([^()]*)\)\s*$")
_TELL = re.compile(r"^\+\s*(.+)$")
_DROP = re.compile(r"^-\s*(.+)$")
_FIND_CALL = re.compile(
    r"^find\(\?([A-Za-z_][\w]*)(?::(\S+))?,\s*(.+)\)\s*$"
)
_FIND = re.compile(r"^\?([A-Za-z_][\w]*)\s*:\s*(\S+)\s+(.+)$")
_FIND_BARE = re.compile(r"^\?([A-Za-z_][\w]*)\s+(.+)$")
_YESNO = re.compile(r"^\?\s*(.+)$")
_INTRO = re.compile(r"^!\s*(\S+)\s*:\s*(\S+)\s*$")
_AND = re.compile(r"\s*∧\s*|\s*/\\\s*")
_LANG_HEADER = re.compile(r"^lang\s+(\S+)\s*\{\s*$")
_SORT = re.compile(r"^sort\s+(\S+)(?:\s*<\s*(\S+))?\s*$")
_PRED = re.compile(r"^pred\s+(\S+)\(([^()]*)\)\s*$")
_ACT = re.compile(r"^act\s+(\S+)\s*$")
_RULE = re.compile(r"^rule\s+(\S+)\s*:\s*(.+?)\s*(?:=>|⇒)\s*(.+)$")


@dataclass
class Sort:
    name: str
    parent: str = ""


@dataclass
class Pred:
    name: str
    args: list[str] = field(default_factory=list)


@dataclass
class WorldLang:
    name: str = ""
    sorts: list[Sort] = field(default_factory=list)
    preds: list[Pred] = field(default_factory=list)
    acts: list[str] = field(default_factory=list)
    source: str = ""


def parse_lang(text: str, filename: str = "<lang>") -> WorldLang:
    lines = text.splitlines()
    header_line = 0
    while header_line < len(lines) and not _clean(lines[header_line]):
        header_line += 1
    if header_line >= len(lines):
        raise WorldParseError("empty lang", filename, 1)
    header = _clean(lines[header_line])
    match = _LANG_HEADER.match(header)
    if match is None:
        raise WorldParseError("expected 'lang <name> {'", filename, header_line + 1)
    lang = WorldLang(name=match.group(1), source=filename)
    closed_line = _closed_at(lines, header_line + 1, filename, "lang")
    for line_no, raw in enumerate(lines[header_line + 1 : closed_line - 1], start=header_line + 2):
        line = _clean(raw)
        if not line:
            continue
        if sort := _SORT.match(line):
            lang.sorts.append(Sort(sort.group(1), sort.group(2) or ""))
            continue
        if pred := _PRED.match(line):
            lang.preds.append(
                Pred(pred.group(1), _split_args(pred.group(2), filename, line_no))
            )
            continue
        if act := _ACT.match(line):
            lang.acts.append(act.group(1))
            continue
        raise WorldParseError(f"unknown lang statement: {line}", filename, line_no)
    return lang


def kernel(path: Path | None = None) -> WorldLang:
    path = path or LANG_PATH
    return parse_lang(path.read_text(encoding="utf-8"), filename=str(path))


def load_msgs(machine: MachineWorld, path: Path) -> None:
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = _clean(raw)
        if line:
            machine.apply(parse_msg(line, filename=str(path), line=line_no))


def _parse_rule_atom(text: str, filename: str, line: int) -> Goal:
    atom = _ATOM.match(text.strip())
    if atom is None:
        raise WorldParseError("rule needs pred(...)", filename, line)
    return Goal(atom.group(1), _split_args(atom.group(2), filename, line))


def parse_rules(text: str, filename: str = "<rules>") -> tuple[Rule, ...]:
    allowed = {"isa", "of"}
    rules: list[Rule] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = _clean(raw)
        if not line:
            continue
        rule = _RULE.match(line)
        if rule is None:
            raise WorldParseError(f"bad rule: {line}", filename, line_no)
        lhs = tuple(
            _parse_rule_atom(part, filename, line_no)
            for part in _AND.split(rule.group(2))
            if part.strip()
        )
        if not lhs:
            raise WorldParseError("rule needs lhs atoms", filename, line_no)
        rhs = _parse_rule_atom(rule.group(3), filename, line_no)
        if any(goal.pred not in allowed for goal in lhs) or rhs.pred not in allowed:
            raise WorldParseError("rule uses non-kernel predicate", filename, line_no)
        rules.append(Rule(name=rule.group(1), lhs=lhs, rhs=rhs))
    return tuple(rules)


def load_rules(path: Path | None = None) -> tuple[Rule, ...]:
    path = path or RULES_PATH
    if not path.exists():
        return ()
    return parse_rules(path.read_text(encoding="utf-8"), filename=str(path))


def save_world(machine: MachineWorld, path: Path | None = None) -> None:
    path = path or MEMORY_PATH
    kernel = set()
    for raw in BASE_PATH.read_text(encoding="utf-8").splitlines():
        line = _clean(raw)
        if line.startswith("!"):
            kernel.add(line[1:].split(":", 1)[0].strip())
    lines: list[str] = ["# remembered world"]
    for name, sort in machine.domain.items():
        if name not in kernel:
            lines.append(f"! {name} : {sort}")
    for fact in sorted(machine.facts, key=lambda item: (item.pred, item.args)):
        if fact.pred == "isa":
            lines.append(f"+ isa({fact.args[0]}, {fact.args[1]})")
        elif fact.pred == "of":
            lines.append(f"+ of({', '.join(fact.args)})")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def boot(
    path: Path | None = None,
    memory_path: Path | None = None,
    rules_path: Path | None = None,
    infer_depth: int = 2,
) -> MachineWorld:
    """Kernel plus closed names. Open-class names later use intro."""
    machine = MachineWorld(kernel(path), rules=load_rules(rules_path), infer_depth=infer_depth)
    load_msgs(machine, BASE_PATH)
    if memory_path is not None and memory_path.exists():
        load_msgs(machine, memory_path)
    return machine


@dataclass
class Goal:
    pred: str
    args: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Rule:
    name: str
    lhs: tuple[Goal, ...]
    rhs: Goal


@dataclass
class Msg:
    act: str
    pred: str = ""
    args: list[str] = field(default_factory=list)
    goals: list[Goal] = field(default_factory=list)
    var: str = ""
    var_sort: str = ""
    const: str = ""
    sort: str = ""


@dataclass(frozen=True)
class Atom:
    pred: str
    args: tuple[str, ...]


@dataclass(frozen=True)
class FindResult:
    """One-variable find. Generation reads `values` or `rows`."""

    var: str
    values: tuple[str, ...] = ()

    @property
    def rows(self) -> list[dict[str, str]]:
        return [{self.var: value} for value in self.values]


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
            if atom not in self.facts:
                self.facts.add(atom)
                self.inferred.discard(atom)
                self._infer_forward()
            return None
        if msg.act == "drop":
            atom = self._atom(msg)
            self.facts.discard(atom)
            self.inferred.discard(atom)
            return None
        if msg.act == "yesno":
            return self._atom(msg) in self.facts
        if msg.act == "find":
            return self._find(msg)
        raise ValueError(f"unknown act: {msg.act}")

    def query(self, text: str) -> FindResult:
        msg = parse_msg(text)
        if msg.act != "find":
            raise ValueError("query needs a find")
        return self._find(msg)

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
        if msg.goals:
            return msg.goals
        return [Goal(msg.pred, list(msg.args))]

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
        return FindResult(var=msg.var, values=tuple(dict.fromkeys(hits)))

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
        for _ in range(self.infer_depth):
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

    def inference_stats(self) -> dict[str, int]:
        return {"rules": len(self.rules), "inferred_facts": self.inferred_count}

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
                continue
            args.append(token)
        trial = Msg(act="tell", pred=goal.pred, args=args)
        return self._atom(trial)

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


def _hole(arg: str, var: str, filename: str, line: int) -> str:
    if arg == f"?{var}" or arg == var:
        return var
    if arg.startswith("?"):
        raise WorldParseError("find binds one variable", filename, line)
    return arg


def _parse_goals(body: str, var: str, filename: str, line: int) -> list[Goal]:
    parts = [part.strip() for part in _AND.split(body) if part.strip()]
    if not parts:
        raise WorldParseError("find needs pred(...)", filename, line)
    goals: list[Goal] = []
    for part in parts:
        atom = _ATOM.match(part)
        if atom is None:
            raise WorldParseError("find needs pred(...)", filename, line)
        args = [
            _hole(arg, var, filename, line)
            for arg in _split_args(atom.group(2), filename, line)
        ]
        goals.append(Goal(atom.group(1), args))
    return goals


def _find_msg(
    var: str, var_sort: str, body: str, filename: str, line: int
) -> Msg:
    goals = _parse_goals(body, var, filename, line)
    first = goals[0]
    return Msg(
        act="find",
        var=var,
        var_sort=var_sort or "e",
        pred=first.pred,
        args=list(first.args),
        goals=goals,
    )


def parse_msg(text: str, filename: str = "<msg>", line: int = 1) -> Msg:
    text = _clean(text)
    if not text:
        raise WorldParseError("empty msg", filename, line)
    if intro := _INTRO.match(text):
        return Msg(act="intro", const=intro.group(1), sort=intro.group(2))
    if find := _FIND_CALL.match(text):
        return _find_msg(
            find.group(1), find.group(2) or "e", find.group(3).strip(), filename, line
        )
    if find := _FIND.match(text):
        return _find_msg(find.group(1), find.group(2), find.group(3).strip(), filename, line)
    if find := _FIND_BARE.match(text):
        return _find_msg(find.group(1), "e", find.group(2).strip(), filename, line)
    if tell := _TELL.match(text):
        atom = _ATOM.match(tell.group(1).strip())
        if atom is None:
            raise WorldParseError("tell needs pred(...)", filename, line)
        return Msg(
            act="tell",
            pred=atom.group(1),
            args=_split_args(atom.group(2), filename, line),
        )
    if drop := _DROP.match(text):
        atom = _ATOM.match(drop.group(1).strip())
        if atom is None:
            raise WorldParseError("drop needs pred(...)", filename, line)
        return Msg(
            act="drop",
            pred=atom.group(1),
            args=_split_args(atom.group(2), filename, line),
        )
    if yesno := _YESNO.match(text):
        atom = _ATOM.match(yesno.group(1).strip())
        if atom is None:
            raise WorldParseError("yesno needs pred(...)", filename, line)
        return Msg(
            act="yesno",
            pred=atom.group(1),
            args=_split_args(atom.group(2), filename, line),
        )
    raise WorldParseError(f"unknown msg: {text}", filename, line)
