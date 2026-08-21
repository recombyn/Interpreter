"""D1–D69: one ordered decoder. write=True → hear; write=False → turn query/echo."""

from __future__ import annotations

from dataclasses import dataclass
import re

from para.api import KnowledgeHit
from para.decode import effects as fx
from para.decode.lex import Sense, form_of, pick_lex, tokenize
from para.decode.route_table import classify_buckets
from para.kernel import FindResult, MachineWorld
from para.render.forms import form as form_tm
from para.render.forms import polar_spoken
from para.session import Session
from para.system_tm import load_system
from para.text.d66 import D66_CONTENT_RE, clip_d66_content

_D67 = re.compile(r"^(.+?)\s*的内容\s*是什么\s*[？?]?\s*$")
_D67_CHAR = re.compile(
    r"^(.+?)(?:的)?第(?P<n>\d+|[一二三四五六七八九十百零〇两]+)"
    r"个字(?:是什么|是啥|是哪|为)?\s*[？?]?\s*$"
)
_D67_LEN = re.compile(r"^(.+?)(?:的)?(?:有多少字|多少字|字数(?:是多少)?)\s*[？?]?\s*$")

# Multi-fire: D67.char mid-utterance; D67/D67.len use needle scan
_D67_CHAR_FIND = re.compile(
    r"(?P<entity>.{1,40}?)(?:的)?第(?P<n>\d+|[一二三四五六七八九十百零〇两]+)"
    r"个字(?:是什么|是啥|是哪|为)?"
)

_SPAN_BREAK = set("？?。；;，,、\n\r\t ")

_VERBS = {
    "invent",
    "buy",
    "hungry",
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
_INTRANS = {"come", "go", "live", "wait", "talk", "think", "hungry"}
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
_ADJ = {
    "adj_tall": "高",
    "adj_short": "矮",
    "adj_big": "大",
    "adj_small": "小",
    "adj_good": "好",
    "adj_bad": "坏",
    "adj_strong": "强",
    "adj_weak": "弱",
    "adj_fast": "快",
    "adj_slow": "慢",
    "adj_long": "长",
    "adj_brief": "短",
    "adj_new": "新",
    "adj_old": "旧",
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
    confidence: float = 1.0
    warn: str = ""
    evidence: tuple[KnowledgeHit, ...] = ()


def _names(senses: list[Sense]) -> list[str]:
    return [s.name for s in senses]


def _entity(sense: Sense, session: Session, *, eventish: bool = False) -> str | None:
    # D50–D54
    if sense.name == "self":
        return "me"
    if sense.name == "addr":
        return "other"
    if sense.name in _ADJ:
        return _ADJ[sense.name]
    if sense.name == "ana":
        # D52 / MEM5: patient → focus → coref chain tip; else intro
        top = session.resolve_ana()
        if top:
            return top
        return ""  # caller will intro
    if sense.name == "this":
        return session.resolve_deixis(far=False, eventish=eventish)
    if sense.name == "that":
        # D54: far deixis; event classifiers → event stack
        return session.resolve_deixis(far=True, eventish=eventish)
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
        "able",
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
        *_ADJ,
    }:
        if sense.name in _VERBS:
            return None
        return sense.name
    return None


def _ents(senses: list[Sense], session: Session, machine: MachineWorld | None = None) -> list[str]:
    out: list[str] = []
    for i, sense in enumerate(senses):
        if sense.name == "ana" and not session.focus(0):
            # D52: no focus → intro
            name = sense.surface or "他"
            if machine is not None:
                fx.ensure(machine, name)
            out.append(name)
            continue
        eventish = False
        if sense.name in {"this", "that"} and i + 1 < len(senses):
            nxt = senses[i + 1]
            tip = nxt.surface or nxt.name
            deixis = load_system().event_deixis
            if tip in deixis or nxt.name in deixis:
                eventish = True
        name = _entity(sense, session, eventish=eventish)
        if name:
            out.append(name)
    return out


def _verbs_in(senses: list[Sense]) -> list[tuple[int, str]]:
    base = [(i, s.name) for i, s in enumerate(senses) if s.name in _VERBS]
    give_marks = [i for i, s in enumerate(senses) if s.name == "give_mark"]
    if give_marks and not base:
        # D11 give_mark as main verb
        return [(give_marks[0], "give")]
    # D16 give as preposition: ignore give_mark as verb
    return base


def _mood(senses: list[Sense]) -> str:
    for s in senses:
        if s.name in _MOOD_WORD:
            return _MOOD_WORD[s.name]
    return ""


def _extract_mods(senses: list[Sense], ents: list[str]) -> tuple[str, str, str, str]:
    """Degree/freq/scope/time (incl. absolute dates injected by G)."""
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
    """Kind name previously used as isa(_, name)."""
    return any(a.pred == "isa" and a.args[1] == name for a in machine.facts)


def _is_individual_name(machine: MachineWorld, name: str) -> bool:
    """Predicate is an individual: in domain, not a kind, and person or has instance isa."""
    if name not in machine.domain:
        return False
    if _is_kind_name(machine, name):
        return False
    if name in _PERSON or machine.yes(f"isa({name}, person)"):
        return True
    return any(a.pred == "isa" and a.args[0] == name for a in machine.facts)


def _prefer(session: Session, values: tuple[str, ...] | list[str]) -> str:
    """QP1: take first of find sorted hits (explicit>inferred>session pin>event)."""
    del session
    if not values:
        return ""
    return values[0]


def _qfind(machine: MachineWorld, session: Session, query: str):
    return machine.find(query, pins=session.focus_stack)


def _fill_ellipsis(senses: list[Sense], session: Session, *, write: bool) -> list[Sense]:
    # D47: sentence-initial verb without subject → supply other; if context is me supply me; D7 write → me
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
    """Return (modal constant, rule id). D60 can / D61 able / D62 must / D63 force / D64 may."""
    for s in senses:
        if s.name == "can":
            return "能力", "D60"
        if s.name == "able":
            return "能力", "D61"
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


def _surf(name: str) -> str:
    # form.tm first (user/system REN); lex outs for verb/adj surfaces
    got = form_tm(name) or form_of(name)
    if got:
        return got
    if name == "me":
        return "我"
    if name == "other":
        return "你"
    if name == "unknown":
        return "有人"
    return name


def _ren1(pred: str, *args: str) -> str:
    """REN1: fact exists but form.tm has no matching template."""
    return f"[原始逻辑] {pred}({','.join(args)})"


def _apply_form(key: str, *args: str, pred: str | None = None) -> str:
    """Render with form.tm template; missing → REN1."""
    tpl = form_tm(key) or form_of(key)
    if not tpl:
        return _ren1(pred or key, *args)
    out = tpl
    for i, arg in enumerate(args):
        out = out.replace(f"{{{i}}}", _surf(arg))
    return out


def _say_isa(subj: str, kind: str) -> str:
    return _apply_form("say.isa", subj, kind, pred="isa")


def _say_located(thing: str, place: str) -> str:
    return _apply_form("say.located", thing, place, pred="located")


def _say_has(owner: str, thing: str) -> str:
    return _apply_form("say.has", owner, thing, pred="has")


def _yes() -> str:
    return form_tm("yes") or ""


def _no() -> str:
    return form_tm("no") or ""


def _empty_q() -> str:
    """REN2 question: the rule ran and find returned empty."""
    return form_tm("unknown_q") or ""


def _empty_info() -> str:
    """REN2 statement: the rule ran and find returned empty."""
    return form_tm("unknown_info") or ""


def _role(machine: MachineWorld, src: str, rel: str) -> str:
    hits = machine.find(f"?x of({rel}, {src}, x)")
    return hits.values[0] if hits.values else ""


def _speak_event(machine: MachineWorld, eid: str) -> str:
    kind = _role(machine, eid, "kind")
    agent = _role(machine, eid, "agent")
    obj = _role(machine, eid, "object")
    if not kind:
        return _ren1("event", eid)
    kind_surf = form_of(kind) or form_tm(kind)
    if not kind_surf:
        # REN1: have event, no kind surface template
        parts = ["kind", eid, kind]
        if agent:
            parts = [eid, kind, agent] + ([obj] if obj else [])
            return _ren1("of", *parts)
        return _ren1("of", "kind", eid, kind)
    # say.event {0}{1}{2} = agent + kind_surf + object
    tpl = form_tm("say.event") or form_of("say.event")
    if tpl:
        a = _surf(agent) if agent else ""
        o = _surf(obj) if obj else ""
        return tpl.replace("{0}", a).replace("{1}", kind_surf).replace("{2}", o)
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
            # D58: count if when < today; also count events without when (else past-neg misfires)
            whens = machine.find(f"?x of(when, {name}, x)")
            if whens.values and not any(t < today for t in whens.values):
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
    """D57/D58 chat: existence-query the de-negated proposition and flip; D58 only counts at_time < now."""
    names = _names(core)
    ents = _ents(core, session, machine)
    past = neg == "past"
    rule = "D58" if past else "D57"

    def _flip(ok: bool) -> Result:
        # Negated proposition: positive fact exists → answer no; absent → yes
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


def _clause_before_needle(
    text: str, needle_start: int, needle: str
) -> tuple[int, int, str] | None:
    """Entity/clause immediately before needle, bounded by punctuation."""
    i = needle_start
    j = i
    while j > 0 and text[j - 1] not in _SPAN_BREAK and (i - j) < 40:
        j -= 1
    while j < i and text[j] in _SPAN_BREAK:
        j += 1
    if j >= i:
        return None
    end = i + len(needle)
    frag = text[j:end].strip()
    frag = re.sub(r"[？?\s]+$", "", frag)
    if not frag:
        return None
    return j, end, frag


def _collect_content_spans(text: str) -> list[tuple[int, int, str, str]]:
    """(start, end, kind, fragment) for D67 / D67.char / D67.len clauses."""
    raw = text or ""
    cands: list[tuple[int, int, str, str]] = []

    needle = "的内容是什么"
    start = 0
    while True:
        i = raw.find(needle, start)
        if i < 0:
            break
        got = _clause_before_needle(raw, i, needle)
        if got is not None:
            s, e, frag = got
            if _D67.match(frag):
                cands.append((s, e, "D67", frag))
        start = i + 1

    for m in _D67_CHAR_FIND.finditer(raw):
        full_ent = m.group("entity")
        ent = full_ent
        for br in ("？", "?", "。", "；", ";", "，", ",", "、", " ", "\t"):
            if br in ent:
                ent = ent.split(br)[-1]
        ent = ent.strip()
        if not ent:
            continue
        off = full_ent.rfind(ent)
        if off < 0:
            continue
        ent_pos = m.start("entity") + off
        frag = re.sub(r"[？?\s]+$", "", raw[ent_pos : m.end()].strip())
        if _D67_CHAR.match(frag):
            cands.append((ent_pos, m.end(), "D67.char", frag))

    for needle in ("有多少字", "多少字", "字数是多少"):
        start = 0
        while True:
            i = raw.find(needle, start)
            if i < 0:
                break
            got = _clause_before_needle(raw, i, needle)
            if got is not None:
                s, e, frag = got
                if _D67_LEN.match(frag):
                    cands.append((s, e, "D67.len", frag))
            start = i + 1

    return cands


def _dedupe_spans(
    spans: list[tuple[int, int, str, str]],
) -> list[tuple[int, int, str, str]]:
    spans = sorted(spans, key=lambda x: (x[0], -(x[1] - x[0])))
    out: list[tuple[int, int, str, str]] = []
    last_end = -1
    for s, e, kind, frag in spans:
        if s < last_end:
            continue
        out.append((s, e, kind, frag))
        last_end = e
    return out


def _try_multi_query(
    machine: MachineWorld, session: Session, text: str, *, write: bool
) -> Result | None:
    """Multiple D67/D69 fires, or peel one mid-sentence query from a long prefix.

    Full-utterance single span → None so early-exit / pending D69 resume stays primary.
    """
    if write:
        return None
    from para.judge import find_judge_spans

    spans: list[tuple[int, int, str, str]] = []
    spans.extend(_collect_content_spans(text))
    for s, e, frag in find_judge_spans(text):
        spans.append((s, e, "D69", frag))
    spans = _dedupe_spans(spans)
    if not spans:
        return None

    body = text.strip().rstrip("？?")
    if len(spans) == 1:
        s, _e, _kind, frag = spans[0]
        if s == 0 and frag.strip().rstrip("？?") == body:
            return None

    parts: list[str] = []
    rules: list[str] = []
    evidence: list[KnowledgeHit] = []
    focus = ""
    for _s, _e, kind, frag in spans:
        if kind == "D69":
            got = _try_d69(machine, session, frag, write=False)
        elif kind == "D67":
            got = _try_d67(machine, session, frag)
        elif kind == "D67.len":
            got = _try_d67_char(machine, session, frag)
        else:
            got = _try_d67_char(machine, session, frag)
        if got is None:
            continue
        if got.spoken:
            parts.append(got.spoken.strip())
        rules.append(got.rule or kind)
        if got.focus:
            focus = got.focus
        if got.evidence:
            evidence.extend(got.evidence)

    if not parts:
        return None
    if len(parts) == 1:
        return Result(
            ok=True,
            spoken=parts[0],
            rule=rules[0] if rules else "MULTI",
            focus=focus,
            evidence=tuple(evidence),
        )
    uniq_rules: list[str] = []
    for r in rules:
        if r not in uniq_rules:
            uniq_rules.append(r)
    return Result(
        ok=True,
        spoken="；".join(parts),
        rule="+".join(uniq_rules) if len(uniq_rules) <= 3 else "MULTI",
        focus=focus,
        warn=f"fires:{len(parts)}",
        evidence=tuple(evidence),
    )


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

    # Multi-fire / mid-sentence query spans (before single full-string early exit)
    multi = _try_multi_query(machine, session, raw, write=write)
    if multi is not None:
        return multi

    # D66 / D67 / D69: content + judgment early exit (basic group; must run before tokenize)
    d66 = _try_d66(machine, session, raw, write=write)
    if d66 is not None:
        return d66
    d67 = _try_d67(machine, session, raw)
    if d67 is not None:
        return d67
    d67c = _try_d67_char(machine, session, raw)
    if d67c is not None:
        return d67c
    d69 = _try_d69(machine, session, raw, write=write)
    if d69 is not None:
        return d69

    lex = pick_lex(raw)
    senses = tokenize(raw, lex)
    if not senses:
        return Result(ok=False, err="empty")

    names = _names(senses)

    # greet (I2 usually in preprocess; fallback here)
    if "greet" in names:
        if write:
            eid = fx.new_event(machine)
            machine.tell(f"of(kind, {eid}, greet)")
            machine.tell(f"of(agent, {eid}, other)")
            machine.tell(f"of(object, {eid}, me)")
        return Result(ok=True, spoken=form_tm("greet") or "", rule="greet")

    senses = _fill_ellipsis(senses, session, write=write)
    names = _names(senses)
    buckets = classify_buckets(raw, names)

    # Write path: first hit wins (legacy). Chat path may scan for AMB1.
    from para.user_config import ambig_mode

    mode = ambig_mode() if not write else "first"
    probe = mode in {"clarify", "warn"} and (
        len(raw) >= 10 or "，" in raw or "," in raw or len(buckets) > 2
    )

    if not probe:
        for bucket in buckets:
            try:
                got = _try_bucket(
                    machine, session, raw, senses, names, write=write, bucket=bucket
                )
            except ValueError:
                got = None
            if got is not None:
                return got
        return Result(ok=False, err="no pattern")

    # Multi-bucket probe (read-only): collect distinct rules
    hits: list[Result] = []
    seen_rules: set[str] = set()
    for bucket in buckets:
        try:
            got = _try_bucket(
                machine, session, raw, senses, names, write=False, bucket=bucket
            )
        except ValueError:
            got = None
        if got is None or not got.ok:
            continue
        key = (got.rule or "").split(".")[0]
        if key in seen_rules:
            continue
        seen_rules.add(key)
        hits.append(got)

    if not hits:
        return Result(ok=False, err="no pattern")
    if len(hits) == 1:
        return hits[0]

    rules = [h.rule or "?" for h in hits[:4]]
    warn = f"ambiguous:{'/'.join(rules)}"
    if mode == "clarify":
        spoken = form_tm("ambig") or ""
        return Result(
            ok=True,
            spoken=spoken,
            rule="AMB1",
            confidence=0.4,
            warn=warn,
            focus=hits[0].focus,
        )
    # warn: return first answer but lower confidence
    first = hits[0]
    return Result(
        ok=first.ok,
        spoken=first.spoken,
        rule=first.rule,
        focus=first.focus,
        err=first.err,
        confidence=0.55,
        warn=warn,
    )


def _try_bucket(
    machine: MachineWorld,
    session: Session,
    raw: str,
    senses: list[Sense],
    names: list[str],
    *,
    write: bool,
    bucket: str,
) -> Result | None:
    """Opt 3: try by route.tm group; on miss return None to fall through to next group."""
    if bucket == "query":
        if "rhetorical" in names:
            return Result(ok=True, spoken=form_tm("rhetorical") or _empty_q(), rule="D35")
        if _is_query(names):
            return _decode_query(machine, session, senses, write=write)
        return None

    if bucket == "compound":
        clause = _clause_split(raw)
        if clause is not None:
            return _decode_clauses(machine, session, clause, write=write)
        return None

    if bucket == "special":
        special_marks = {
            "ba",
            "bei",
            "give_mark",
            "let",
            "help",
            "call",
            "invite",
            "cmp",
            "less",
            "target_mark",
            "dest_mark",
        }
        if not (special_marks & set(names)):
            return None
        got = _decode_statement(machine, session, senses, write=write, mode="special")
        if got is None or (not got.ok and (got.err or "") in {"no pattern", "no query rule"}):
            return None
        return got

    if bucket == "deixis":
        # Ellipsis/deixis already in _fill_ellipsis; defer when this group has no dedicated handler
        return None

    if bucket == "basic":
        neg = _neg(senses)
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
            spoken = f"别{_surf(kind)}{_surf(obj)}" if kind else "好的"
            return Result(ok=True, spoken=spoken, rule="D59", focus=obj)
        if neg in {"no", "past"}:
            # Fact vs query negation: teach/write never stores a negated event triple;
            # chat uses D57/D58 query flip (see _decode_neg_query). Spoken "不/没"+echo
            # on write=True is acknowledgment only (RO teach of bare 不… is particle+echo).
            core = [s for s in senses if s.name not in {"no", "pastneg"}]
            if write:
                got = _decode_statement(machine, session, core, write=False, mode="basic")
                particle = "没" if neg == "past" else "不"
                if got and got.spoken and got.spoken not in {_empty_info(), _empty_q()}:
                    return Result(
                        ok=True,
                        spoken=particle + got.spoken,
                        rule="D57" if neg == "no" else "D58",
                    )
                return Result(ok=True, spoken="好的", rule="D57" if neg == "no" else "D58")
            return _decode_neg_query(machine, session, core, neg=neg)
        return _decode_statement(machine, session, senses, write=write, mode="basic")

    return None


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
    """D66: entity content-clause — write only; keep body verbatim, clip following questions."""
    m = D66_CONTENT_RE.match(text)
    if m is None:
        return None
    # Exclude D67 content-what questions
    tail = m.group(2).strip()
    if re.fullmatch(r"什么\s*[？?]?", tail):
        return None
    if not write:
        return None
    entity = m.group(1).strip()
    content = clip_d66_content(_strip_wrap_quotes(tail))
    if not entity or not content:
        return Result(ok=False, err="D66 needs entity and content", rule="D66")
    fx.write_content(machine, entity, content)
    session.note_content_hit(entity, content, rule="D66")
    return Result(
        ok=True,
        spoken=f"{entity}的内容是{content}",
        rule="D66",
        focus=entity,
    )


def _try_d67(machine: MachineWorld, session: Session, text: str) -> Result | None:
    """D67: ask entity content → find of(content,…); empty → REN2."""
    m = _D67.match(text)
    if m is None:
        return None
    entity = m.group(1).strip()
    if not entity:
        return Result(ok=False, err="D67 needs entity", rule="D67")
    # Session pins disambiguate bare 第N行 → {doc}第N行 when known
    entity = session.qualify_entity(entity, machine.domain)
    if entity not in machine.domain:
        return Result(ok=True, spoken=_empty_q(), rule="REN2")
    # QP1 via content side-index (O(1) by entity; not a full-facts scan)
    hits = machine.contents_of(entity)
    if not hits:
        return Result(ok=True, spoken=_empty_q(), rule="REN2")
    got = _prefer(session, hits)
    session.note_content_hit(entity, got, rule="D67")
    evidence = (
        KnowledgeHit(kind="content", ref=entity, text=got, topic=entity),
    )
    return Result(ok=True, spoken=got, rule="D67", focus=entity, evidence=evidence)


def _content_plain_chars(text: str) -> str:
    """Strip markdown / 第N条 heading; keep non-space characters for 第N个字."""
    t = (text or "").replace("**", "").replace("　", " ")
    t = re.sub(r"^第[一二三四五六七八九十百零〇\d]+条\s*", "", t.strip())
    return re.sub(r"\s+", "", t)


def _try_d67_char(
    machine: MachineWorld, session: Session, text: str
) -> Result | None:
    """D67.char / D67.len: nth character or length of entity content."""
    from para.judge import parse_cn_int

    m = _D67_CHAR.match(text.strip())
    mlen = None if m else _D67_LEN.match(text.strip())
    if m is None and mlen is None:
        return None
    entity = (m or mlen).group(1).strip()  # type: ignore[union-attr]
    entity = session.qualify_entity(entity, machine.domain)
    if entity not in machine.domain:
        return Result(ok=True, spoken=_empty_q(), rule="REN2")
    hits = machine.contents_of(entity)
    if not hits:
        return Result(ok=True, spoken=_empty_q(), rule="REN2")
    body = _content_plain_chars(_prefer(session, hits))
    session.note_content_hit(entity, hits[0] if hits else "", rule="D67.char")
    if mlen is not None:
        return Result(
            ok=True,
            spoken=str(len(body)),
            rule="D67.len",
            focus=entity,
        )
    assert m is not None
    idx = parse_cn_int(m.group("n"))
    if idx is None or idx < 1:
        return Result(ok=True, spoken=_empty_q(), rule="REN2", focus=entity)
    if idx > len(body):
        return Result(
            ok=True,
            spoken=_empty_q(),
            rule="REN2",
            focus=entity,
            warn=f"len={len(body)}",
        )
    ch = body[idx - 1]
    return Result(ok=True, spoken=ch, rule="D67.char", focus=entity)


def _source_body(machine: MachineWorld, src: str) -> str:
    """Resolve cited line/entity to stored content text (D66/D67 memory)."""
    if not src:
        return ""
    bodies = machine.contents_of(src)
    if bodies:
        return bodies[0]
    from para.judge import of_value

    return of_value(machine, "content", src) or ""


def _cite_evidence(
    machine: MachineWorld, src: str, *, topic: str = "", kind: str = "cite"
) -> tuple[KnowledgeHit, ...]:
    """Build audit evidence from a source ref (content body when known)."""
    if not src:
        return ()
    body = _source_body(machine, src)
    if not body:
        return (KnowledgeHit(kind=kind, ref=src, text="", topic=topic),)
    return (KnowledgeHit(kind=kind, ref=src, text=body, topic=topic),)


def _spoken_with_ref(spoken: str, src: str) -> str:
    """Optional short ref label in spoken; full body stays in evidence."""
    from para.user_config import judge_cite

    if not src or not judge_cite():
        return spoken
    return f"{spoken}（见{src}）"


def _try_d69(
    machine: MachineWorld,
    session: Session,
    text: str,
    *,
    write: bool,
) -> Result | None:
    """D69: threshold / enum / tier / ask-slot judgment (rules.tm + limits)."""
    if write:
        return None
    from para.judge import judge

    pending_q = session.pending_judge_text
    hit = judge(
        machine,
        text,
        pending_topic=session.pending_judge_topic,
        pending_text=pending_q,
    )
    if hit is None:
        return None
    session.push(hit.topic)
    src = hit.source or ""
    evidence = list(_cite_evidence(machine, src, topic=hit.topic, kind="cite"))
    if hit.conditions:
        evidence.append(
            KnowledgeHit(
                kind="condition",
                ref=src or hit.topic,
                text=hit.conditions,
                topic=hit.topic,
            )
        )
    evidence_t = tuple(evidence)
    if hit.kind == "ask":
        session.pending_judge_topic = hit.topic
        session.pending_judge_text = text.strip()
        spoken = hit.ask or form_tm("judge_ask") or ""
        return Result(
            ok=True,
            spoken=spoken,
            rule="D69.ask",
            focus=hit.topic,
            evidence=evidence_t,
            warn=f"source:{src}" if src else "",
        )
    # polarity from original judge question (resume may be bare「六个月」)
    ask_for_tone = pending_q or text
    session.pending_judge_topic = ""
    session.pending_judge_text = ""
    if hit.kind not in {"answer", "explain"}:
        return Result(
            ok=True,
            spoken=_empty_q(),
            rule="REN2",
            focus=hit.topic,
            evidence=evidence_t,
        )

    spoken = _d69_spoken(hit, ask_for_tone, text)
    spoken = _spoken_with_ref(spoken, src)
    return Result(
        ok=True,
        spoken=spoken,
        rule="D69",
        focus=hit.topic,
        evidence=evidence_t,
        warn=f"source:{src}" if src else "",
    )


def _d69_dur_surface(question: str, topic: str, trigger: str) -> str:
    from para.judge import _LEGAL_JUNK, strip_cond_cue

    raw, _ = strip_cond_cue(question or "")
    if trigger and raw.endswith(trigger):
        raw = raw[: -len(trigger)]
    if topic and raw.startswith(topic):
        mid = raw[len(topic) :].strip("，, ")
    else:
        mid = raw.strip("，, ")
    # Drop trailing legality leftovers if cue/trigger mismatch
    for junk in _LEGAL_JUNK:
        if mid.endswith(junk) and mid != junk:
            mid = mid[: -len(junk)].strip("，, ")
            break
    return mid


def _d69_spoken(hit, ask_for_tone: str, text: str) -> str:
    """Compose D69 spoken: conditional/explain narrative, else polar."""
    from para.judge import _NEG_TRIG, parse_duration

    if getattr(hit, "detail", "") == "all_topics":
        spoken = "都合法" if hit.ok else "不都合法"
        cond = (hit.conditions or "").strip()
        if hit.ok and cond:
            spoken = f"{spoken}。相关规定：{cond}"
        return spoken

    cond = (hit.conditions or "").strip()
    want_cond = (
        hit.kind == "explain"
        or hit.detail == "conditional"
        or hit.detail in {"over_abs", "no_tier"}
        or "什么情况" in (text or "")
        or "什么情况" in (ask_for_tone or "")
    )
    if want_cond and cond:
        # Prefer current turn for duration surface (resume may be bare「六个月不违法」)
        dur_surf = ""
        for src_q in (text, ask_for_tone):
            cand = _d69_dur_surface(src_q, hit.topic, hit.trigger or "")
            head = cand.split("合同", 1)[0].strip("，, ") if cand else ""
            if head and parse_duration(head) is not None:
                dur_surf = cand
                break
            if cand and parse_duration(cand) is not None:
                dur_surf = cand
                break
        if not dur_surf:
            dur_surf = _d69_dur_surface(text or ask_for_tone, hit.topic, hit.trigger or "")
        inv = bool(getattr(hit, "invert_polar", False)) or (
            (hit.trigger or "") in _NEG_TRIG
        )
        if hit.ok:
            if inv:
                spoken = f"{hit.topic}{dur_surf}不违法。相关规定：{cond}"
            else:
                spoken = f"{hit.topic}{dur_surf}在下列情况下合法：{cond}"
        else:
            spoken = f"{hit.topic}{dur_surf}不合法。相关规定：{cond}"
        return spoken

    return polar_spoken(
        ask_for_tone,
        hit.ok,
        trigger=getattr(hit, "trigger", "") or "",
        topic=hit.topic,
    )


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


def _clause_split(text: str) -> tuple[str, list[str], str] | None:
    # returns (link_rel, parts, rule_id) or None
    sys = load_system()
    for (a, b), rel, rule in sys.clause_pairs:
        if a in text and b in text:
            left = text.split(a, 1)[1].split(b, 1)[0]
            right = text.split(b, 1)[1]
            return rel, [left.strip("，, "), right.strip("，, ")], rule
    for mark, rel, rule, unless in sys.clause_singles:
        if mark not in text:
            continue
        if unless and unless in text:
            continue
        left, right = text.split(mark, 1)
        return rel, [left.strip("，, "), right.strip("，, ")], rule
    # 意合 (no explicit conj): A，B → because / then heuristic (D37y / D40y)
    return _clause_split_yihe(text)


_YIHE_CAUSE_LEFT = re.compile(
    r"(下雨|下雪|刮风|天[冷热黑亮]|地震|停电|堵车|.+了)$"
)


def _clause_split_yihe(text: str) -> tuple[str, list[str], str] | None:
    """Chinese parataxis: split on first comma when both halves look like clauses."""
    if "，" not in text and "," not in text:
        return None
    # Avoid breaking content / questions that already have WH
    if any(x in text for x in ("因为", "所以", "虽然", "但是", "如果", "的内容是")):
        return None
    sep = "，" if "，" in text else ","
    left, right = text.split(sep, 1)
    left, right = left.strip(), right.strip()
    if len(left) < 2 or len(right) < 2:
        return None
    if len(left) > 24 or len(right) > 30:
        return None
    # Cause-ish: weather/state + reaction (often with 不/没)
    if _YIHE_CAUSE_LEFT.search(left) or ("不" in right or "没" in right):
        if _YIHE_CAUSE_LEFT.search(left) or left.endswith("了"):
            return "cause", [left, right], "D37y"
    # Sequential fallback when both sides have enough substance
    if len(left) >= 3 and len(right) >= 3:
        return "before", [left, right], "D40y"
    return None


def _decode_clauses(
    machine: MachineWorld,
    session: Session,
    clause: tuple[str, list[str], str],
    *,
    write: bool,
) -> Result:
    rel, parts, rule = clause
    if len(parts) != 2 or not all(parts):
        return Result(ok=False, err="bad clause")
    if not write:
        # Chat: prefer already-written compound relations, else echo each half
        for atom in machine.facts:
            if atom.pred != "of" or len(atom.args) != 3 or atom.args[0] != rel:
                continue
            newer, older = atom.args[1], atom.args[2]
            if newer.startswith("e.") and older.startswith("e."):
                spoken = f"{_speak_event(machine, older)}，{_speak_event(machine, newer)}"
                return Result(ok=True, spoken=spoken, rule=f"{rule}.echo")
        spoken = None
        for part in parts:
            got = decode(machine, session, part, write=False)
            spoken = got.spoken or spoken
        return Result(ok=True, spoken=spoken or _empty_info(), rule=rule)
    eids: list[str] = []
    spoken = None
    for part in parts:
        before = _latest_event(machine)
        got = decode(machine, session, part, write=True)
        after = _latest_event(machine)
        # 意合 / negation halves often fail or only echo (D57) without a new event —
        # still allocate a stub so because/then can link the two clauses.
        if got.ok and after and after != before:
            eids.append(after)
            spoken = got.spoken or spoken
        else:
            pol = ""
            if got.ok and (got.rule or "").startswith("D57"):
                pol = "不"
            elif got.ok and (got.rule or "").startswith("D58"):
                pol = "没"
            eids.append(_stub_clause_event(machine, part, polarity=pol))
            spoken = got.spoken or spoken or "好的"
    if len(eids) == 2 and eids[0] and eids[1] and eids[0] != eids[1]:
        fx.link(machine, rel, eids[1], eids[0])
    return Result(ok=True, spoken=spoken or "好的", rule=rule, focus=session.focus(0))


def _stub_clause_event(
    machine: MachineWorld, text: str, *, polarity: str = ""
) -> str:
    """Minimal event for a clause half that did not write its own e.N."""
    eid = fx.write_event(machine, kind="say", agent="other", polarity=polarity)
    surface = (text or "").strip()
    if surface:
        fx.write_content(machine, eid, surface)
    return eid


def _latest_event(machine: MachineWorld) -> str:
    ids = [int(n[2:]) for n in machine.domain if n.startswith("e.") and n[2:].isdigit()]
    return f"e.{max(ids)}" if ids else ""


def _decode_statement(
    machine: MachineWorld,
    session: Session,
    senses: list[Sense],
    *,
    write: bool,
    mode: str = "basic",
) -> Result | None:
    names = _names(senses)
    ents = _ents(senses, session, machine)
    modal, modal_rule = _modal(senses)
    mood = _mood(senses)
    progress = "prog" in names

    special = bool(
        {"ba", "bei", "give_mark", "let", "help", "call", "invite", "cmp", "less", "target_mark", "dest_mark"}
        & set(names)
    )
    if mode == "special" and not special:
        return None

    # D3 copula: kind predicative → isa; individual → identity (basic; special skips)
    if mode != "special" and "copula" in names and "loc" not in names:
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
        # Query: identity first, then isa
        ids = _qfind(machine, session, f"?x of(identity, {subj}, x)")
        if ids.values:
            got = _prefer(session, ids.values)
            return Result(ok=True, spoken=_say_isa(subj, got), rule="D3.echo", focus=subj)
        kinds = _qfind(machine, session, f"?x isa({subj}, x)")
        if isinstance(kinds, FindResult) and kinds.values:
            got = _prefer(session, kinds.values)
            return Result(ok=True, spoken=_say_isa(subj, got), rule="D3.echo", focus=subj)
        return Result(ok=True, spoken=_empty_info(), rule="REN2")

    # D6 loc / D4–D5 have
    if mode != "special" and "loc" in names and not any(s.name in _VERBS for s in senses):
        if len(ents) < 2:
            return Result(ok=False, err="loc needs two")
        thing, place = ents[0], ents[1]
        if write:
            fx.write_located(machine, thing, place)
            session.push(thing)
            return Result(
                ok=True,
                spoken=_say_located(thing, place),
                rule="D6",
                focus=thing,
            )
        places = _qfind(machine, session, f"?x located({thing}, x)")
        if places.values:
            return Result(ok=True, spoken=_say_located(thing, places.values[0]), rule="D6.echo")
        return Result(ok=True, spoken=_empty_info(), rule="REN2")

    if mode != "special" and "have" in names:
        if len(ents) < 2:
            return Result(ok=False, err="have needs two")
        left, right = ents[0], ents[1]
        if write:
            if _placeish(left, machine) and not _personish(left, machine):
                fx.write_located(machine, right, left)  # D4
                session.push(right)
                return Result(ok=True, spoken=_say_has(left, right), rule="D4", focus=right)
            fx.write_has(machine, left, right)  # D5
            session.push(left)
            return Result(ok=True, spoken=_say_has(left, right), rule="D5", focus=left)
        if _placeish(left, machine):
            hits = _qfind(machine, session, f"?x located(x, {left})")
        else:
            hits = _qfind(machine, session, f"?x has({left}, x)")
        if hits.values:
            return Result(ok=True, spoken=_say_has(left, hits.values[0]), rule="have.echo")
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
                fx.ensure(machine, "negative")
                machine.tell(f"of(polarity, {left}, negative)")
            session.push(left)
            rule = "D19" if "less" in names else "D18"
            spoken = f"{_surf(left)}比{_surf(right)}{_surf(prop)}" if prop else f"{_surf(left)}比{_surf(right)}"
            if "less" in names:
                spoken = f"{_surf(left)}不如{_surf(right)}{_surf(prop)}" if prop else f"{_surf(left)}不如{_surf(right)}"
            return Result(ok=True, spoken=spoken, rule=rule, focus=left)
        hits = _qfind(machine, session, f"?x of(comparative, {left}, x)")
        if hits.values:
            right_got = hits.values[0]
            props = _qfind(machine, session, f"?x of(property, {left}, x)")
            prop_got = props.values[0] if props.values else ""
            neg_pol = machine.yes(f"of(polarity, {left}, negative)")
            if neg_pol:
                spoken = (
                    f"{_surf(left)}不如{_surf(right_got)}{_surf(prop_got)}"
                    if prop_got
                    else f"{_surf(left)}不如{_surf(right_got)}"
                )
                return Result(ok=True, spoken=spoken, rule="D19.echo")
            spoken = (
                f"{_surf(left)}比{_surf(right_got)}{_surf(prop_got)}"
                if prop_got
                else f"{_surf(left)}比{_surf(right_got)}"
            )
            return Result(ok=True, spoken=spoken, rule="D18.echo")
        return Result(ok=True, spoken=_empty_info(), rule="REN2")

    # D55 possessive X-de
    if "de" in names and len(ents) == 1 and not _verbs_in(senses):
        owner = ents[0]
        hits = _qfind(machine, session, f"?x has({owner}, x)")
        if not hits.values:
            hits = _qfind(machine, session, f"?x of(possession, {owner}, x)")
        if hits.values:
            session.push(hits.values[0])
            return Result(ok=True, spoken=_surf(hits.values[0]), rule="D55", focus=hits.values[0])
        if write:
            return Result(ok=False, err="D55 no possession")
        return Result(ok=True, spoken=_empty_info(), rule="REN2")

    # D56 num+clf: supply focus kind, count(isa(?x, kind))
    nums = [s.name for s in senses if s.name.startswith("n") and s.name[1:].isdigit()]
    if nums and "clf" in names and not _verbs_in(senses) and not ents:
        kind = session.focus(0)
        if not kind:
            return Result(ok=False, err="D56 needs focus")
        hits = _qfind(machine, session, f"?x isa(x, {kind})")
        # If focus is an individual, walk up to its kind then count
        if not hits.values:
            classes = _qfind(machine, session, f"?x isa({kind}, x)")
            if classes.values:
                kind = classes.values[0]
                hits = _qfind(machine, session, f"?x isa(x, {kind})")
        n = len(hits.values)
        tpl = form_tm("count") or ""
        spoken = tpl.replace("{0}", str(n)) + _surf(kind)
        return Result(ok=True, spoken=spoken, rule="D56", focus=kind)

    # D44 and/with
    if "with_mark" in names and not _verbs_in(senses):
        if write:
            for e in ents:
                fx.ensure(machine, e)
                session.push(e)
        return Result(ok=True, spoken="和".join(_surf(e) for e in ents), rule="D44")

    # Verb clauses D1/D2/D7–D17/D20 + serial/causative
    verbs = _verbs_in(senses)
    if not verbs:
        return None if mode == "special" else Result(ok=False, err="no pattern")

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

    # D8: loc/prog marker before verb → progressive (not location)
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

    if "bei" in names:  # D10: agent between bei…verb; elided → unknown
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
        # D16 give as preposition: subject give_mark object V …
        agent = before[0] if before else "other"
        gi = names.index("give_mark")
        mid = _ents(senses[gi + 1 : vi], session, machine)
        obj = mid[0] if mid else (after[0] if after else "")
        rule = "D16"
    elif kind == "give":  # D11
        agent = before[0] if before else "other"
        if len(after) == 1 and len(after[0]) > 2:
            blob = after[0]
            split_at = None
            for i in range(len(blob) - 1, 0, -1):
                left, right = blob[:i], blob[i:]
                # Person names at least 2 chars; avoid treating single-char adj constants as IO
                if len(left) < 2:
                    continue
                if left in machine.domain or right in machine.domain or len(right) >= 2:
                    split_at = i
                    break
            if split_at is None:
                split_at = 2 if len(blob) > 2 else 1
            after = [blob[:split_at], blob[split_at:]]
        if len(after) >= 2:
            recipient, obj = after[0], after[1]
        elif after:
            obj = after[0]
        rule = "D11"
    elif "target_mark" in names and kind in {"say", "talk"}:  # D17 say/talk/introduce only
        agent = before[0] if before else "other"
        ti = names.index("target_mark")
        mid = _ents(senses[ti + 1 : vi], session, machine)
        target = mid[0] if mid else ""
        obj = after[0] if after else ""
        rule = "D17"
    else:
        agent = before[0] if before else "other"
        obj = after[0] if after else ""

    # D20: V+dest_mark place; attach destination only for motion/place (avoid resultative false hits)
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

    # D49 object ellipsis → focus / last object (D54: no near fallback when far empty)
    filled_d49 = False
    if not obj and kind in _TRANS:
        if "that" in names and not session.focus(1):
            pass
        else:
            obj = session.focus(0) or session.last_to
            if obj:
                filled_d49 = True

    # D1 vs D2
    if kind in _INTRANS:
        obj = ""
    elif kind in _TRANS and not obj and write:
        return Result(ok=False, err="D1 needs object")

    if not rule:
        if filled_d49:
            rule = "D49"
        elif prog:
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
    elif recipient and obj:
        spoken = f"{_surf(agent)}{_surf(kind)}{_surf(recipient)}{_surf(obj)}"
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
    if not obj:
        obj = session.focus(0) or session.last_to
    if not pivot:
        return Result(ok=False, err="causative needs pivot")
    # D12 help; D15 let/call/make/order/invite/send
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
    if not o2:
        o2 = session.focus(0) or session.last_to
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

    # D24 polar can
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

        def _tag_spoken(ok: bool) -> str:
            base = _yes() if ok else _no()
            tones = load_system().tag_tones
            if qrule in tones:
                return f"{base}{tones[qrule]}"
            return base

        if "copula" in cn and len(ce) >= 2:
            ok = machine.yes(f"isa({ce[0]}, {ce[1]})") or machine.yes(
                f"of(identity, {ce[0]}, {ce[1]})"
            )
            if neg:
                ok = not ok
            return Result(ok=True, spoken=_tag_spoken(ok), rule=qrule)
        if "have" in cn and len(ce) >= 2:
            a, b = ce[0], ce[1]
            ok = machine.yes(f"has({a}, {b})") or machine.yes(f"located({b}, {a})")
            if neg:
                ok = not ok
            return Result(ok=True, spoken=_tag_spoken(ok), rule="D23" if qrule == "D21" else qrule)
        if "loc" in cn and len(ce) >= 2:
            ok = machine.yes(f"located({ce[0]}, {ce[1]})")
            if neg:
                ok = not ok
            return Result(ok=True, spoken=_tag_spoken(ok), rule=qrule)
        verbs = _verbs_in(core)
        if verbs:
            kind = verbs[0][1]
            vi = verbs[0][0]
            agent = (_ents(core[:vi], session, machine) or [""])[0]
            obj = (_ents(core[vi + 1 :], session, machine) or [""])[0]
            ok = bool(_events(machine, kind=kind, agent=agent, obj=obj))
            if neg:
                ok = not ok
            return Result(ok=True, spoken=_tag_spoken(ok), rule=qrule)
        return Result(ok=False, err="D21 no statement")

    if "polar_isa" in names and len(ents) >= 2:
        ok = machine.yes(f"isa({ents[0]}, {ents[1]})")
        return Result(ok=True, spoken=_yes() if ok else _no(), rule="D22")

    if "polar_have" in names and len(ents) >= 2:
        a, b = ents[0], ents[1]
        ok = machine.yes(f"has({a}, {b})") or machine.yes(f"located({b}, {a})")
        return Result(ok=True, spoken=_yes() if ok else _no(), rule="D23")

    # D25 / D26 / D28; to-whom → target (query paired with D17)
    if "who" in names:
        verbs = _verbs_in(senses)
        if not verbs:
            subj = ents[0] if ents else "me"
            hits = _qfind(machine, session, f"?x of(identity, {subj}, x)")
            if hits.values:
                return Result(ok=True, spoken=_say_isa(subj, hits.values[0]), rule="D28")
            kinds = _qfind(machine, session, f"?x isa({subj}, x)")
            if kinds.values:
                return Result(
                    ok=True,
                    spoken=_say_isa(subj, _prefer(session, kinds.values)),
                    rule="D27",
                )
            return Result(ok=True, spoken=_empty_q(), rule="REN2")
        kind = verbs[0][1]
        vi = verbs[0][0]
        after = _ents(senses[vi + 1 :], session, machine)
        who_i = next(i for i, s in enumerate(senses) if s.name == "who")
        # to-whom V → query target
        if "target_mark" in names and who_i > names.index("target_mark"):
            agent = (_ents(senses[: names.index("target_mark")], session, machine) or [""])[0]
            hits = _find_role(machine, "target", kind=kind, agent=agent, session=session)
            if hits:
                return Result(ok=True, spoken=_surf(hits[0]), rule="D17.q")
            return Result(ok=True, spoken=_empty_q(), rule="REN2")
        who_first = senses[0].name == "who"
        if who_first:
            obj = after[0] if after else ""
            hits = _find_agents(machine, kind, obj, session=session)
            if hits:
                return Result(ok=True, spoken=_surf(hits[0]), rule="D25")
            return Result(ok=True, spoken=_empty_q(), rule="REN2")
        agent = (_ents(senses[:vi], session, machine) or [""])[0]
        hits = _find_objects(machine, kind, agent, session=session)
        if hits:
            return Result(ok=True, spoken=_surf(hits[0]), rule="D26")
        return Result(ok=True, spoken=_empty_q(), rule="REN2")

    # D27 / QP3: what→object (with verb) or isa (no verb)
    if "what" in names:
        verbs = _verbs_in(senses)
        if verbs:
            kind = verbs[0][1]
            vi = verbs[0][0]
            agent = (_ents(senses[:vi], session, machine) or [""])[0]
            hits = _find_objects(machine, kind, agent, session=session)
            if hits:
                return Result(ok=True, spoken=_surf(hits[0]), rule="D26")
            return Result(ok=True, spoken=_empty_q(), rule="REN2")
        if ents:
            hits = _qfind(machine, session, f"?x isa({ents[0]}, x)")
            if hits.values:
                return Result(
                    ok=True,
                    spoken=_say_isa(ents[0], _prefer(session, hits.values)),
                    rule="D27",
                )
            return Result(ok=True, spoken=_empty_q(), rule="REN2")

    # D29 where; V+where → destination (paired with D20)
    if "where" in names:
        verbs = _verbs_in(senses)
        if verbs:
            kind = verbs[0][1]
            vi = verbs[0][0]
            agent = (_ents(senses[:vi], session, machine) or [""])[0]
            hits = _find_role(machine, "destination", kind=kind, agent=agent, session=session)
            if hits:
                return Result(
                    ok=True,
                    spoken=f"{_surf(agent)}{_surf(kind)}到{_surf(hits[0])}",
                    rule="D20.q",
                )
            return Result(ok=True, spoken=_empty_q(), rule="REN2")
        if ents:
            hits = _qfind(machine, session, f"?x located({ents[0]}, x)")
            if hits.values:
                return Result(
                    ok=True,
                    spoken=_say_located(ents[0], hits.values[0]),
                    rule="D29",
                )
            return Result(ok=True, spoken=_empty_q(), rule="REN2")
        return Result(ok=False, err="D29 needs entity")

    # D30 how
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

    # D31 why
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

    # D32 or
    if "or" in names and "copula" in names and len(ents) >= 3:
        subj, a, b = ents[0], ents[1], ents[2]
        if machine.yes(f"isa({subj}, {a})"):
            return Result(ok=True, spoken=_say_isa(subj, a), rule="D32")
        if machine.yes(f"isa({subj}, {b})"):
            return Result(ok=True, spoken=_say_isa(subj, b), rule="D32")
        return Result(ok=True, spoken=_empty_q(), rule="REN2")

    # D36 how-many: count(find ?x ∧ isa(?x, noun))
    if "howmany" in names:
        noun = ""
        subj = ""
        # Pattern: [{subject}] how-many [{clf}] {noun}
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
        # Aggregate: count(find isa(?x, noun)); subject does not change count semantics (by noun kind)
        del subj
        hits = _qfind(machine, session, f"?x isa(x, {noun})")
        n = len(hits.values)
        tpl = form_tm("count") or ""
        spoken = tpl.replace("{0}", str(n)) + _surf(noun)
        return Result(ok=True, spoken=spoken, rule="D36", focus=noun)

    return Result(ok=False, err="no query rule")


def _find_agents(
    machine: MachineWorld,
    kind: str,
    obj: str,
    *,
    session: Session | None = None,
) -> list[str]:
    out: list[str] = []
    for name in list(machine.domain):
        if not name.startswith("e."):
            continue
        if not machine.yes(f"of(kind, {name}, {kind})"):
            continue
        if obj and not machine.yes(f"of(object, {name}, {obj})"):
            continue
        if session is not None:
            agents = _qfind(machine, session, f"?x of(agent, {name}, x)")
        else:
            agents = machine.find(f"?x of(agent, {name}, x)")
        out.extend(agents.values)
    return list(dict.fromkeys(out))


def _find_objects(
    machine: MachineWorld,
    kind: str,
    agent: str,
    *,
    session: Session | None = None,
) -> list[str]:
    out: list[str] = []
    for name in list(machine.domain):
        if not name.startswith("e."):
            continue
        if not machine.yes(f"of(kind, {name}, {kind})"):
            continue
        if agent and not machine.yes(f"of(agent, {name}, {agent})"):
            continue
        if session is not None:
            objs = _qfind(machine, session, f"?x of(object, {name}, x)")
        else:
            objs = machine.find(f"?x of(object, {name}, x)")
        out.extend(objs.values)
    return list(dict.fromkeys(out))


def _find_role(
    machine: MachineWorld,
    role: str,
    *,
    kind: str = "",
    agent: str = "",
    session: Session | None = None,
) -> list[str]:
    out: list[str] = []
    for name in list(machine.domain):
        if not name.startswith("e."):
            continue
        if kind and not machine.yes(f"of(kind, {name}, {kind})"):
            continue
        if agent and not machine.yes(f"of(agent, {name}, {agent})"):
            continue
        if session is not None:
            hits = _qfind(machine, session, f"?x of({role}, {name}, x)")
        else:
            hits = machine.find(f"?x of({role}, {name}, x)")
        out.extend(hits.values)
    return list(dict.fromkeys(out))
