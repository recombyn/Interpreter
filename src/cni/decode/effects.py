"""World effects: write helpers matching design wire (isa/of/located/has)."""

from __future__ import annotations

from cni.kernel import MachineWorld, Msg


def ensure(machine: MachineWorld, name: str) -> str:
    if name and name not in machine.domain:
        machine.ensure(name)
    return name


def new_event(machine: MachineWorld) -> str:
    n = 1
    while f"e.{n}" in machine.domain:
        n += 1
    eid = f"e.{n}"
    machine.ensure(eid)
    return eid


def write_event(
    machine: MachineWorld,
    *,
    kind: str,
    agent: str = "",
    obj: str = "",
    recipient: str = "",
    destination: str = "",
    target: str = "",
    progress: bool = False,
    modal: str = "",
    mood: str = "",
    polarity: str = "",
) -> str:
    eid = new_event(machine)
    ensure(machine, kind)
    machine.tell(f"of(kind, {eid}, {kind})")
    if agent:
        ensure(machine, agent)
        machine.tell(f"of(agent, {eid}, {agent})")
    if obj:
        ensure(machine, obj)
        machine.tell(f"of(object, {eid}, {obj})")
    if recipient:
        ensure(machine, recipient)
        machine.tell(f"of(recipient, {eid}, {recipient})")
    if destination:
        ensure(machine, destination)
        machine.tell(f"of(destination, {eid}, {destination})")
    if target:
        ensure(machine, target)
        machine.tell(f"of(target, {eid}, {target})")
    if progress:
        ensure(machine, "进行中")
        machine.tell(f"of(progress, {eid}, 进行中)")
    if modal:
        ensure(machine, modal)
        machine.tell(f"of(modal, {eid}, {modal})")
    if mood:
        ensure(machine, mood)
        machine.tell(f"of(mood, {eid}, {mood})")
    if polarity:
        ensure(machine, polarity)
        machine.tell(f"of(polarity, {eid}, {polarity})")
    return eid


def link(machine: MachineWorld, rel: str, newer: str, older: str) -> None:
    machine.tell(f"of({rel}, {newer}, {older})")


def write_isa(machine: MachineWorld, subj: str, kind: str) -> None:
    ensure(machine, subj)
    ensure(machine, kind)
    machine.tell(f"isa({subj}, {kind})")


def write_identity(machine: MachineWorld, left: str, right: str) -> None:
    ensure(machine, left)
    ensure(machine, right)
    machine.tell(f"of(identity, {left}, {right})")


def write_located(machine: MachineWorld, thing: str, place: str) -> None:
    ensure(machine, thing)
    ensure(machine, place)
    machine.tell(f"located({thing}, {place})")


def write_has(machine: MachineWorld, owner: str, thing: str) -> None:
    ensure(machine, owner)
    ensure(machine, thing)
    machine.tell(f"has({owner}, {thing})")


def write_cmp(machine: MachineWorld, left: str, right: str, prop: str = "") -> None:
    ensure(machine, left)
    ensure(machine, right)
    machine.tell(f"of(comparative, {left}, {right})")
    if prop:
        ensure(machine, prop)
        machine.tell(f"of(property, {left}, {prop})")


def write_forbid(machine: MachineWorld, verb: str, obj: str = "") -> None:
    """D59: wire via of(forbid, V, O) (lang has no forbid predicate)."""
    ensure(machine, "forbid")
    ensure(machine, verb)
    if obj:
        ensure(machine, obj)
        machine.tell(f"of(forbid, {verb}, {obj})")
    else:
        ensure(machine, "unknown")
        machine.tell(f"of(forbid, {verb}, unknown)")


def write_when(machine: MachineWorld, eid: str, when: str) -> None:
    ensure(machine, when)
    machine.tell(f"of(when, {eid}, {when})")


def write_degree(machine: MachineWorld, eid: str, value: str) -> None:
    ensure(machine, "degree")
    ensure(machine, value)
    machine.tell(f"of(degree, {eid}, {value})")


def write_freq(machine: MachineWorld, eid: str, value: str) -> None:
    ensure(machine, "freq")
    ensure(machine, value)
    machine.tell(f"of(freq, {eid}, {value})")


def write_scope(machine: MachineWorld, eid: str, value: str) -> None:
    ensure(machine, "scope")
    ensure(machine, value)
    machine.tell(f"of(scope, {eid}, {value})")


def write_mods(
    machine: MachineWorld,
    eid: str,
    *,
    when: str = "",
    degree: str = "",
    freq: str = "",
    scope: str = "",
) -> None:
    if when:
        write_when(machine, eid, when)
    if degree:
        write_degree(machine, eid, degree)
    if freq:
        write_freq(machine, eid, freq)
    if scope:
        write_scope(machine, eid, scope)


def write_content(machine: MachineWorld, entity: str, text: str) -> None:
    """D66: of(content, entity, text). Bypass string tell so commas/parens stay intact."""
    ensure(machine, "content")
    ensure(machine, entity)
    ensure(machine, text)
    machine.apply(Msg(act="tell", pred="of", args=["content", entity, text]))


def write_limit(
    machine: MachineWorld,
    entity: str,
    value: str,
    *,
    key: str = "上限",
    unit: str = "",
    source: str = "",
) -> None:
    """Numeric threshold: of(上限|下限, entity, value) and optional unit/source."""
    ensure(machine, key)
    ensure(machine, entity)
    ensure(machine, value)
    machine.apply(Msg(act="tell", pred="of", args=[key, entity, value]))
    if unit:
        ensure(machine, "单位")
        ensure(machine, unit)
        machine.apply(Msg(act="tell", pred="of", args=["单位", entity, unit]))
    if source:
        ensure(machine, "出处")
        ensure(machine, source)
        machine.apply(Msg(act="tell", pred="of", args=["出处", entity, source]))


def write_permit(machine: MachineWorld, entity: str, value: str) -> None:
    """Enum allow-list: of(许可, entity, value)."""
    ensure(machine, "许可")
    ensure(machine, entity)
    ensure(machine, value)
    machine.apply(Msg(act="tell", pred="of", args=["许可", entity, value]))
