"""Operation routing RO1–RO3. Preprocess E→F→G→H→I then D."""

from __future__ import annotations

from datetime import date

from para.decode import Result, decode
from para.decode import effects as fx
from para.decode.lex import pick_lex
from para.kernel import MachineWorld
from para.preprocess import PrepResult, preprocess
from para.session import Session
from para.system_tm import load_system


def is_teach(text: str, *, mode: str | None = None) -> bool:
    if mode == "teach":
        return True
    return any(text.startswith(p) for p in load_system().teach_prefix)


def strip_teach(text: str) -> str:
    for p in load_system().teach_prefix:
        if text.startswith(p):
            return text[len(p) :].lstrip(" ：:")
    return text


def _prep(machine: MachineWorld, text: str, *, today: date | None = None) -> PrepResult:
    lex = pick_lex(text)
    return preprocess(text, vocab=lex.vocab, known=set(machine.domain), today=today)


def _attach_social(
    machine: MachineWorld, session: Session, prep: PrepResult, *, write: bool
) -> None:
    if not prep.mood and not prep.emphasis:
        return
    eid = session.last_event
    if not eid or eid not in machine.domain:
        if write and (prep.mood or prep.emphasis):
            eid = fx.new_event(machine)
            machine.tell(f"of(kind, {eid}, say)")
            machine.tell(f"of(agent, {eid}, other)")
            session.note(event=eid)
        else:
            return
    if prep.mood:
        fx.ensure(machine, prep.mood)
        machine.tell(f"of(mood, {eid}, {prep.mood})")
    if prep.emphasis:
        fx.ensure(machine, prep.emphasis)
        machine.tell(f"of(emphasis, {eid}, {prep.emphasis})")


def _handle_intercept(
    machine: MachineWorld,
    session: Session,
    prep: PrepResult,
    *,
    write: bool,
) -> Result:
    if prep.greet:
        eid = fx.new_event(machine)
        machine.tell(f"of(kind, {eid}, greet)")
        machine.tell(f"of(agent, {eid}, other)")
        machine.tell(f"of(object, {eid}, me)")
        session.note(event=eid)
    elif prep.farewell and write:
        eid = fx.new_event(machine)
        machine.tell(f"of(kind, {eid}, say)")
        machine.tell(f"of(agent, {eid}, other)")
        fx.ensure(machine, "farewell")
        machine.tell(f"of(mood, {eid}, farewell)")
        session.note(event=eid)
    elif prep.intercept_rule == "I10" and write:
        # I10: supply other as agent to avoid agentless-sentence deadlock
        eid = fx.new_event(machine)
        machine.tell(f"of(kind, {eid}, say)")
        machine.tell(f"of(agent, {eid}, other)")
        session.note(event=eid, src="other")
        session.push("other")
    elif prep.mood and write and not prep.greet:
        eid = fx.new_event(machine)
        machine.tell(f"of(kind, {eid}, say)")
        machine.tell(f"of(agent, {eid}, other)")
        fx.ensure(machine, prep.mood)
        machine.tell(f"of(mood, {eid}, {prep.mood})")
        session.note(event=eid)
    return Result(
        ok=True,
        spoken=prep.intercept or "",
        rule=prep.intercept_rule,
    )


def hear(
    machine: MachineWorld,
    session: Session,
    text: str,
    *,
    today: date | None = None,
) -> Result:
    """RO1 write path. RO3: failure stays failure."""
    prep = _prep(machine, text, today=today)
    if prep.intercept is not None:
        return _handle_intercept(machine, session, prep, write=True)
    got = decode(machine, session, prep.text, write=True)
    # RO3: decode failure or empty spoken → do not fall back to chat
    if not got.ok or not (got.spoken or "").strip():
        from para.render.forms import form as form_tm

        return Result(
            ok=False,
            spoken=form_tm("teach_err") or "",
            err=got.err or ("empty spoken" if got.ok else "decode fail"),
            rule="RO3",
        )
    _attach_social(machine, session, prep, write=True)
    if prep.notes:
        got.rule = f"{got.rule}+{'+'.join(prep.notes)}" if got.rule else "+".join(prep.notes)
    return got


def turn(
    machine: MachineWorld,
    session: Session,
    text: str,
    *,
    today: date | None = None,
) -> Result:
    """RO2 read-only path: never write the world."""
    raw_user = text.strip()
    # MEM4: short follow-up → D67 on pinned entity (session pins only; no open search)
    expanded = session.expand_short_ask(raw_user, domain=machine.domain)
    if expanded:
        raw_user = expanded

    prep = _prep(machine, raw_user, today=today)
    if prep.intercept is not None:
        return Result(ok=True, spoken=prep.intercept, rule=prep.intercept_rule)
    try:
        got = decode(machine, session, prep.text, write=False)
    except ValueError as exc:
        return Result(ok=False, err=str(exc), rule="ERR")
    # Unify empty / failed chat answers to REN2 spoken form
    if not (got.spoken or "").strip():
        from para.decode import _empty_q

        got = Result(
            ok=True,
            spoken=_empty_q(),
            rule=got.rule or "REN2",
            focus=got.focus,
            err=got.err,
            confidence=got.confidence,
            warn=got.warn,
            evidence=getattr(got, "evidence", ()) or (),
        )
    # Drop stale D69.ask pending once another rule answered
    if (got.rule or "") not in {"D69", "D69.ask"} and session.pending_judge_topic:
        session.pending_judge_topic = ""
        session.pending_judge_text = ""
    return got


def route(
    machine: MachineWorld,
    session: Session,
    text: str,
    *,
    mode: str | None = None,
    today: date | None = None,
) -> Result:
    if is_teach(text, mode=mode):
        return hear(machine, session, strip_teach(text), today=today)
    return turn(machine, session, text, today=today)
