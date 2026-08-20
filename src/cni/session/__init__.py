"""Session memory MEM1–MEM3. Facts stay in MachineWorld; pins are temporary."""

from __future__ import annotations

from dataclasses import dataclass, field

_RESET = {"重置", "新会话", "重新开始"}


@dataclass
class Session:
    focus_stack: list[str] = field(default_factory=list)
    max_focus: int = 5
    # MEM2 temporary pegs (not world facts)
    last_from: str = ""
    last_to: str = ""
    last_mark: str = ""
    last_event: str = ""

    def reset_if(self, text: str) -> bool:
        if text.strip() in _RESET:
            self.focus_stack.clear()
            self.last_from = self.last_to = self.last_mark = self.last_event = ""
            return True
        return False

    def push(self, name: str | None) -> None:
        if not name or name in {"me", "other", "unknown", "here", "now"}:
            return
        if name in self.focus_stack:
            self.focus_stack.remove(name)
        self.focus_stack.append(name)
        while len(self.focus_stack) > self.max_focus:
            self.focus_stack.pop(0)

    def focus(self, index: int = 0) -> str:
        if index < 0 or index >= len(self.focus_stack):
            return ""
        return self.focus_stack[-(index + 1)]

    def note(self, *, src: str = "", dst: str = "", mark: str = "", event: str = "") -> None:
        if src:
            self.last_from = src
        if dst:
            self.last_to = dst
        if mark:
            self.last_mark = mark
        if event:
            self.last_event = event
