from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cni.text.normalize import normalize_text
from cni.text.utf8 import as_text
from cni.world.lang import MEMORY_PATH, boot, save_world
from cni.world.translate import turn


@dataclass
class Trace:
    text: str
    reply: str
    notes: list[str] = field(default_factory=list)


class Interpreter:
    def __init__(
        self,
        remember: bool = False,
        memory_path: Path | None = None,
        rules_path: Path | None = None,
        infer_depth: int = 2,
    ) -> None:
        self.remember = remember
        self.memory_path = Path(memory_path) if memory_path else MEMORY_PATH
        self.speech = boot(
            memory_path=self.memory_path if remember else None,
            rules_path=Path(rules_path) if rules_path else None,
            infer_depth=infer_depth,
        )

    def reply(self, text: str | bytes, trace: bool = False) -> str | Trace:
        result = self.interpret(text)
        return result if trace else result.reply

    def interpret(self, text: str | bytes) -> Trace:
        text = normalize_text(as_text(text))
        before = self.speech.inferred_count
        spoken = turn(self.speech, text)
        added = self.speech.inferred_count - before
        notes = ["world"] if spoken is not None else ["world-miss"]
        if added:
            notes.append(f"infer:{added}")
        if spoken is not None and self.remember:
            save_world(self.speech, self.memory_path)
        return Trace(text=text, reply=spoken or "", notes=notes)
