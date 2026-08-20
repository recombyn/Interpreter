"""Application shell: boot + session + RO routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cni.kernel import MEMORY_PATH, MachineWorld, boot, save_world
from cni.knowledge import load_user_memories
from cni.paths import USER_DIR
from cni.route import hear, route, turn
from cni.session import Session
from cni.text.normalize import normalize_text
from cni.text.utf8 import as_text


@dataclass
class Trace:
    text: str
    reply: str
    notes: list[str] = field(default_factory=list)
    rule: str = ""


class Interpreter:
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
        self.world: MachineWorld = boot(
            memory_path=self.memory_path if remember else None,
            rules_path=Path(rules_path) if rules_path else None,
            infer_depth=infer_depth,
        )
        self.session = Session()
        self.user_docs: list[Path] = []
        if load_user_docs:
            self.user_docs = load_user_memories(self.world, self.user_dir)

    def teach(self, text: str | bytes) -> str:
        text = normalize_text(as_text(text))
        got = hear(self.world, self.session, text)
        if self.remember and got.ok:
            save_world(self.world, self.memory_path)
        return got.spoken or "教学格式错误"

    def reply(self, text: str | bytes, trace: bool = False) -> str | Trace:
        result = self.interpret(text)
        return result if trace else result.reply

    def interpret(self, text: str | bytes) -> Trace:
        text = normalize_text(as_text(text))
        before = self.world.inferred_count
        got = route(self.world, self.session, text)
        notes: list[str] = []
        if got.ok and got.spoken:
            notes.append("world")
        else:
            notes.append("world-miss")
        added = self.world.inferred_count - before
        if added:
            notes.append(f"infer:{added}")
        if got.rule:
            notes.append(got.rule)
        if getattr(got, "warn", ""):
            notes.append(got.warn)
        if getattr(got, "confidence", 1.0) < 0.99:
            notes.append(f"conf:{got.confidence:.2f}")
        if got.ok and got.spoken and self.remember and is_teach_reply(text):
            save_world(self.world, self.memory_path)
        return Trace(text=text, reply=got.spoken or "", notes=notes, rule=got.rule)


def is_teach_reply(text: str) -> bool:
    from cni.route import is_teach

    return is_teach(text)
