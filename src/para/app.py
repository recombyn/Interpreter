"""Application shell: boot + session + public decode API."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from para.api import DecodeOutcome, WorldFact, classify_status, facts_delta
from para.judge import clear_judge_cache
from para.kernel import MEMORY_PATH, MachineWorld, boot, save_world
from para.knowledge import load_user_memories
from para.paths import USER_DIR, set_user_dir
from para.preprocess import clear_user_dict_cache
from para.render.forms import clear_forms_cache
from para.route import hear, is_teach, strip_teach, turn
from para.session import Session
from para.suggest import attach_suggestions
from para.text.normalize import normalize_text
from para.text.utf8 import as_text
from para.user_config import clear_user_config_cache


@dataclass
class Trace:
    """Legacy chat trace; prefer DecodeOutcome for integrations."""

    text: str
    reply: str
    notes: list[str] = field(default_factory=list)
    rule: str = ""


class Para:
    """Pluggable Chinese decoder: grammar in package, knowledge from user_dir."""

    def __init__(
        self,
        remember: bool = False,
        memory_path: Path | None = None,
        rules_path: Path | None = None,
        infer_depth: int = 2,
        *,
        load_user_docs: bool = True,
        user_dir: Path | None = None,
    ) -> None:
        self.remember = remember
        self.memory_path = Path(memory_path) if memory_path else MEMORY_PATH
        self.user_dir = Path(user_dir) if user_dir else USER_DIR
        set_user_dir(self.user_dir)
        # Knowledge paths are cached; refresh when host swaps user_dir.
        clear_user_dict_cache()
        clear_judge_cache()
        clear_forms_cache()
        clear_user_config_cache()
        self.world: MachineWorld = boot(
            memory_path=self.memory_path if remember else None,
            rules_path=Path(rules_path) if rules_path else None,
            infer_depth=infer_depth,
        )
        self.session = Session()
        self.user_docs: list[Path] = []
        if load_user_docs:
            self.user_docs = load_user_memories(self.world, self.user_dir)

    def decode(
        self,
        text: str | bytes,
        *,
        write: bool | None = None,
    ) -> DecodeOutcome:
        """Primary host API: Chinese text → structured understanding.

        write=None: auto (teach-prefix → write path, else read-only).
        write=True/False: force hear / turn.
        """
        text = normalize_text(as_text(text))
        auto_teach = is_teach(text)
        do_write = auto_teach if write is None else write
        before = set(self.world.facts)
        if do_write:
            body = strip_teach(text) if auto_teach else text
            got = hear(self.world, self.session, body)
            if self.remember and got.ok:
                save_world(self.world, self.memory_path)
        else:
            got = turn(self.world, self.session, text)
            if self.remember and got.ok and auto_teach:
                save_world(self.world, self.memory_path)
        added = facts_delta(before, set(self.world.facts))
        spoken = got.spoken or ""
        status, miss = classify_status(
            write=do_write,
            ok=got.ok,
            rule=got.rule or "",
            spoken=spoken,
            facts_added=added,
            err=got.err or "",
        )
        # ok: host can trust the outcome as a successful understand/act
        trusted = status in {"write", "query", "social"} and bool(got.ok)
        evidence = tuple(getattr(got, "evidence", ()) or ())
        outcome = DecodeOutcome(
            ok=trusted,
            status=status,
            rule=got.rule or "",
            text=text,
            spoken=spoken,
            focus=got.focus or "",
            facts_added=added,
            evidence=evidence,
            miss=miss,
            err=got.err or "",
            confidence=getattr(got, "confidence", 1.0),
            warn=getattr(got, "warn", "") or "",
        )
        return attach_suggestions(outcome, user_dir=self.user_dir)

    def teach(self, text: str | bytes) -> str:
        return self.decode(text, write=True).spoken

    def reply(self, text: str | bytes, trace: bool = False) -> str | Trace:
        result = self.interpret(text)
        return result if trace else result.reply

    def interpret(self, text: str | bytes) -> Trace:
        """Chat-oriented wrapper around decode (keeps Trace notes)."""
        out = self.decode(text)
        notes: list[str] = []
        if out.miss:
            notes.append("world-miss")
        else:
            notes.append("world")
        if out.facts_added:
            notes.append(f"facts:+{len(out.facts_added)}")
        if out.rule:
            notes.append(out.rule)
        if out.warn:
            notes.append(out.warn)
        if out.confidence < 0.99:
            notes.append(f"conf:{out.confidence:.2f}")
        return Trace(text=out.text, reply=out.spoken, notes=notes, rule=out.rule)
