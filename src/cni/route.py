"""Operation routing RO1–RO3. Preprocess E→F→G→H→I then D."""

from __future__ import annotations

from datetime import date

from cni.decode import Result, decode
from cni.decode import effects as fx
from cni.decode.lex import pick_lex
from cni.kernel import MachineWorld
from cni.preprocess import PrepResult, preprocess
from cni.session import Session

_TEACH_PREFIX = ("教", "记住", "学习", "记")


def is_teach(text: str, *, mode: str | None = None) -> bool:
    if mode == "teach":
        return True
    return any(text.startswith(p) for p in _TEACH_PREFIX)


def strip_teach(text: str) -> str:
    for p in _TEACH_PREFIX:
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
        # I10：补 other 为施事，防无主语句死锁
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
    # RO3：解码失败或口头结果为空 → 不降级闲聊
    if not got.ok or not (got.spoken or "").strip():
        return Result(
            ok=False,
            spoken="教学格式错误",
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
    """RO2 read-only path：绝不写库。"""
    prep = _prep(machine, text, today=today)
    if prep.intercept is not None:
        return Result(ok=True, spoken=prep.intercept, rule=prep.intercept_rule)
    got = decode(machine, session, prep.text, write=False)
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
