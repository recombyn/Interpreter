"""Chinese constructions → isa/of facts. Forms live in ch.tm; open names use intro."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from cni.paths import WORLD_DIR
from cni.text.repair import load_pins, repair_text
from cni.world.lang import BASE_PATH, FindResult, MachineWorld, Msg, parse_msg
from cni.world.parser import WorldParseError, _clean, _closed_at

CH_PATH = WORLD_DIR / "ch.tm"
EN_PATH = WORLD_DIR / "en.tm"
FORM_PATH = WORLD_DIR / "form.tm"
_SKIP = set(" \t\r\n，。！、；：,.!;:()（）")
_CLAUSE = re.compile(r"因为|所以|如果|那么|然后|而且|但是|可是|不过")
_EN_CLAUSE = re.compile(r"\bbecause\b|\bhowever\b|\bbut\b|\bif\b|\bthen\b|\bso\b", re.I)
_OPEN_CHUNK = re.compile(r"\d+|[^\d]+")
_LEX_HEADER = re.compile(r"^lex\s+(\S+)\s*\{\s*$")
_FORM_HEADER = re.compile(r"^form\s+(\S+)\s*\{\s*$")
_USE = re.compile(r"^use\s+(\S+)\s+(\S+)\s+(\S+)\s*$")
_IN = re.compile(r"^in\s+(\S+)\s+(\S+)\s*$")
_OUT = re.compile(r"^out\s+(\S+)\s+(.+)$")

_DEIXIS = {"self": "other", "addr": "me", "this": "this", "that": "that"}
_QUERY = {"who", "where", "what", "how", "whenq"}
_REL = {"greet", "copula", "have", "loc", "nohave"}
_KIND = {"greet", "ask", "say", "want", "order"}
_ASP = {"prog", "pfv", "dur", "exp"}


@dataclass
class Lex:
    name: str
    ins: list[tuple[str, str]] = field(default_factory=list)
    outs: dict[str, str] = field(default_factory=dict)


def parse_lex(text: str, filename: str = "<lex>") -> Lex:
    lines = text.splitlines()
    header_line = 0
    while header_line < len(lines) and not _clean(lines[header_line]):
        header_line += 1
    if header_line >= len(lines):
        raise WorldParseError("empty lex", filename, 1)
    header = _clean(lines[header_line])
    match = _LEX_HEADER.match(header)
    if match is None:
        raise WorldParseError("expected 'lex <name> {'", filename, header_line + 1)
    lex = Lex(name=match.group(1))
    closed_line = _closed_at(lines, header_line + 1, filename, "lex")
    for line_no, raw in enumerate(lines[header_line + 1 : closed_line - 1], start=header_line + 2):
        line = _clean(raw)
        if not line:
            continue
        if incoming := _IN.match(line):
            lex.ins.append((incoming.group(1), incoming.group(2)))
            continue
        if outgoing := _OUT.match(line):
            lex.outs[outgoing.group(1)] = outgoing.group(2)
            continue
        raise WorldParseError(f"unknown lex statement: {line}", filename, line_no)
    return lex


@dataclass(frozen=True)
class FormUse:
    trigger: str
    pred: str
    mark: str


def parse_form(text: str, filename: str = "<form>") -> list[FormUse]:
    lines = text.splitlines()
    header_line = 0
    while header_line < len(lines) and not _clean(lines[header_line]):
        header_line += 1
    if header_line >= len(lines):
        raise WorldParseError("empty form", filename, 1)
    header = _clean(lines[header_line])
    if _FORM_HEADER.match(header) is None:
        raise WorldParseError("expected 'form <name> {'", filename, header_line + 1)
    closed_line = _closed_at(lines, header_line + 1, filename, "form")
    rules: list[FormUse] = []
    for line_no, raw in enumerate(lines[header_line + 1 : closed_line - 1], start=header_line + 2):
        line = _clean(raw)
        if not line:
            continue
        use = _USE.match(line)
        if use is None:
            raise WorldParseError(f"unknown form statement: {line}", filename, line_no)
        rules.append(FormUse(use.group(1), use.group(2), use.group(3)))
    return rules


@lru_cache(maxsize=1)
def load_form(path: Path | None = None) -> tuple[FormUse, ...]:
    path = path or FORM_PATH
    return tuple(parse_form(path.read_text(encoding="utf-8"), filename=str(path)))


@lru_cache(maxsize=8)
def load_lex(path: Path | None = None) -> Lex:
    path = path or CH_PATH
    return parse_lex(path.read_text(encoding="utf-8"), filename=str(path))


@lru_cache(maxsize=1)
def _kernel_names() -> frozenset[str]:
    names: set[str] = set()
    for raw in BASE_PATH.read_text(encoding="utf-8").splitlines():
        line = _clean(raw)
        if not line.startswith("!"):
            continue
        names.add(line[1:].split(":", 1)[0].strip())
    return frozenset(names)


@dataclass(frozen=True)
class Sense:
    name: str
    open: bool = False


def _lex_for(text: str) -> Lex:
    stripped = "".join(ch for ch in text if ch not in _SKIP)
    alpha = sum(1 for ch in stripped if ch.isalpha() and ch.isascii())
    if stripped and alpha >= max(1, (len(stripped) + 1) // 2):
        return load_lex(EN_PATH)
    return load_lex(CH_PATH)


def _match_closed(raw: str, index: int, lex: Lex) -> tuple[str, str] | None:
    forms = sorted(lex.ins, key=lambda item: len(item[0]), reverse=True)
    for form, name in forms:
        if raw.startswith(form, index):
            return form, name
    return None


def _decode_words(text: str, lex: Lex) -> list[Sense] | None:
    forms = {form.casefold(): name for form, name in lex.ins}
    taken: list[Sense] = []
    for raw in text.split():
        word = "".join(ch for ch in raw if ch not in _SKIP)
        if not word:
            continue
        name = forms.get(word.casefold())
        if name in {"skip", "conj"}:
            continue
        if name:
            taken.append(Sense(name))
        else:
            taken.append(Sense(word, open=True))
    return taken or None


def decode(text: str) -> list[Sense] | None:
    lex = _lex_for(text)
    if lex.name == "en":
        return _decode_words(text, lex)
    raw = "".join(ch for ch in text if ch not in _SKIP)
    if not raw:
        return None
    taken: list[Sense] = []
    i = 0
    while i < len(raw):
        closed = _match_closed(raw, i, lex)
        if closed is not None:
            form, name = closed
            if name not in {"skip", "conj"}:
                taken.append(Sense(name))
            i += len(form)
            continue
        start = i
        i += 1
        while i < len(raw) and _match_closed(raw, i, lex) is None:
            i += 1
        for chunk in _OPEN_CHUNK.findall(raw[start:i]):
            taken.append(Sense(chunk, open=True))
    return taken or None


def _fresh(machine: MachineWorld) -> str:
    n = 1
    while f"e.{n}" in machine.domain:
        n += 1
    aid = f"e.{n}"
    machine.apply(Msg(act="intro", const=aid, sort="e"))
    return aid


def _ensure(machine: MachineWorld, name: str) -> None:
    if name not in machine.domain:
        machine.apply(parse_msg(f"! {name} : e"))


def _bind_ana(machine: MachineWorld, senses: list[Sense]) -> list[Sense]:
    bound: list[Sense] = []
    for sense in senses:
        if sense.name != "ana":
            bound.append(sense)
            continue
        topic = _focus_of(machine)
        if topic:
            bound.append(Sense(topic, open=True))
    return bound


def _verb_names(machine: MachineWorld) -> set[str]:
    return set(_find(machine, "?X:e isa(X, verb)"))


def _rel_names(machine: MachineWorld) -> set[str]:
    return set(_find(machine, "?X:e isa(X, rel)"))


def _is_verb(machine: MachineWorld, name: str) -> bool:
    return name in _verb_names(machine)


def _apply_verb(machine: MachineWorld, senses: list[Sense]) -> bool:
    verbs = _verb_names(machine)
    verb = next((sense.name for sense in senses if sense.name in verbs), "")
    if not verb:
        return False
    ents: list[str] = []
    src = ""
    dest = ""
    patient = ""
    agent = ""
    num = ""
    expect = ""
    for sense in senses:
        if sense.name == "src":
            expect = "src"
            continue
        if sense.name == "goal":
            expect = "goal"
            continue
        if sense.name == "ba":
            expect = "ba"
            continue
        if sense.name == "bei":
            expect = "bei"
            continue
        if sense.name in verbs | {"clf", "part", "cmp", "year"} | _ASP:
            continue
        if sense.open and sense.name.isdigit():
            continue
        name = _entity(sense)
        if name is None:
            if sense.name.startswith("n") and sense.name[1:].isdigit():
                num = sense.name
            continue
        if expect == "src":
            src = name
            expect = ""
            continue
        if expect == "goal":
            dest = name
            expect = ""
            continue
        if expect == "ba":
            patient = name
            expect = ""
            continue
        if expect == "bei":
            agent = name
            expect = ""
            continue
        ents.append(name)
    if patient and ents and not dest:
        dest = ents[-1]
        ents = ents[:-1]
    doer = agent
    if not doer and ents:
        doer = ents[0]
        ents = ents[1:]
    elif not doer and not src and not dest:
        doer = "other"
    if verb == "give" and not dest and len(ents) >= 2:
        dest = ents[0]
        ents = ents[1:]
    if agent and ents and not patient:
        done = ents[0]
        if len(ents) > 1 and not dest:
            dest = ents[-1]
    else:
        done = patient or (ents[-1] if ents else "")
    pol = "no" if any(sense.name == "no" for sense in senses) else "yes"
    aid = _write_act(machine, verb, doer, done, pol, False, stamp=True)
    if verb == "call" and doer and done:
        _tell(machine, f"isa({doer}, {done})")
        _tell(machine, f"isa({done}, person)")
    if src:
        _tell(machine, f"of(from, {aid}, {src})")
    if dest:
        _tell(machine, f"of(goal, {aid}, {dest})")
    if num:
        _tell(machine, f"of(with, {aid}, {num})")
    for sense in senses:
        if sense.name in _ASP:
            _tell(machine, f"of(with, {aid}, {sense.name})")
    years = [sense.name for sense in senses if sense.open and sense.name.isdigit()]
    if years:
        year = _year_id(years[0])
        _ensure(machine, year)
        _tell(machine, f"of(when, {aid}, {year})")
    _focus_on(machine, done or doer)
    return True


def _tell(machine: MachineWorld, text: str) -> None:
    machine.apply(parse_msg(f"+ {text}"))


def _drop(machine: MachineWorld, text: str) -> None:
    machine.apply(parse_msg(f"- {text}"))


def _yes(machine: MachineWorld, text: str) -> bool:
    return machine.apply(parse_msg(f"? {text}")) is True


def _entity(sense: Sense) -> str | None:
    if sense.open or sense.name in _QUERY:
        return sense.name
    return _DEIXIS.get(sense.name)


def _apply_copulas(machine: MachineWorld, senses: list[Sense]) -> bool:
    """是 → tell isa; 不是 → drop isa. Several 是 share the last subject."""
    subject = ""
    deny = False
    want_object = False
    applied = False
    for sense in senses:
        if sense.name == "no":
            deny = True
            continue
        if sense.name == "copula":
            want_object = True
            continue
        name = _entity(sense)
        if name is None:
            continue
        if want_object:
            if not subject:
                return applied
            atom = f"isa({subject}, {name})"
            if deny:
                _drop(machine, atom)
            else:
                for old in _isa_kinds(machine, subject, include_inferred=True):
                    if old != name:
                        _drop(machine, f"isa({subject}, {old})")
                _tell(machine, atom)
            deny = False
            want_object = False
            applied = True
            _note_last(machine, subject, name, "copula")
            _focus_on(machine, subject)
            continue
        subject = name
    return applied


def _write_act(
    machine: MachineWorld,
    kind: str,
    agent: str,
    patient: str,
    pol: str,
    asking: bool,
    stamp: bool = False,
) -> str:
    aid = _fresh(machine)
    _tell(machine, f"isa({aid}, {kind})")
    if asking and kind != "ask":
        _tell(machine, f"isa({aid}, ask)")
    if agent:
        _tell(machine, f"of(do, {aid}, {agent})")
    if patient:
        _tell(machine, f"of(to, {aid}, {patient})")
    if stamp:
        _tell(machine, f"of(when, {aid}, now)")
    _tell(machine, f"of(pol, {aid}, {pol})")
    return aid


def _find(machine: MachineWorld, text: str) -> list[str]:
    found = machine.apply(parse_msg(text))
    return list(found.values) if isinstance(found, FindResult) else []


def _edges(machine: MachineWorld, rel: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for fact in machine.facts:
        if fact.pred == "of" and fact.args[0] == rel:
            hits.append((fact.args[1], fact.args[2]))
    return hits


def _role(machine: MachineWorld, aid: str, rel: str) -> str:
    for src, dst in _edges(machine, rel):
        if src == aid:
            return dst
    return ""


def _roles(machine: MachineWorld, aid: str, rel: str) -> list[str]:
    return [dst for src, dst in _edges(machine, rel) if src == aid]


def _clear_role(machine: MachineWorld, rel: str, src: str) -> None:
    for dst in _find(machine, f"?X:e of({rel}, {src}, X)"):
        _drop(machine, f"of({rel}, {src}, {dst})")


def _focus_on(machine: MachineWorld, name: str) -> None:
    if not name:
        return
    _clear_role(machine, "to", "focus")
    _tell(machine, f"of(to, focus, {name})")


def _focus_of(machine: MachineWorld) -> str:
    hits = _find(machine, "?X:e of(to, focus, X)")
    return hits[0] if hits else ""


def _note_last(machine: MachineWorld, src: str, dst: str, mark: str) -> None:
    _clear_role(machine, "from", "last")
    _clear_role(machine, "to", "last")
    _clear_role(machine, "with", "last")
    _tell(machine, f"of(from, last, {src})")
    _tell(machine, f"of(to, last, {dst})")
    _tell(machine, f"of(with, last, {mark})")


def _year_id(raw: str) -> str:
    digits = raw[2:] if raw.startswith("y.") else raw
    return f"y.{digits}" if digits.isdigit() else raw


def _year_text(const: str) -> str:
    if const.startswith("y.") and const[2:].isdigit():
        return const[2:]
    return const


def _subject(senses: list[Sense]) -> str:
    for sense in senses:
        name = _entity(sense)
        if name and name not in _QUERY:
            return name
    return ""


def _query_name(senses: list[Sense]) -> str:
    for sense in senses:
        if sense.name in _QUERY:
            return sense.name
    return ""


def _mapped(name: str) -> str:
    return _DEIXIS.get(name, name)


def _pair_ents(senses: list[Sense]) -> list[str]:
    ents: list[str] = []
    for sense in senses:
        name = _entity(sense)
        if name and name not in _QUERY:
            ents.append(_mapped(name) if sense.name in _DEIXIS else name)
    return ents


def _hear_polar(machine: MachineWorld, senses: list[Sense], names: list[str]) -> bool:
    ents = _pair_ents(senses)
    if len(ents) < 2:
        return False
    left, right = ents[0], ents[1]
    mark = "copula"
    if "loc" in names:
        ok = _yes(machine, f"of(at, {left}, {right})")
        mark = "at"
    elif "cmp" in names:
        ok = _yes(machine, f"of(than, {left}, {right})")
        mark = "than"
    elif "with" in names:
        ok = _yes(machine, f"of(with, {left}, {right})")
        mark = "with"
    elif "have" in names or "nohave" in names:
        ok = _yes(machine, f"of(has, {left}, {right})")
        mark = "has"
    else:
        ok = _yes(machine, f"isa({left}, {right})")
    aid = _write_act(machine, "ask", "other", "me", "yes" if ok else "no", False)
    _tell(machine, f"of(with, {aid}, polar)")
    _tell(machine, f"of(with, {aid}, {mark})")
    _note_last(machine, left, right, mark)
    _focus_on(machine, left)
    return True


def _hear_ask(machine: MachineWorld, senses: list[Sense], pol: str) -> bool:
    sub = _subject(senses)
    q = _query_name(senses)
    if not sub:
        return False
    aid = _write_act(machine, "ask", "other", sub, pol, False)
    if q:
        _tell(machine, f"of(with, {aid}, {q})")
    names = [sense.name for sense in senses]
    if "have" in names:
        _tell(machine, f"of(with, {aid}, has)")
    if "invent" in names:
        _tell(machine, f"of(with, {aid}, invent)")
    _focus_on(machine, sub)
    return True


def _isa_kinds(machine: MachineWorld, src: str, include_inferred: bool = True) -> list[str]:
    hits: list[str] = []
    inferred = getattr(machine, "inferred", set())
    for fact in machine.facts:
        if fact.pred != "isa" or fact.args[0] != src:
            continue
        if not include_inferred and fact in inferred:
            continue
        hits.append(fact.args[1])
    skip = _KIND | _QUERY | _ASP | _verb_names(machine) | _rel_names(machine) | {
        "yes",
        "no",
        "last",
        "focus",
        "polar",
        "copula",
        "de",
        "clf",
        "nay",
        "verb",
        "person",
        "rel",
    }
    return sorted({hit for hit in hits if hit not in skip})


def _isa_closed(machine: MachineWorld, src: str, depth: int = 4) -> list[str]:
    seen: list[str] = []
    frontier = [src]
    for _ in range(depth):
        nxt: list[str] = []
        for node in frontier:
            for kind in _isa_kinds(machine, node):
                if kind not in seen and kind != src:
                    seen.append(kind)
                    nxt.append(kind)
        frontier = nxt
    return seen


def _ask_slots(machine: MachineWorld, aid: str) -> set[str]:
    return {dst for src, dst in _edges(machine, "with") if src == aid}


def speak_query(machine: MachineWorld, lex: Lex | None = None) -> str | None:
    def form(const: str) -> str | None:
        return _form(const, lex)

    latest = _latest_act(machine)
    if _act_kind(machine, latest) != "ask":
        return None
    slots = _ask_slots(machine, latest)
    if "polar" in slots:
        return speak(machine, lex)
    sub = _role(machine, latest, "to")
    left = form(sub)
    if not sub or not left:
        return None
    def spoken(template: str | None, *args: str | None) -> str | None:
        return _fill(template, *args)

    def first_dst(template: str | None, values: list[str]) -> str | None:
        for value in values:
            got = spoken(template, left, form(value))
            if got:
                return got
        return None

    if "where" in slots:
        return first_dst(form("ask.where"), _find(machine, f"find(?x, of(at, {sub}, x))"))
    if "whenq" in slots:
        cond = f"of(to, ev, {sub})"
        if "invent" in slots:
            cond = f"{cond} ∧ isa(ev, invent)"
        for event in _find(machine, f"find(?ev, {cond})"):
            times = [
                t
                for t in _find(machine, f"find(?t, of(when, {event}, t))")
                if t != "now"
            ]
            if times:
                got = spoken(form("ask.whenq"), left, _year_text(times[0]))
                if got:
                    return got
        return None
    if "who" in slots:
        return first_dst(
            form("ask.who"),
            _find(machine, f"find(?x, isa({sub}, x) ∧ isa(x, person))"),
        )
    if "what" in slots and "has" in slots:
        return first_dst(form("ask.has"), _find(machine, f"find(?x, of(has, {sub}, x))"))
    if "how" in slots:
        if "invent" in slots:
            events = _find(
                machine, f"find(?ev, of(do, ev, {sub}) ∧ isa(ev, invent))"
            ) or _find(machine, f"find(?ev, of(to, ev, {sub}) ∧ isa(ev, invent))")
        else:
            events = _find(machine, f"find(?ev, of(do, ev, {sub}))") or _find(
                machine, f"find(?ev, of(to, ev, {sub}))"
            )
        for event in events:
            kind = _act_kind(machine, event)
            if kind in {"", "ask", "say", "greet"}:
                continue
            got = spoken(
                form("ask.how"),
                form(sub),
                form(kind),
                form(_role(machine, event, "to")),
            )
            if got:
                return got
        return None
    if "what" in slots:
        kinds = _isa_kinds(machine, sub, include_inferred=False) or _isa_closed(
            machine, sub
        )
        return first_dst(form("ask.what"), kinds)
    return None


def _apply_use(
    machine: MachineWorld,
    senses: list[Sense],
    names: list[str],
    ents: list[str],
    pol: str,
) -> bool:
    for rule in load_form():
        if rule.trigger not in names:
            continue
        if rule.pred == "isa":
            if "loc" in names:
                continue
            if not _apply_copulas(machine, senses):
                return False
            _write_act(machine, "say", "other", "me", pol, False)
            return True
        if len(ents) < 2:
            return False
        left = _DEIXIS.get(ents[0], ents[0])
        right = _DEIXIS.get(ents[1], ents[1])
        atom = f"of({rule.pred}, {left}, {right})"
        drop = rule.trigger == "nohave" or pol == "no"
        if drop:
            _drop(machine, atom)
        else:
            for dst in _find(machine, f"find(?x, of({rule.pred}, {left}, x))"):
                if dst != right:
                    _drop(machine, f"of({rule.pred}, {left}, {dst})")
            _tell(machine, atom)
        _note_last(machine, left, right, rule.mark)
        _focus_on(machine, right if rule.mark == "de" else left)
        _write_act(machine, "say", "other", "me", pol, False)
        return True
    return False


def hear(machine: MachineWorld, senses: list[Sense]) -> bool:
    senses = _bind_ana(machine, senses)
    for sense in senses:
        if sense.open:
            _ensure(machine, sense.name)
    names = [sense.name for sense in senses]
    opens = [sense.name for sense in senses if sense.open]
    pol = "no" if "no" in names else "yes"
    asking = "ask" in names or any(name in _QUERY for name in names)
    ents: list[str] = []
    for sense in senses:
        if sense.name in _DEIXIS or sense.name in _QUERY or sense.open:
            ents.append(sense.name)
    if "greet" in names:
        _write_act(machine, "greet", "other", "me", pol, asking)
        _focus_on(machine, "other")
        return True
    if "why" in names:
        return False
    if "ask" in names and not any(name in _QUERY for name in names):
        return _hear_polar(machine, senses, names)
    if asking:
        return _hear_ask(machine, senses, pol)
    if _apply_use(machine, senses, names, ents, pol):
        return True
    if any(_is_verb(machine, name) for name in names):
        return _apply_verb(machine, senses)
    if "src" in names or "goal" in names:
        return _apply_verb(machine, [*senses, Sense("go")])
    nums = [name for name in names if name.startswith("n") and name[1:].isdigit()]
    if nums and opens:
        _tell(machine, f"of(with, {opens[0]}, {nums[0]})")
        _note_last(machine, opens[0], nums[0], "clf")
        _focus_on(machine, opens[0])
        _write_act(machine, "say", "other", "me", pol, False)
        return True
    if opens:
        _focus_on(machine, opens[0])
        return True
    return False


def _greeted_me(machine: MachineWorld) -> bool:
    found = machine.apply(parse_msg("?X:e isa(X, greet)"))
    if not isinstance(found, FindResult):
        return False
    for aid in found.values:
        if _yes(machine, f"of(do, {aid}, other)") and _yes(machine, f"of(to, {aid}, me)"):
            return True
    return False


def _i_greeted_you(machine: MachineWorld) -> bool:
    found = machine.apply(parse_msg("?X:e isa(X, greet)"))
    if not isinstance(found, FindResult):
        return False
    for aid in found.values:
        if _yes(machine, f"of(do, {aid}, me)") and _yes(machine, f"of(to, {aid}, other)"):
            return True
    return False


def answer(machine: MachineWorld) -> bool:
    if not _greeted_me(machine):
        return False
    if _i_greeted_you(machine):
        return True
    _write_act(machine, "greet", "me", "other", "yes", False)
    return True


def _fill(template: str | None, *args: str | None) -> str | None:
    if not template:
        return None
    text = template
    for index, arg in enumerate(args):
        key = "{" + str(index) + "}"
        if key in text and not arg:
            return None
        text = text.replace(key, arg or "")
    if "{" in text:
        return None
    return text


def _form(const: str, lex: Lex | None = None) -> str | None:
    if lex and const in lex.outs:
        return lex.outs[const]
    if lex and lex.name == "en":
        if const in _kernel_names() or const.startswith("e."):
            return None
        return const
    got = load_lex().outs.get(const)
    if got:
        return got
    if const in _kernel_names() or const.startswith("e."):
        return None
    return const


def _acts(machine: MachineWorld, kind: str) -> list[str]:
    found = machine.apply(parse_msg(f"?X:e isa(X, {kind})"))
    return list(found.values) if isinstance(found, FindResult) else []


def _latest_act(machine: MachineWorld) -> str:
    ids: list[int] = []
    for name in machine.domain:
        if name.startswith("e.") and name[2:].isdigit():
            ids.append(int(name[2:]))
    return f"e.{max(ids)}" if ids else ""


def _act_kind(machine: MachineWorld, aid: str) -> str:
    if not aid:
        return ""
    if _yes(machine, f"isa({aid}, greet)"):
        return "greet"
    if _yes(machine, f"isa({aid}, ask)"):
        return "ask"
    if _yes(machine, f"isa({aid}, say)"):
        return "say"
    for kind in _verb_names(machine):
        if _yes(machine, f"isa({aid}, {kind})"):
            return kind
    return ""


def speak(machine: MachineWorld, lex: Lex | None = None) -> str | None:
    def form(const: str) -> str | None:
        return _form(const, lex)

    def glue(*bits: str | None) -> str:
        parts = [bit for bit in bits if bit]
        if lex and lex.name == "en":
            return " ".join(parts)
        return "".join(parts)

    latest = _latest_act(machine)
    kind = _act_kind(machine, latest) if latest else ""
    if kind == "ask" and _yes(machine, f"of(with, {latest}, polar)"):
        mark = _role(machine, "last", "with")
        src = form(_role(machine, "last", "from"))
        dst = form(_role(machine, "last", "to"))
        yes = _role(machine, latest, "pol") == "yes"
        echoed = _fill(form(f"say.{mark}" if yes else f"nay.{mark}"), src, dst)
        if echoed and src != dst:
            return echoed
        return form("yes" if yes else "nay")
    if kind == "greet" and _role(machine, latest, "do") == "me":
        spoken = _fill(form("say.greet"), form(_role(machine, latest, "to")))
        if spoken:
            return spoken
        if lex and lex.name == "en":
            return form("greet")
        return glue(form(_role(machine, latest, "to")), form("greet"))
    if kind in _verb_names(machine):
        do = form(_role(machine, latest, "do"))
        to = form(_role(machine, latest, "to"))
        verb = form(kind)
        src = form(_role(machine, latest, "from"))
        dest = form(_role(machine, latest, "goal"))
        times = [t for t in _roles(machine, latest, "when") if t != "now"]
        year_bit = glue(_year_text(times[0]), form("year")) if times else None
        asp = next((mark for mark in _ASP if mark in _roles(machine, latest, "with")), "")
        deny = _role(machine, latest, "pol") == "no"
        english = bool(lex and lex.name == "en")
        ditrans = bool(to and dest and kind == "give")
        ba = form("ba") if to and dest and not ditrans and not english else None
        bits = [do]
        if year_bit and not english:
            bits.append(year_bit)
        if asp:
            bits.append(form(asp))
        if deny:
            bits.append(form("no"))
        if ditrans:
            bits += [verb, dest, to]
        elif ba:
            bits += [ba, to, verb, form("goal"), dest]
        else:
            if src:
                bits += [form("from"), src]
            if dest:
                bits += [form("goal"), dest]
            bits.append(verb)
            if to and to not in {src, dest, do}:
                bits.append(to)
            if year_bit and english:
                bits.append(year_bit)
        spoken = glue(*bits)
        if spoken:
            return spoken
    if kind == "say":
        mark = _role(machine, "last", "with")
        src = form(_role(machine, "last", "from"))
        dst = form(_role(machine, "last", "to"))
        if mark == "clf":
            return _fill(form("say.clf"), src, dst)
        return _fill(form(f"say.{mark}"), src, dst)
    return None


def _open_known(machine: MachineWorld) -> list[str]:
    skip = set(_kernel_names())
    names: list[str] = []
    for name in machine.domain:
        if name in skip or name.startswith(("e.", "y.")):
            continue
        if len(name) < 2:
            continue
        names.append(name)
    return names


def repair_input(machine: MachineWorld, text: str, *, toward_names: bool) -> str:
    lex = _lex_for(text)
    closed = [form for form, name in lex.ins if name not in {"skip", "conj"}]
    known = _open_known(machine) if toward_names else []
    raw = text if lex.name == "en" else "".join(ch for ch in text if ch not in _SKIP)
    return repair_text(
        raw,
        closed=closed,
        known=known,
        pins=load_pins() if lex.name == "ch" else {},
        spaced=lex.name == "en",
    )


def _is_query_turn(names: list[str]) -> bool:
    return "greet" in names or "ask" in names or any(name in _QUERY for name in names)


def _echo_known(
    machine: MachineWorld, senses: list[Sense], lex: Lex | None
) -> str | None:
    senses = _bind_ana(machine, senses)
    names = [sense.name for sense in senses]
    ents = _pair_ents(senses)
    if not ents:
        return None
    left = ents[0]

    def form(const: str) -> str | None:
        return _form(const, lex)

    if "copula" in names and "loc" not in names:
        kinds = _isa_kinds(machine, left, include_inferred=False)
        if not kinds:
            return None
        _note_last(machine, left, kinds[0], "copula")
        _focus_on(machine, left)
        return _fill(form("say.copula"), form(left), form(kinds[0]))
    if "loc" in names:
        places = _find(machine, f"find(?x, of(at, {left}, x))")
        if not places:
            return None
        _note_last(machine, left, places[0], "at")
        _focus_on(machine, left)
        return _fill(form("say.at"), form(left), form(places[0]))
    if "have" in names or "nohave" in names:
        owned = _find(machine, f"find(?x, of(has, {left}, x))")
        if not owned:
            return None
        _note_last(machine, left, owned[0], "has")
        _focus_on(machine, left)
        return _fill(form("say.has"), form(left), form(owned[0]))
    if "cmp" in names:
        hits = _find(machine, f"find(?x, of(than, {left}, x))")
        if not hits:
            return None
        _note_last(machine, left, hits[0], "than")
        _focus_on(machine, left)
        return _fill(form("say.than"), form(left), form(hits[0]))
    if "with" in names:
        hits = _find(machine, f"find(?x, of(with, {left}, x))")
        if not hits:
            return None
        _note_last(machine, left, hits[0], "with")
        _focus_on(machine, left)
        return _fill(form("say.with"), form(left), form(hits[0]))
    if "de" in names:
        hits = _find(machine, f"find(?x, of(has, {left}, x))")
        if not hits:
            return None
        _note_last(machine, left, hits[0], "de")
        _focus_on(machine, left)
        return _fill(form("say.de"), form(left), form(hits[0]))
    verbs = _verb_names(machine)
    verb = next((name for name in names if name in verbs), "")
    if verb:
        events = _find(
            machine, f"find(?ev, of(do, ev, {left}) ∧ isa(ev, {verb}))"
        ) or _find(machine, f"find(?ev, of(to, ev, {left}) ∧ isa(ev, {verb}))")
        for event in events:
            if _act_kind(machine, event) in {"", "ask", "say", "greet"}:
                continue
            _focus_on(machine, left)
            return _fill(
                form("ask.how"),
                form(_role(machine, event, "do") or left),
                form(verb),
                form(_role(machine, event, "to")),
            )
    nums = [name for name in names if name.startswith("n") and name[1:].isdigit()]
    opens = [sense.name for sense in senses if sense.open]
    if nums and opens and _yes(machine, f"of(with, {opens[0]}, {nums[0]})"):
        _note_last(machine, opens[0], nums[0], "clf")
        _focus_on(machine, opens[0])
        return _fill(form("say.clf"), form(opens[0]), form(nums[0]))
    return None


def _turn_one(machine: MachineWorld, text: str) -> str | None:
    text = repair_input(machine, text, toward_names=False)
    senses = decode(text)
    if not senses:
        return None
    names = [sense.name for sense in senses]
    if not _is_query_turn(names):
        named = repair_input(machine, text, toward_names=True)
        if named != text:
            text = named
            senses = decode(text)
            if not senses:
                return None
            names = [sense.name for sense in senses]
    lex = _lex_for(text)
    if "why" in names:
        return None
    if _is_query_turn(names):
        before = _latest_act(machine)
        if not hear(machine, senses):
            return None
        latest = _latest_act(machine)
        if latest and _act_kind(machine, latest) == "ask":
            return speak_query(machine, lex)
        answer(machine)
        if latest == before:
            return None
        return speak(machine, lex)
    return _echo_known(machine, senses, lex)


def turn(machine: MachineWorld, text: str) -> str | None:
    splitter = _EN_CLAUSE if _lex_for(text).name == "en" else _CLAUSE
    parts = [part.strip() for part in splitter.split(text) if part.strip()]
    if not parts:
        return None
    causal = bool(_CLAUSE.search(text) or _EN_CLAUSE.search(text))
    spoken: str | None = None
    prev = ""
    for part in parts:
        before = _latest_act(machine)
        got = _turn_one(machine, part)
        after = _latest_act(machine)
        if causal and prev and after and after != prev:
            _tell(machine, f"of(cause, {after}, {prev})")
        if after and after != before:
            prev = after
        spoken = got or spoken
    return spoken
