"""Public decode contract: structured Chinese understanding for host systems.

In-scope + taught knowledge → faithful ops/answers.
Out-of-scope / unknown → refuse (miss). Never invent facts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from para.kernel.parse import Atom

Status = Literal["write", "query", "refuse", "error", "social"]


@dataclass(frozen=True)
class WorldFact:
    """One grounded world atom (user knowledge only)."""

    pred: str
    args: tuple[str, ...]

    @classmethod
    def from_atom(cls, atom: Atom) -> WorldFact:
        return cls(pred=atom.pred, args=tuple(atom.args))

    def to_dict(self) -> dict[str, Any]:
        return {"pred": self.pred, "args": list(self.args)}


@dataclass(frozen=True)
class KnowledgeHit:
    """Grounded knowledge that justifies the spoken answer (audit trail for hosts)."""

    kind: str  # cite | content | limit | fact
    text: str  # retrieved body (statute line, taught content, …)
    ref: str = ""  # addressable id, e.g. 劳动法第84行
    topic: str = ""  # judgment topic / focus entity

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "ref": self.ref,
            "text": self.text,
            "topic": self.topic,
        }


@dataclass(frozen=True)
class DecodeOutcome:
    """Plug-in result: host renders/stores; this engine only understands."""

    ok: bool
    status: Status
    rule: str
    text: str
    spoken: str = ""
    focus: str = ""
    facts_added: tuple[WorldFact, ...] = ()
    evidence: tuple[KnowledgeHit, ...] = ()
    miss: bool = False
    err: str = ""
    confidence: float = 1.0
    warn: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["facts_added"] = [f.to_dict() for f in self.facts_added]
        d["evidence"] = [e.to_dict() for e in self.evidence]
        return d


def classify_status(
    *,
    write: bool,
    ok: bool,
    rule: str,
    spoken: str,
    facts_added: tuple[WorldFact, ...],
    err: str,
) -> tuple[Status, bool]:
    """Map internal Result → public status + miss flag."""
    rule_l = (rule or "").casefold()
    if rule_l.startswith("i1") or rule_l in {"greet", "i1", "i2", "i3", "i10"}:
        return "social", False
    if write:
        if ok and facts_added:
            return "write", False
        if ok and spoken:
            # Acknowledgment without new atoms (e.g. WC1 duplicate)
            return "write", False
        return "error", True
    if not ok:
        return "error", True
    if rule_l in {"ren2", "ro3"} or rule_l.endswith(".ask"):
        # ask is intentional slot-fill, not a miss of understanding
        if rule_l.endswith(".ask"):
            return "query", False
        return "refuse", True
    if not (spoken or "").strip():
        return "refuse", True
    return "query", False


def facts_delta(before: set[Atom], after: set[Atom]) -> tuple[WorldFact, ...]:
    added = after - before
    return tuple(sorted((WorldFact.from_atom(a) for a in added), key=lambda f: (f.pred, f.args)))
