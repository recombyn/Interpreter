"""Message and language parsing for the machine world."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from cni.kernel.tmutil import ParseError, clean, closed_at, split_args

_ATOM = re.compile(r"^(\S+)\(([^()]*)\)\s*$")
_TELL = re.compile(r"^\+\s*(.+)$")
_DROP = re.compile(r"^-\s*(.+)$")
_FIND_CALL = re.compile(r"^find\(\?([A-Za-z_][\w]*)(?::(\S+))?,\s*(.+)\)\s*$")
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
    var: str
    values: tuple[str, ...] = ()

    @property
    def rows(self) -> list[dict[str, str]]:
        return [{self.var: value} for value in self.values]


def parse_lang(text: str, filename: str = "<lang>") -> WorldLang:
    lines = text.splitlines()
    header_line = 0
    while header_line < len(lines) and not clean(lines[header_line]):
        header_line += 1
    if header_line >= len(lines):
        raise ParseError("empty lang", filename, 1)
    header = clean(lines[header_line])
    match = _LANG_HEADER.match(header)
    if match is None:
        raise ParseError("expected 'lang <name> {'", filename, header_line + 1)
    lang = WorldLang(name=match.group(1), source=filename)
    end = closed_at(lines, header_line + 1, filename, "lang")
    for line_no, raw in enumerate(lines[header_line + 1 : end - 1], start=header_line + 2):
        line = clean(raw)
        if not line:
            continue
        if sort := _SORT.match(line):
            lang.sorts.append(Sort(sort.group(1), sort.group(2) or ""))
            continue
        if pred := _PRED.match(line):
            lang.preds.append(Pred(pred.group(1), split_args(pred.group(2), filename, line_no)))
            continue
        if act := _ACT.match(line):
            lang.acts.append(act.group(1))
            continue
        raise ParseError(f"unknown lang statement: {line}", filename, line_no)
    return lang


def _parse_rule_atom(text: str, filename: str, line: int) -> Goal:
    atom = _ATOM.match(text.strip())
    if atom is None:
        raise ParseError("rule needs pred(...)", filename, line)
    return Goal(atom.group(1), split_args(atom.group(2), filename, line))


def parse_rules(text: str, filename: str = "<rules>") -> tuple[Rule, ...]:
    allowed = {"isa", "of", "located", "has"}
    rules: list[Rule] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = clean(raw)
        if not line:
            continue
        rule = _RULE.match(line)
        if rule is None:
            raise ParseError(f"bad rule: {line}", filename, line_no)
        lhs = tuple(
            _parse_rule_atom(part, filename, line_no)
            for part in _AND.split(rule.group(2))
            if part.strip()
        )
        if not lhs:
            raise ParseError("rule needs lhs atoms", filename, line_no)
        rhs = _parse_rule_atom(rule.group(3), filename, line_no)
        if any(g.pred not in allowed for g in lhs) or rhs.pred not in allowed:
            raise ParseError("rule uses non-kernel predicate", filename, line_no)
        rules.append(Rule(name=rule.group(1), lhs=lhs, rhs=rhs))
    return tuple(rules)


def _hole(arg: str, var: str, filename: str, line: int) -> str:
    if arg == f"?{var}" or arg == var:
        return var
    if arg.startswith("?"):
        raise ParseError("find binds one variable", filename, line)
    return arg


def _parse_goals(body: str, var: str, filename: str, line: int) -> list[Goal]:
    parts = [part.strip() for part in _AND.split(body) if part.strip()]
    if not parts:
        raise ParseError("find needs pred(...)", filename, line)
    goals: list[Goal] = []
    for part in parts:
        atom = _ATOM.match(part)
        if atom is None:
            raise ParseError("find needs pred(...)", filename, line)
        args = [_hole(a, var, filename, line) for a in split_args(atom.group(2), filename, line)]
        goals.append(Goal(atom.group(1), args))
    return goals


def _find_msg(var: str, var_sort: str, body: str, filename: str, line: int) -> Msg:
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
    text = clean(text)
    if not text:
        raise ParseError("empty msg", filename, line)
    if intro := _INTRO.match(text):
        return Msg(act="intro", const=intro.group(1), sort=intro.group(2))
    if find := _FIND_CALL.match(text):
        return _find_msg(find.group(1), find.group(2) or "e", find.group(3).strip(), filename, line)
    if find := _FIND.match(text):
        return _find_msg(find.group(1), find.group(2), find.group(3).strip(), filename, line)
    if find := _FIND_BARE.match(text):
        return _find_msg(find.group(1), "e", find.group(2).strip(), filename, line)
    if tell := _TELL.match(text):
        atom = _ATOM.match(tell.group(1).strip())
        if atom is None:
            raise ParseError("tell needs pred(...)", filename, line)
        return Msg(act="tell", pred=atom.group(1), args=split_args(atom.group(2), filename, line))
    if drop := _DROP.match(text):
        atom = _ATOM.match(drop.group(1).strip())
        if atom is None:
            raise ParseError("drop needs pred(...)", filename, line)
        return Msg(act="drop", pred=atom.group(1), args=split_args(atom.group(2), filename, line))
    if yesno := _YESNO.match(text):
        atom = _ATOM.match(yesno.group(1).strip())
        if atom is None:
            raise ParseError("yesno needs pred(...)", filename, line)
        return Msg(act="yesno", pred=atom.group(1), args=split_args(atom.group(2), filename, line))
    raise ParseError(f"unknown msg: {text}", filename, line)


def load_lang(path: Path) -> WorldLang:
    return parse_lang(path.read_text(encoding="utf-8"), filename=str(path))


def load_rules(path: Path) -> tuple[Rule, ...]:
    if not path.exists():
        return ()
    return parse_rules(path.read_text(encoding="utf-8"), filename=str(path))
