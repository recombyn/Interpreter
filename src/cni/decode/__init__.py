"""D1–D67: one ordered decoder. write=True → hear; write=False → turn query/echo."""

from __future__ import annotations

from dataclasses import dataclass
import re

from cni.decode import effects as fx
from cni.decode.lex import Sense, form_of, pick_lex, tokenize
from cni.kernel import FindResult, MachineWorld
from cni.session import Session

_D66 = re.compile(r"^(.+?)\s*的内容是\s*(.+)$")
_D67 = re.compile(r"^(.+?)\s*的内容\s*是什么\s*[？?]?\s*$")

_VERBS = {
    "invent",
    "buy",
    "drink",
    "eat",
    "see",
    "go",
    "come",
    "give",
    "put",
    "help",
    "let",
    "invite",
    "call",
    "say",
    "make",
    "use",
    "hit",
    "think",
    "wait",
    "openv",
    "close",
    "live",
    "talk",
    "checkv",
    "holdv",
    "updatev",
    "downloadv",
    "sharev",
    "linkv",
    "copyv",
    "deletev",
    "sendv",
    "phone",
    "callout",
}
_CAUSE_V = {"let", "invite", "call", "help"}
_PERSON = {"me", "other", "unknown"}
_TRANS = {
    "invent",
    "buy",
    "drink",
    "eat",
    "see",
    "give",
    "put",
    "help",
    "hit",
    "use",
    "make",
    "call",
    "openv",
    "close",
}
_INTRANS = {"come", "go", "live", "wait", "talk", "think"}
_MOOD_WORD = {
    "mood_ne": "呢",
    "mood_ba": "吧",
    "mood_a": "啊",
    "mood_o": "哦",
}
_DEG = {
    "deg_high": "很",
    "deg_very": "非常",
    "deg_too": "太",
}
_FREQ = {
    "freq_always": "总是",
    "freq_often": "经常",
    "freq_rare": "偶尔",
}
_SCOPE = {
    "scope_all": "都",
    "scope_only": "只",
    "scope_also": "也",
}
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MOD_NAMES = set(_DEG) | set(_FREQ) | set(_SCOPE)


@dataclass
class Result:
    ok: bool
    spoken: str | None = None
    rule: str = ""
    focus: str = ""
    err: str = ""


def _names(senses: list[Sense]) -> list[str]:
    return [s.name for s in senses]


def _entity(sense: Sense, session: Session) -> str | None:
    # D50–D54
    if sense.name == "self":
        return "me"
    if sense.name == "addr":
        return "other"
    if sense.name == "ana":
        # D52：focus_stack[0]，若无则 intro 新个体
        top = session.focus(0)
        if top:
            return top
        return ""  # 由调用方 intro
    if sense.name == "this":
        return session.focus(0) or ""
    if sense.name == "that":
        # D54：仅远指 focus[1]，不回退到 [0]
        return session.focus(1) or ""
    if sense.open or sense.name not in {
        *_VERBS,
        "copula",
        "have",
        "loc",
        "ba",
        "bei",
        "give_mark",
        "help",
        "let",
        "call",
        "invite",
        "target_mark",
        "cmp",
        "less",
        "dest_mark",
        "go",
        "with_mark",
        "de",
        "ask",
        "polar_isa",
        "polar_have",
        "polar_can",
        "or",
        "tag_right",
        "tag_isa",
        "rhetorical",
        "who",
        "what",
        "where",
        "how",
        "why",
        "howmany",
        "how",
        "clf",
        "n1",
        "n2",
        "n3",
        "n4",
        "n5",
        "n6",
        "n7",
        "n8",
        "n9",
        "n10",
        "polar_can",
        "cause_mark",
        "so_mark",
        "therefore",
        "although",
        "but",
        "if_mark",
        "then_mark",
        "when_mark",
        "first",
        "again",
        "then",
        "not_only",
        "moreover",
        "no",
        "pastneg",
        "forbid",
        "can",
        "must",
        "force",
        "may",
        "greet",
        "self",
        "addr",
        "ana",
        "this",
        "that",
        "mood_ne",
        "mood_ba",
        "mood_a",
        "mood_o",
        "prog",
        "de",
        "deg_high",
        "deg_very",
        "deg_too",
        "freq_always",
        "freq_often",
        "freq_rare",
        "scope_all",
        "scope_only",
        "scope_also",
    }:
        if sense.name in _VERBS:
            return None
        return sense.name
    return None


def _ents(senses: list[Sense], session: Session, machine: MachineWorld | None = None) -> list[str]:
    out: list[str] = []
    for sense in senses:
        if sense.name == "ana" and not session.focus(0):
            # D52：无 focus 则 intro
            name = sense.surface or "他"
            if machine is not None:
                fx.ensure(machine, name)
            out.append(name)
            continue
        name = _entity(sense, session)
        if name:
            out.append(name)
    return out


def _verbs_in(senses: list[Sense]) -> list[tuple[int, str]]:
    base = [(i, s.name) for i, s in enumerate(senses) if s.name in _VERBS]
    give_marks = [i for i, s in enumerate(senses) if s.name == "give_mark"]
    if give_marks and not base:
        # D11 给 as main verb
        return [(give_marks[0], "give")]
    # D16 给 as preposition: ignore give_mark as verb
    return base


def _mood(senses: list[Sense]) -> str:
    for s in senses:
        if s.name in _MOOD_WORD:
            return _MOOD_WORD[s.name]
    return ""


def _extract_mods(senses: list[Sense], ents: list[str]) -> tuple[str, str, str, str]:
    """程度/频率/范围/时间（含 G 注入的绝对日期）。"""
    degree = freq = scope = when = ""
    for s in senses:
        if s.name in _DEG:
            degree = _DEG[s.name]
        elif s.name in _FREQ:
            freq = _FREQ[s.name]
        elif s.name in _SCOPE:
            scope = _SCOPE[s.name]
    for e in ents:
        if _ISO_DATE.match(e):
            when = e
            break
    return degree, freq, scope, when


def _strip_dates(ents: list[str]) -> list[str]:
    return [e for e in ents if not _ISO_DATE.match(e)]


def _is_kind_name(machine: MachineWorld, name: str) -> bool:
    """曾作 isa(_, name) 的类名。"""
    return any(a.pred == "isa" and a.args[1] == name for a in machine.facts)


def _is_individual_name(machine: MachineWorld, name: str) -> bool:
    """表语为个体：已在域内、不作类、且为人称或已有实例身份。"""
    if name not in machine.domain:
        return False
    if _is_kind_name(machine, name):
        return False
    if name in _PERSON or machine.yes(f"isa({name}, person)"):
        return True
    return any(a.pred == "isa" and a.args[0] == name for a in machine.facts)


def _prefer(session: Session, values: tuple[str, ...] | list[str]) -> str:
    """QP1：取 find 已排序的首项（显式>推导>…）；会话钉不压过显式。"""
    del session
    if not values:
        return ""
    return values[0]


def _fill_ellipsis(senses: list[Sense], session: Session, *, write: bool) -> list[Sense]:
    # D47 verb-initial → other；上下文指向 me 时用 me；D7 teach/write → me
    if not senses:
        return senses
    names = _names(senses)
    if names[0] in _VERBS or names[0] == "give_mark":
        if write:
            agent = "me"
        elif session.last_from == "me" or session.focus(0) == "me":
            agent = "me"
        else:
            agent = "other"
        return [Sense(agent, open=False), *senses]
    if names[0] in {"copula", "have", "loc"}:
        top = session.focus(0) or "other"
        return [Sense(top, open=True), *senses]
    return senses


def _modal(senses: list[Sense]) -> tuple[str, str]:
    """返回 (modal常量, 规则号)。表：能力/义务/强制/可能。"""
    for s in senses:
        if s.name == "can":
            return "能力", "D60"
        if s.name == "must":
            return "义务", "D62"
        if s.name == "force":
            return "强制", "D63"
        if s.name == "may":
            return "可能", "D64"
    return "", ""


def _neg(senses: list[Sense]) -> str:
    names = _names(senses)
    if "forbid" in names:
        return "forbid"
    if "pastneg" in names:
        return "past"
    if "no" in names:
        return "no"
    return ""


def _personish(name: str, machine: MachineWorld) -> bool:
    if name in _PERSON:
        return True
    if name not in machine.domain:
        return False
    return machine.yes(f"isa({name}, person)")


def _placeish(name: str, machine: MachineWorld) -> bool:
    if name in {"here"}:
        return True
    if name not in machine.domain:
        return False
    return machine.yes(f"isa({name}, place)")


def _say_isa(subj: str, kind: str) -> str:
    return f"{_surf(subj)}是{_surf(kind)}"


def _surf(name: str) -> str:
    from cni.render.forms import form as form_tm

    got = form_of(name) or form_tm(name)
    if got:
        return got
    if name == "me":
        return "我"
    if name == "other":
        return "你"
    return name


def _ren1(pred: str, *args: str) -> str:
    """REN1: fact exists but no surface template."""
    return f"[原始逻辑] {pred}({','.join(args)})"


def _yes() -> str:
    from cni.render.forms import form as form_tm

    return form_of("yes") or form_tm("yes") or "是的"


def _no() -> str:
    from cni.render.forms import form as form_tm

    return form_of("no") or form_tm("no") or "不是"


def _empty_q() -> str:
    """REN2 question: the rule ran and find returned empty."""
    from cni.render.forms import form as form_tm

    return form_of("unknown_q") or form_tm("unknown_q") or "我不知道"


def _empty_info() -> str:
    """REN2 statement: the rule ran and find returned empty."""
    from cni.render.forms import form as form_tm

    return form_of("unknown_info") or form_tm("unknown_info") or "我不了解这个信息"


def _role(machine: MachineWorld, src: str, rel: str) -> str:
    hits = machine.find(f"?x of({rel}, {src}, x)")
    return hits.values[0] if hits.values else ""


def _speak_event(machine: MachineWorld, eid: str) -> str:
    kind = _role(machine, eid, "kind")
    agent = _role(machine, eid, "agent")
    obj = _role(machine, eid, "object")
    if not kind:
        return _ren1("event", eid)
    from cni.render.forms import form as form_tm

    kind_surf = form_of(kind) or form_tm(kind)
    if not kind_surf:
        # REN1：有事件、无 kind 表面模板
        parts = [eid, kind]
        if agent:
            parts.append(agent)
        if obj:
            parts.append(obj)
        return _ren1("of", *parts)
    if agent and obj:
        return f"{_surf(agent)}{kind_surf}{_surf(obj)}"
    if agent:
        return f"{_surf(agent)}{kind_surf}"
    return _ren1("of", "kind", eid, kind)


def _events(
    machine: MachineWorld,
    *,
    kind: str = "",
    agent: str = "",
    obj: str = "",
    before_now: bool = False,
) -> list[str]:
    from datetime import date

    out: list[str] = []
    today = date.today().isoformat()
    for name in list(machine.domain):
        if not name.startswith("e."):
            continue
        if kind and not machine.yes(f"of(kind, {name}, {kind})"):
            continue
        if agent and not machine.yes(f"of(agent, {name}, {agent})"):
            continue
        if obj and not machine.yes(f"of(object, {name}, {obj})"):
            continue
        if before_now:
            # D58：仅保留 of(when,e,t) 且 t < now 的事件；无 when 则不计入过去否定命中
            whens = machine.find(f"?x of(when, {name}, x)")
            if not whens.values:
                continue
            if not any(t < today for t in whens.values):
                continue
        if kind or agent or obj:
            out.append(name)
    return out


def _decode_neg_query(
    machine: MachineWorld,
    session: Session,
    core: list[Sense],
    *,
    neg: str,
) -> Result:
    """D57/D58 闲聊：对去否定后的命题做存在查询并取反；D58 仅计 at_time < now。"""
    names = _names(core)
    ents = _ents(core, session, machine)
    past = neg == "past"
    rule = "D58" if past else "D57"

    def _flip(ok: bool) -> Result:
        # 否定命题：正事实存在 → 答「不是」；不存在 → 「是的」
        return Result(ok=True, spoken=_yes() if (not ok) else _no(), rule=rule)

    if "copula" in names and len(ents) >= 2:
        ok = machine.yes(f"isa({ents[0]}, {ents[1]})") or machine.yes(
            f"of(identity, {ents[0]}, {ents[1]})"
        )
        return _flip(ok)
    if "have" in names and len(ents) >= 2:
        a, b = ents[0], ents[1]
        ok = machine.yes(f"has({a}, {b})") or machine.yes(f"located({b}, {a})")
        return _flip(ok)
    if "loc" in names and len(ents) >= 2:
        ok = machine.yes(f"located({ents[0]}, {ents[1]})")
        return _flip(ok)
    verbs = _verbs_in(core)
    if verbs:
        kind = verbs[0][1]
        vi = verbs[0][0]
        agent = (_ents(core[:vi], session, machine) or [""])[0]
        obj = (_ents(core[vi + 1 :], session, machine) or [""])[0]
        ok = bool(_events(machine, kind=kind, agent=agent, obj=obj, before_now=past))
        return _flip(ok)
    return Result(ok=False, err="no query rule", rule=rule)


def decode(
    machine: MachineWorld,
    session: Session,
    text: str,
    *,
    write: bool,
) -> Result:
    raw = text.strip()
    if not raw:
        return Result(ok=False, err="empty")

    # MEM3
    if session.reset_if(raw):
        return Result(ok=True, spoken="好的", rule="MEM3")

    # D66 / D67：正文不入 tokenizer（在 greet / 句法之前）
    d66 = _try_d66(machine, session, raw, write=write)
    if d66 is not None:
        return d66
    d67 = _try_d67(machine, session, raw)
    if d67 is not None:
        return d67

    lex = pick_lex(raw)
    senses = tokenize(raw, lex)
    if not senses:
        return Result(ok=False, err="empty")

    names = _names(senses)

    # greet
    if "greet" in names:
        if write:
            eid = fx.new_event(machine)
            machine.tell(f"of(kind, {eid}, greet)")
            machine.tell(f"of(agent, {eid}, other)")
            machine.tell(f"of(object, {eid}, me)")
        return Result(ok=True, spoken=form_of("greet", lex) or "你好", rule="greet")

    # D35 rhetorical
    if "rhetorical" in names:
        return Result(ok=True, spoken=form_of("rhetorical") or _empty_q(), rule="D35")

    # Clause split D37–D46
    clause = _clause_split(raw)
    if clause is not None:
        return _decode_clauses(machine, session, clause, write=write)

    senses = _fill_ellipsis(senses, session, write=write)
    names = _names(senses)

    if _is_query(names):
        return _decode_query(machine, session, senses, write=write)

    neg = _neg(senses)
    # D59 别 → forbid(V,O), no event write
    if neg == "forbid":
        verbs = _verbs_in(senses)
        obj = ""
        kind = verbs[0][1] if verbs else ""
        if verbs:
            obj = (_ents(senses[verbs[0][0] + 1 :], session) or [""])[0]
        if write:
            if kind:
                fx.write_forbid(machine, kind, obj)
            session.push(obj)
            spoken = f"别{_surf(kind)}{_surf(obj)}" if kind else "好的"
            return Result(ok=True, spoken=spoken, rule="D59", focus=obj)
        # chat: acknowledge forbid without new write if already stored
        spoken = f"别{_surf(kind)}{_surf(obj)}" if kind else "好的"
        return Result(ok=True, spoken=spoken, rule="D59", focus=obj)
    # D57/D58: 不入库；闲聊路径对肯定命题做 yesno（加 not）；D58 再滤 at_time < now
    if neg in {"no", "past"}:
        core = [s for s in senses if s.name not in {"no", "pastneg"}]
        if write:
            got = _decode_statement(machine, session, core, write=False)
            particle = "没" if neg == "past" else "不"
            if got.spoken and got.spoken not in {_empty_info(), _empty_q()}:
                return Result(
                    ok=True,
                    spoken=particle + got.spoken,
                    rule="D57" if neg == "no" else "D58",
                )
            return Result(ok=True, spoken="好的", rule="D57" if neg == "no" else "D58")
        return _decode_neg_query(machine, session, core, neg=neg)

    return _decode_statement(machine, session, senses, write=write)


def _strip_wrap_quotes(text: str) -> str:
    text = text.strip()
    for a, b in (('"', '"'), ("'", "'"), ("“", "”"), ("「", "」")):
        if len(text) >= 2 and text.startswith(a) and text.endswith(b):
            return text[len(a) : -len(b)]
    return text


def _try_d66(
    machine: MachineWorld,
    session: Session,
    text: str,
    *,
    write: bool,
) -> Result | None:
    """D66: {实体}的内容是{任意文本} — 仅写库；正文原样，不解析。"""
    m = _D66.match(text)
    if m is None:
        return None
    # 排除 D67：「…的内容是什么」
    tail = m.group(2).strip()
    if re.fullmatch(r"什么\s*[？?]?", tail):
        return None
    if not write:
        return None
    entity = m.group(1).strip()
    content = _strip_wrap_quotes(tail)
    if not entity or not content:
        return Result(ok=False, err="D66 needs entity and content", rule="D66")
    fx.write_content(machine, entity, content)
    session.push(entity)
    return Result(
        ok=True,
        spoken=f"{entity}的内容是{content}",
        rule="D66",
        focus=entity,
    )


def _try_d67(machine: MachineWorld, session: Session, text: str) -> Result | None:
    """D67: {实体}的内容是什么 → find of(content,…); 空则 REN2。"""
    m = _D67.match(text)
    if m is None:
        return None
    entity = m.group(1).strip()
    if not entity:
        return Result(ok=False, err="D67 needs entity", rule="D67")
    if entity not in machine.domain:
        return Result(ok=True, spoken=_empty_q(), rule="REN2")
    # 直接扫 facts，避免正文含逗号时走字符串 find
    hits = [
        atom.args[2]
        for atom in machine.facts
        if atom.pred == "of" and len(atom.args) == 3 and atom.args[0] == "content" and atom.args[1] == entity
    ]
    if not hits:
        # inferred 也可能
        hits = [
            atom.args[2]
            for atom in machine.inferred
            if atom.pred == "of"
            and len(atom.args) == 3
            and atom.args[0] == "content"
            and atom.args[1] == entity
        ]
    if not hits:
        return Result(ok=True, spoken=_empty_q(), rule="REN2")
    session.push(entity)
    return Result(ok=True, spoken=hits[0], rule="D67", focus=entity)


def _is_query(names: list[str]) -> bool:
    marks = {
        "ask",
        "polar_isa",
        "polar_have",
        "polar_can",
        "or",
        "tag_right",
        "tag_isa",
        "who",
        "what",
        "where",
        "how",
        "why",
        "howmany",
    }
    return any(n in marks for n in names)


def _clause_split(text: str) -> tuple[str, list[str]] | None:
    # returns (link_rel, parts) or None
    pairs = [
        (("虽然", "但是"), "contrast"),
        (("虽然", "可是"), "contrast"),
        (("因为", "所以"), "cause"),
        (("如果", "就"), "condition"),
        (("不但", "而且"), "progression"),
        (("先", "然后"), "before"),
        (("先", "再"), "before"),
    ]
    for (a, b), rel in pairs:
        if a in text and b in text:
            left = text.split(a, 1)[1].split(b, 1)[0]
            right = text.split(b, 1)[1]
            return rel, [left.strip("，, "), right.strip("，, ")]
    if "的时候" in text:
        left, right = text.split("的时候", 1)
        return "during", [left.strip("，, "), right.strip("，, ")]
    if "因此" in text:
        left, right = text.split("因此", 1)
        return "cause", [left.strip("，, "), right.strip("，, ")]
    if "然后" in text and "先" not in text:
        left, right = text.split("然后", 1)
        return "before", [left.strip("，, "), right.strip("，, ")]
    if "但是" in text and "虽然" not in text:
        left, right = text.split("但是", 1)
        return "contrast", [left.strip("，, "), right.strip("，, ")]
    return None


def _decode_clauses(
    machine: MachineWorld,
    session: Session,
    clause: tuple[str, list[str]],
    *,
    write: bool,
) -> Result:
    rel, parts = clause
    if len(parts) != 2 or not all(parts):
        return Result(ok=False, err="bad clause")
    if not write:
        # chat: echo/query each; no write
        spoken = None
        for part in parts:
            got = decode(machine, session, part, write=False)
            spoken = got.spoken or spoken
        return Result(ok=True, spoken=spoken, rule=f"clause:{rel}")
    eids: list[str] = []
    spoken = None
    for part in parts:
        got = decode(machine, session, part, write=True)
        if not got.ok:
            return Result(ok=False, err=got.err or "clause fail", rule=got.rule)
        spoken = got.spoken or spoken
        # latest event
        eids.append(_latest_event(machine))
    if len(eids) == 2 and eids[0] and eids[1] and eids[0] != eids[1]:
        fx.link(machine, rel, eids[1], eids[0])
    return Result(ok=True, spoken=spoken, rule=f"D37-46:{rel}", focus=session.focus(0))


def _latest_event(machine: MachineWorld) -> str:
    ids = [int(n[2:]) for n in machine.domain if n.startswith("e.") and n[2:].isdigit()]
    return f"e.{max(ids)}" if ids else ""


def _decode_statement(
    machine: MachineWorld,
    session: Session,
    senses: list[Sense],
    *,
    write: bool,
) -> Result:
    names = _names(senses)
    ents = _ents(senses, session, machine)
    modal, modal_rule = _modal(senses)
    mood = _mood(senses)
    progress = "prog" in names

    # D3 是：表语为类→isa；个体→identity
    if "copula" in names and "loc" not in names:
        if len(ents) < 2:
            return Result(ok=False, err="copula needs two")
        subj, pred = ents[0], ents[1]
        if write:
            if _is_individual_name(machine, pred):
                fx.write_identity(machine, subj, pred)
                session.push(subj)
                return Result(ok=True, spoken=_say_isa(subj, pred), rule="D3.identity", focus=subj)
            fx.write_isa(machine, subj, pred)
            session.push(subj)
            return Result(ok=True, spoken=_say_isa(subj, pred), rule="D3", focus=subj)
        # 查：先 identity，再 isa
        ids = machine.find(f"?x of(identity, {subj}, x)")
        if ids.values:
            got = _prefer(session, ids.values)
            return Result(ok=True, spoken=_say_isa(subj, got), rule="D3.echo", focus=subj)
        kinds = machine.find(f"?x isa({subj}, x)")
        if isinstance(kinds, FindResult) and kinds.values:
            got = _prefer(session, kinds.values)
            return Result(ok=True, spoken=_say_isa(subj, got), rule="D3.echo", focus=subj)
        return Result(ok=True, spoken=_empty_info(), rule="REN2")

    # D6 在 / D4–D5 有
    if "loc" in names and not any(s.name in _VERBS for s in senses):
        if len(ents) < 2:
            return Result(ok=False, err="loc needs two")
        thing, place = ents[0], ents[1]
        if write:
            fx.write_located(machine, thing, place)
            session.push(thing)
            return Result(
                ok=True,
                spoken=f"{_surf(thing)}在{_surf(place)}",
                rule="D6",
                focus=thing,
            )
        places = machine.find(f"?x located({thing}, x)")
        if places.values:
            return Result(ok=True, spoken=f"{_surf(thing)}在{_surf(places.values[0])}", rule="D6.echo")
        return Result(ok=True, spoken=_empty_info(), rule="REN2")

    if "have" in names:
        if len(ents) < 2:
            return Result(ok=False, err="have needs two")
        left, right = ents[0], ents[1]
        if write:
            if _placeish(left, machine) and not _personish(left, machine):
                fx.write_located(machine, right, left)  # D4
                session.push(right)
                return Result(ok=True, spoken=f"{_surf(left)}有{_surf(right)}", rule="D4", focus=right)
            fx.write_has(machine, left, right)  # D5
            session.push(left)
            return Result(ok=True, spoken=f"{_surf(left)}有{_surf(right)}", rule="D5", focus=left)
        if _placeish(left, machine):
            hits = machine.find(f"?x located(x, {left})")
        else:
            hits = machine.find(f"?x has({left}, x)")
        if hits.values:
            return Result(ok=True, spoken=f"{_surf(left)}有{_surf(hits.values[0])}", rule="have.echo")
        return Result(ok=True, spoken=_empty_info(), rule="REN2")

    # D18/D19 cmp
    if "cmp" in names or "less" in names:
        if len(ents) < 2:
            return Result(ok=False, err="cmp needs two")
        left, right = ents[0], ents[1]
        prop = ents[2] if len(ents) > 2 else ""
        if write:
            fx.write_cmp(machine, left, right, prop)
            if "less" in names:
                # D19：极性挂在比较事实上（用 of(polarity, left, negative)）
                fx.ensure(machine, "negative")
                machine.tell(f"of(polarity, {left}, negative)")
            session.push(left)
            rule = "D19" if "less" in names else "D18"
            return Result(ok=True, spoken=f"{_surf(left)}比{_surf(right)}", rule=rule, focus=left)
        hits = machine.find(f"?x of(comparative, {left}, x)")
        if hits.values:
            return Result(ok=True, spoken=f"{_surf(left)}比{_surf(hits.values[0])}", rule="D18.echo")
        return Result(ok=True, spoken=_empty_info(), rule="REN2")

    # D55 X的
    if "de" in names and len(ents) == 1 and not _verbs_in(senses):
        owner = ents[0]
        hits = machine.find(f"?x has({owner}, x)")
        if not hits.values:
            hits = machine.find(f"?x of(possession, {owner}, x)")
        if hits.values:
            session.push(hits.values[0])
            return Result(ok=True, spoken=_surf(hits.values[0]), rule="D55", focus=hits.values[0])
        if write:
            return Result(ok=False, err="D55 no possession")
        return Result(ok=True, spoken=_empty_info(), rule="REN2")

    # D56 数+量
    nums = [s.name for s in senses if s.name.startswith("n") and s.name[1:].isdigit()]
    if nums and "clf" in names and not _verbs_in(senses) and not ents:
        kind = session.focus(0)
        if not kind:
            return Result(ok=False, err="D56 needs focus")
        hits = machine.find(f"?x isa(x, {kind})")
        n = len(hits.values)
        return Result(ok=True, spoken=f"{n}个{_surf(kind)}", rule="D56", focus=kind)

    # D44 和
    if "with_mark" in names and not _verbs_in(senses):
        if write:
            for e in ents:
                fx.ensure(machine, e)
                session.push(e)
        return Result(ok=True, spoken="和".join(_surf(e) for e in ents), rule="D44")

    # Verb clauses D1/D2/D7–D17/D20 + serial/causative
    verbs = _verbs_in(senses)
    if not verbs:
        return Result(ok=False, err="no pattern")

    # D15/D12 causative
    cause_i = next((i for i, v in verbs if v in _CAUSE_V), None)
    if cause_i is not None and len(verbs) >= 2:
        return _causative(
            machine,
            session,
            senses,
            write=write,
            modal=modal,
            mood=mood,
            modal_rule=modal_rule,
        )

    if len(verbs) >= 2:
        return _serial(
            machine,
            session,
            senses,
            write=write,
            modal=modal,
            mood=mood,
            modal_rule=modal_rule,
        )

    return _simple_verb(
        machine,
        session,
        senses,
        write=write,
        modal=modal,
        mood=mood,
        progress=progress,
        modal_rule=modal_rule,
    )


def _simple_verb(
    machine: MachineWorld,
    session: Session,
    senses: list[Sense],
    *,
    write: bool,
    modal: str,
    mood: str,
    progress: bool,
    modal_rule: str = "",
) -> Result:
    names = _names(senses)
    verbs = _verbs_in(senses)
    vi, kind = verbs[0]
    before = _strip_dates(_ents(senses[:vi], session, machine))
    after = _strip_dates(_ents(senses[vi + 1 :], session, machine))
    all_ents = _ents(senses, session, machine)
    degree, freq, scope, when = _extract_mods(senses, all_ents)

    # D8: 在/正在 before verb → progressive (not location)
    prog = progress or "prog" in names
    if not prog and "loc" in names:
        loc_i = names.index("loc")
        if loc_i < vi and not _ents(senses[loc_i + 1 : vi], session, machine):
            prog = True

    agent = ""
    obj = ""
    recipient = ""
    destination = ""
    target = ""
    rule = ""

    if "bei" in names:  # D10：施事在 被…动词 之间；省略则 unknown
        obj = before[0] if before else (session.focus(0) or "")
        bei_i = names.index("bei")
        mid = _ents(senses[bei_i + 1 : vi], session, machine)
        agent = mid[0] if mid else "unknown"
        if not obj and after:
            obj = after[-1]
        rule = "D10"
    elif "ba" in names:  # D9
        agent = before[0] if before else "other"
        ba_i = names.index("ba")
        mid = _ents(senses[ba_i + 1 : vi], session, machine)
        obj = mid[0] if mid else (after[0] if after else "")
        rule = "D9"
    elif "give_mark" in names and kind != "give":
        # D16 给 as preposition: 主语 给 宾语 V …
        agent = before[0] if before else "other"
        gi = names.index("give_mark")
        mid = _ents(senses[gi + 1 : vi], session, machine)
        obj = mid[0] if mid else (after[0] if after else "")
        rule = "D16"
    elif kind == "give":  # D11
        agent = before[0] if before else "other"
        if len(after) == 1 and len(after[0]) > 2:
            blob = after[0]
            split_at = 2
            for i in range(len(blob) - 1, 0, -1):
                if blob[:i] in machine.domain or blob[i:] in machine.domain:
                    split_at = i
                    break
            after = [blob[:split_at], blob[split_at:]]
        if len(after) >= 2:
            recipient, obj = after[0], after[1]
        elif after:
            obj = after[0]
        rule = "D11"
    elif "target_mark" in names and kind in {"say", "talk"}:  # D17 仅说/讲/介绍
        agent = before[0] if before else "other"
        ti = names.index("target_mark")
        mid = _ents(senses[ti + 1 : vi], session, machine)
        target = mid[0] if mid else ""
        obj = after[0] if after else ""
        rule = "D17"
    else:
        agent = before[0] if before else "other"
        obj = after[0] if after else ""

    # D20：V到处所；运动动词或处所词才挂 destination（避免「吃到苹果」误伤）
    if "dest_mark" in names and after:
        dest_cand = after[-1]
        motion = kind in {"go", "come"}
        if motion or _placeish(dest_cand, machine):
            destination = dest_cand
            if obj == destination and len(after) > 1:
                obj = after[0]
            elif obj == destination:
                obj = ""
            rule = "D20"

    # D49 object ellipsis → focus / last object
    if not obj and kind in _TRANS:
        obj = session.focus(0) or session.last_to

    # D1 vs D2
    if kind in _INTRANS:
        obj = ""
    elif kind in _TRANS and not obj and write:
        return Result(ok=False, err="D1 needs object")

    if not rule:
        if prog:
            rule = "D8"
        elif modal_rule:
            rule = modal_rule
        elif obj:
            rule = "D1"
        else:
            rule = "D2"

    if not write:
        hits = _events(machine, kind=kind, agent=agent, obj=obj)
        if hits:
            eid = hits[0]
            session.note(event=eid, src=agent, dst=obj or agent)
            return Result(
                ok=True,
                spoken=_speak_event(machine, eid),
                rule=f"{rule}.echo",
                focus=obj or agent,
            )
        return Result(ok=True, spoken=_empty_info(), rule="REN2")

    if not agent:
        agent = "other"
    eid = fx.write_event(
        machine,
        kind=kind,
        agent=agent,
        obj=obj,
        recipient=recipient,
        destination=destination,
        target=target,
        progress=prog,
        modal=modal,
        mood=mood,
    )
    fx.write_mods(machine, eid, when=when, degree=degree, freq=freq, scope=scope)
    session.push(obj or agent)
    session.note(event=eid, src=agent, dst=obj or agent, mark=kind)
    if destination:
        spoken = f"{_surf(agent)}{_surf(kind)}到{_surf(destination)}"
    elif target and obj:
        spoken = f"{_surf(agent)}对{_surf(target)}{_surf(kind)}{_surf(obj)}"
    elif obj:
        spoken = f"{_surf(agent)}{_surf(kind)}{_surf(obj)}"
    else:
        spoken = f"{_surf(agent)}{_surf(kind)}"
    if mood:
        spoken += mood
    return Result(
        ok=True,
        spoken=spoken,
        rule=rule,
        focus=obj or destination or agent,
    )


def _causative(
    machine: MachineWorld,
    session: Session,
    senses: list[Sense],
    *,
    write: bool,
    modal: str,
    mood: str,
    modal_rule: str = "",
) -> Result:
    del modal_rule
    verbs = _verbs_in(senses)
    (i1, v1), (i2, v2) = verbs[0], verbs[1]
    agent = (_ents(senses[:i1], session, machine) or ["other"])[0]
    pivot_ents = _ents(senses[i1 + 1 : i2], session, machine)
    pivot = pivot_ents[0] if pivot_ents else ""
    obj = (_ents(senses[i2 + 1 :], session, machine) or [""])[0]
    if not pivot:
        return Result(ok=False, err="causative needs pivot")
    # D12 帮；D15 让/叫/使/令/请/派
    rule = "D12" if v1 == "help" else "D15"
    if not write:
        hits = _events(machine, kind=v2, agent=pivot, obj=obj)
        if hits:
            return Result(ok=True, spoken=_speak_event(machine, hits[0]), rule=f"{rule}.echo", focus=pivot)
        return Result(ok=True, spoken=_empty_info(), rule="REN2")
    e1 = fx.write_event(machine, kind=v1, agent=agent, obj=pivot, modal=modal, mood=mood)
    e2 = fx.write_event(machine, kind=v2, agent=pivot, obj=obj)
    fx.link(machine, "cause", e2, e1)
    degree, freq, scope, when = _extract_mods(senses, _ents(senses, session, machine))
    fx.write_mods(machine, e2, when=when, degree=degree, freq=freq, scope=scope)
    session.push(pivot)
    return Result(
        ok=True,
        spoken=f"{_surf(agent)}{_surf(v1)}{_surf(pivot)}{_surf(v2)}{_surf(obj)}",
        rule=rule,
        focus=pivot,
    )


def _serial(
    machine: MachineWorld,
    session: Session,
    senses: list[Sense],
    *,
    write: bool,
    modal: str,
    mood: str,
    modal_rule: str = "",
) -> Result:
    del modal_rule
    verbs = _verbs_in(senses)
    (i1, v1), (i2, v2) = verbs[0], verbs[1]
    rel = "manner" if v1 == "go" or (len(verbs) > 2 and any(v == "go" for _, v in verbs)) else "purpose"
    agent = (_ents(senses[:i1], session, machine) or ["other"])[0]
    o1 = (_ents(senses[i1 + 1 : i2], session, machine) or [""])[-1]
    o2 = (_ents(senses[i2 + 1 :], session, machine) or [""])[-1]
    if not write:
        hits = _events(machine, kind=v2, agent=agent, obj=o2)
        if hits:
            return Result(ok=True, spoken=_speak_event(machine, hits[0]), rule="D13.echo")
        return Result(ok=True, spoken=_empty_info(), rule="REN2")
    e1 = fx.write_event(machine, kind=v1, agent=agent, obj=o1, modal=modal, mood=mood)
    e2 = fx.write_event(machine, kind=v2, agent=agent, obj=o2)
    fx.link(machine, rel, e2, e1)
    degree, freq, scope, when = _extract_mods(senses, _ents(senses, session, machine))
    fx.write_mods(machine, e2, when=when, degree=degree, freq=freq, scope=scope)
    session.push(o2 or o1 or agent)
    return Result(
        ok=True,
        spoken=f"{_surf(agent)}{_surf(v1)}{_surf(o1)}{_surf(v2)}{_surf(o2)}",
        rule="D13" if rel == "purpose" else "D14",
        focus=o2 or agent,
    )


def _decode_query(
    machine: MachineWorld,
    session: Session,
    senses: list[Sense],
    *,
    write: bool,
    neg: str = "",
) -> Result:
    del write
    names = _names(senses)
    ents = _ents(senses, session, machine)

    # D24 能不能
    if "polar_can" in names:
        verbs = _verbs_in(senses)
        if not verbs:
            return Result(ok=False, err="D24 needs verb")
        kind = verbs[0][1]
        vi = verbs[0][0]
        agent = (_ents(senses[:vi], session, machine) or [""])[0]
        obj = (_ents(senses[vi + 1 :], session, machine) or [""])[0]
        ok = bool(_events(machine, kind=kind, agent=agent, obj=obj))
        if neg:
            ok = not ok
        return Result(ok=True, spoken=_yes() if ok else _no(), rule="D24")

    # D21 / D33 / D34
    if "ask" in names or "tag_right" in names or "tag_isa" in names:
        qrule = "D33" if "tag_right" in names else ("D34" if "tag_isa" in names else "D21")
        core = [s for s in senses if s.name not in {"ask", "tag_right", "tag_isa"}]
        cn = _names(core)
        ce = _ents(core, session, machine)
        if "copula" in cn and len(ce) >= 2:
            ok = machine.yes(f"isa({ce[0]}, {ce[1]})") or machine.yes(
                f"of(identity, {ce[0]}, {ce[1]})"
            )
            if neg:
                ok = not ok
            return Result(ok=True, spoken=_yes() if ok else _no(), rule=qrule)
        if "have" in cn and len(ce) >= 2:
            a, b = ce[0], ce[1]
            ok = machine.yes(f"has({a}, {b})") or machine.yes(f"located({b}, {a})")
            if neg:
                ok = not ok
            return Result(ok=True, spoken=_yes() if ok else _no(), rule="D23")
        if "loc" in cn and len(ce) >= 2:
            ok = machine.yes(f"located({ce[0]}, {ce[1]})")
            if neg:
                ok = not ok
            return Result(ok=True, spoken=_yes() if ok else _no(), rule=qrule)
        verbs = _verbs_in(core)
        if verbs:
            kind = verbs[0][1]
            vi = verbs[0][0]
            agent = (_ents(core[:vi], session, machine) or [""])[0]
            obj = (_ents(core[vi + 1 :], session, machine) or [""])[0]
            ok = bool(_events(machine, kind=kind, agent=agent, obj=obj))
            if neg:
                ok = not ok
            return Result(ok=True, spoken=_yes() if ok else _no(), rule=qrule)
        return Result(ok=False, err="D21 no statement")

    if "polar_isa" in names and len(ents) >= 2:
        ok = machine.yes(f"isa({ents[0]}, {ents[1]})")
        return Result(ok=True, spoken=_yes() if ok else _no(), rule="D22")

    if "polar_have" in names and len(ents) >= 2:
        a, b = ents[0], ents[1]
        ok = machine.yes(f"has({a}, {b})") or machine.yes(f"located({b}, {a})")
        return Result(ok=True, spoken=_yes() if ok else _no(), rule="D23")

    # D25 / D26 / D28
    if "who" in names:
        verbs = _verbs_in(senses)
        if not verbs:
            subj = ents[0] if ents else "me"
            hits = machine.find(f"?x of(identity, {subj}, x)")
            if hits.values:
                return Result(ok=True, spoken=_say_isa(subj, hits.values[0]), rule="D28")
            kinds = machine.find(f"?x isa({subj}, x)")
            if kinds.values:
                return Result(
                    ok=True,
                    spoken=_say_isa(subj, _prefer(session, kinds.values)),
                    rule="D27",
                )
            return Result(ok=True, spoken=_empty_q(), rule="REN2")
        kind = verbs[0][1]
        vi = verbs[0][0]
        after = _ents(senses[vi + 1 :], session)
        who_first = senses[0].name == "who"
        if who_first:
            obj = after[0] if after else ""
            hits = _find_agents(machine, kind, obj)
            if hits:
                return Result(ok=True, spoken=_surf(hits[0]), rule="D25")
            return Result(ok=True, spoken=_empty_q(), rule="REN2")
        agent = (_ents(senses[:vi], session) or [""])[0]
        hits = _find_objects(machine, kind, agent)
        if hits:
            return Result(ok=True, spoken=_surf(hits[0]), rule="D26")
        return Result(ok=True, spoken=_empty_q(), rule="REN2")

    # D27
    if "what" in names and ents:
        hits = machine.find(f"?x isa({ents[0]}, x)")
        if hits.values:
            return Result(
                ok=True,
                spoken=_say_isa(ents[0], _prefer(session, hits.values)),
                rule="D27",
            )
        return Result(ok=True, spoken=_empty_q(), rule="REN2")

    # D29
    if "where" in names and ents:
        hits = machine.find(f"?x located({ents[0]}, x)")
        if hits.values:
            return Result(
                ok=True,
                spoken=f"{_surf(ents[0])}在{_surf(hits.values[0])}",
                rule="D29",
            )
        return Result(ok=True, spoken=_empty_q(), rule="REN2")

    # D30 怎么
    if "how" in names:
        verbs = _verbs_in(senses)
        if not verbs:
            return Result(ok=False, err="D30 needs verb")
        kind = verbs[0][1]
        vi = verbs[0][0]
        agent = (_ents(senses[:vi], session) or [""])[0]
        obj = (_ents(senses[vi + 1 :], session) or [""])[0]
        for eid in _events(machine, kind=kind, agent=agent, obj=obj):
            manners = machine.find(f"?x of(manner, {eid}, x)")
            if manners.values:
                return Result(
                    ok=True,
                    spoken=_speak_event(machine, manners.values[0]),
                    rule="D30",
                )
            # manner may link the other way: of(manner, e2, e1) where e2 is focus
            manners = machine.find(f"?x of(manner, x, {eid})")
            if manners.values:
                return Result(
                    ok=True,
                    spoken=_speak_event(machine, manners.values[0]),
                    rule="D30",
                )
        return Result(ok=True, spoken=_empty_q(), rule="REN2")

    # D31 为什么
    if "why" in names:
        core = [s for s in senses if s.name != "why"]
        verbs = _verbs_in(core)
        if not verbs:
            return Result(ok=False, err="D31 needs statement")
        kind = verbs[0][1]
        vi = verbs[0][0]
        agent = (_ents(core[:vi], session) or [""])[0]
        obj = (_ents(core[vi + 1 :], session) or [""])[0]
        for eid in _events(machine, kind=kind, agent=agent, obj=obj):
            causes = machine.find(f"?x of(cause, {eid}, x)")
            if causes.values:
                return Result(
                    ok=True,
                    spoken=_speak_event(machine, causes.values[0]),
                    rule="D31",
                )
        return Result(ok=True, spoken=_empty_q(), rule="REN2")

    # D32 还是
    if "or" in names and "copula" in names and len(ents) >= 3:
        subj, a, b = ents[0], ents[1], ents[2]
        if machine.yes(f"isa({subj}, {a})"):
            return Result(ok=True, spoken=_say_isa(subj, a), rule="D32")
        if machine.yes(f"isa({subj}, {b})"):
            return Result(ok=True, spoken=_say_isa(subj, b), rule="D32")
        return Result(ok=True, spoken=_empty_q(), rule="REN2")

    # D36 多少 / 几个：count(find ?x ∧ isa(?x, 名词))
    if "howmany" in names:
        noun = ""
        subj = ""
        # 模式：[{主语}] 多少 [{量词}] {名词}
        how_i = next(i for i, s in enumerate(senses) if s.name == "howmany")
        before = _ents(senses[:how_i], session, machine)
        after = _ents(senses[how_i + 1 :], session, machine)
        if before:
            subj = before[0]
        for sense in reversed(senses[how_i + 1 :]):
            if sense.name == "clf":
                continue
            got = _entity(sense, session)
            if got and not got.startswith("n"):
                noun = got
                break
        if not noun and after:
            noun = after[-1]
        if not noun:
            noun = session.focus(0)
        if not noun:
            return Result(ok=False, err="D36 needs noun")
        # 聚合：count(find isa(?x, 名词))；有主语时不改变计数语义（表：按名词类）
        del subj
        hits = machine.find(f"?x isa(x, {noun})")
        n = len(hits.values)
        from cni.render.forms import form as form_tm

        tpl = form_of("count") or form_tm("count") or "有{0}个"
        spoken = tpl.replace("{0}", str(n)) + _surf(noun)
        return Result(ok=True, spoken=spoken, rule="D36", focus=noun)

    return Result(ok=False, err="no query rule")


def _find_agents(machine: MachineWorld, kind: str, obj: str) -> list[str]:
    out: list[str] = []
    for name in list(machine.domain):
        if not name.startswith("e."):
            continue
        if not machine.yes(f"of(kind, {name}, {kind})"):
            continue
        if obj and not machine.yes(f"of(object, {name}, {obj})"):
            continue
        agents = machine.find(f"?x of(agent, {name}, x)")
        out.extend(agents.values)
    return list(dict.fromkeys(out))


def _find_objects(machine: MachineWorld, kind: str, agent: str) -> list[str]:
    out: list[str] = []
    for name in list(machine.domain):
        if not name.startswith("e."):
            continue
        if not machine.yes(f"of(kind, {name}, {kind})"):
            continue
        if agent and not machine.yes(f"of(agent, {name}, {agent})"):
            continue
        objs = machine.find(f"?x of(object, {name}, x)")
        out.extend(objs.values)
    return list(dict.fromkeys(out))
