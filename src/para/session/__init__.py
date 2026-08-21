"""Session memory MEM1–MEM3. Facts stay in MachineWorld; pins are temporary.

Layers:
  entity_focus (focus_stack) — nominal individuals for deixis / D67
  event_focus (event_stack) — event ids
  doc_focus — current user-doc stem (disambiguation)
  topic_focus — recent content terms (short-ask completion)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from para.system_tm import load_system

# Follow-ups that should reuse pinned entity/doc (not full new questions)
_LEGALITY_ASK = (
    r"不违法吗|违法吗|合不合法|合法吗|合规吗|可以吗|对吗|行吗|是吗|呢吗|不违法|合法|违法"
)
_SHORT_ASK = re.compile(
    rf"^(那呢|呢|呢？|那\s*[？?]?|然后呢|还有呢|这个呢|那个呢|"
    rf"{_LEGALITY_ASK}|"
    rf"什么|为什么|怎么|怎样|如何)\s*[？?]?\s*$"
)
_LEGALITY_ONLY = re.compile(rf"^({_LEGALITY_ASK})\s*[？?]?\s*$")
# 「六个月不违法」/「6个月合法吗」 with judge-topic pin
_DUR_LEGALITY = re.compile(
    rf"^((?:\d+|[一二两三四五六七八九十零〇]+)\s*(?:个?月|个月|月|天|日|年)"
    rf"|(?:\d+|[一二两三四五六七八九十])?\s*个?半\s*(?:个?月|个月|月|天|日|年)"
    rf"|(?:\d+|[一二两三四五六七八九十零〇]+)\s*周)"
    rf"({_LEGALITY_ASK})\s*[？?]?\s*$"
)


@dataclass
class Session:
    # Compat old name: focus_stack == entity pin
    focus_stack: list[str] = field(default_factory=list)
    event_stack: list[str] = field(default_factory=list)
    max_focus: int = 5
    # Document / topic pins (dialogue memory; not world facts)
    doc_focus: str = ""
    topic_focus: list[str] = field(default_factory=list)
    max_topics: int = 8
    last_rule: str = ""
    # Lightweight coref beyond focus_stack (MEM5): mention order + last event roles
    coref_chain: list[str] = field(default_factory=list)
    max_coref: int = 8
    last_agent: str = ""
    last_patient: str = ""
    # MEM2 temporary pegs (not world facts)
    last_from: str = ""
    last_to: str = ""
    last_mark: str = ""
    last_event: str = ""
    # D69.ask: waiting for duration / enum / conjunction affirm
    pending_judge_topic: str = ""
    pending_judge_text: str = ""

    def reset_if(self, text: str) -> bool:
        if text.strip() in load_system().mem_reset:
            self.focus_stack.clear()
            self.event_stack.clear()
            self.topic_focus.clear()
            self.coref_chain.clear()
            self.doc_focus = ""
            self.last_rule = ""
            self.last_agent = self.last_patient = ""
            self.last_from = self.last_to = self.last_mark = self.last_event = ""
            self.pending_judge_topic = ""
            self.pending_judge_text = ""
            return True
        return False

    def push(self, name: str | None) -> None:
        """Push onto entity_focus (nominal individual)."""
        if not name or name in {"me", "other", "unknown", "here", "now"}:
            return
        if name.startswith("e.") and name[2:].isdigit():
            self.push_event(name)
            return
        if name in self.focus_stack:
            self.focus_stack.remove(name)
        self.focus_stack.append(name)
        while len(self.focus_stack) > self.max_focus:
            self.focus_stack.pop(0)
        self._coref_mention(name)
        # Infer doc stem from 劳动法／xxx第N行
        m = re.match(r"^([\u4e00-\u9fff]{2,30})第\d+行$", name)
        if m:
            self.set_doc(m.group(1))

    def _coref_mention(self, name: str) -> None:
        if not name or name in {"me", "other", "unknown", "here", "now"}:
            return
        if name.startswith("e.") and name[2:].isdigit():
            return
        if self.coref_chain and self.coref_chain[-1] == name:
            return
        if name in self.coref_chain:
            self.coref_chain.remove(name)
        self.coref_chain.append(name)
        while len(self.coref_chain) > self.max_coref:
            self.coref_chain.pop(0)

    def resolve_ana(self) -> str:
        """D52: 他/她 — prefer last patient, else focus, else coref tip."""
        if self.last_patient:
            return self.last_patient
        top = self.focus(0)
        if top:
            return top
        if self.coref_chain:
            return self.coref_chain[-1]
        return ""

    def push_event(self, eid: str | None) -> None:
        """Push onto event_focus (event id)."""
        if not eid or not eid.startswith("e."):
            return
        if eid in self.event_stack:
            self.event_stack.remove(eid)
        self.event_stack.append(eid)
        while len(self.event_stack) > self.max_focus:
            self.event_stack.pop(0)

    def set_doc(self, doc: str) -> None:
        doc = (doc or "").strip()
        if not doc:
            return
        if self.doc_focus and self.doc_focus != doc:
            # Switching document: drop entity/topic pins from the old doc
            self.focus_stack = [e for e in self.focus_stack if not e.startswith(self.doc_focus)]
            self.topic_focus.clear()
        self.doc_focus = doc

    def add_topics(self, terms: list[str] | tuple[str, ...] | str) -> None:
        if isinstance(terms, str):
            terms = [terms]
        for t in terms:
            t = (t or "").strip()
            if len(t) < 2 or t in {"内容", "什么", "原文"}:
                continue
            if t in self.topic_focus:
                self.topic_focus.remove(t)
            self.topic_focus.append(t)
        while len(self.topic_focus) > self.max_topics:
            self.topic_focus.pop(0)

    def note_content_hit(self, entity: str, body: str = "", *, rule: str = "") -> None:
        """After D66/D67 success: pin entity, doc, light topics from body."""
        self.push(entity)
        if rule:
            self.last_rule = rule
            self.last_mark = rule
        if body:
            # Prefer longer CJK runs as topic pins
            for m in re.finditer(r"[\u4e00-\u9fff]{2,6}", body):
                self.add_topics(m.group(0))
                if len(self.topic_focus) >= self.max_topics:
                    break

    def focus(self, index: int = 0) -> str:
        if index < 0 or index >= len(self.focus_stack):
            return ""
        return self.focus_stack[-(index + 1)]

    def focus_event(self, index: int = 0) -> str:
        if index < 0 or index >= len(self.event_stack):
            return ""
        return self.event_stack[-(index + 1)]

    def resolve_deixis(self, *, far: bool = False, eventish: bool = False) -> str:
        """This/that: with event classifiers → event stack; else entity stack. Far deixis uses [1]."""
        idx = 1 if far else 0
        if eventish:
            return self.focus_event(idx) or self.focus_event(0) or self.last_event
        return self.focus(idx)

    def is_short_ask(self, text: str) -> bool:
        t = text.strip()
        if not t:
            return False
        if _SHORT_ASK.match(t):
            return True
        # Very short follow-up with question mark and an active pin.
        # Keep ≤4 so full polars like「电脑是机器吗」(6) are not MEM4-rewritten.
        if len(t) <= 4 and t.endswith(("吗", "呢", "？", "?")) and (
            self.focus(0) or self.doc_focus or self.topic_focus
        ):
            return True
        return False

    def qualify_entity(self, entity: str, domain: set[str] | dict | None = None) -> str:
        """Disambiguate bare 第N行 with doc_focus when the qualified name exists."""
        entity = (entity or "").strip()
        if not entity or not self.doc_focus:
            return entity
        if entity.startswith(self.doc_focus):
            return entity
        if not re.fullmatch(r"第\d+行", entity):
            return entity
        qual = f"{self.doc_focus}{entity}"
        if domain is None or qual in domain:
            return qual
        return entity

    def pinned_content_entity(self, domain: set[str] | dict | None = None) -> str:
        """Best entity pin for D67 / MEM4, preferring doc-qualified names."""
        ent = self.focus(0)
        if not ent:
            return ""
        return self.qualify_entity(ent, domain)

    def expand_short_ask(self, text: str, domain: set[str] | dict | None = None) -> str | None:
        """Map short follow-up → D67 or D69 form using pinned entity (no open search)."""
        if "的内容是什么" in text:
            return None
        ent = self.pinned_content_entity(domain) or self.focus(0)
        # Duration + legality with judge-topic pin (e.g. 六个月不违法 → 试用期六个月不违法)
        if ent:
            try:
                from para.judge import judge_topics, parse_duration

                if ent in judge_topics():
                    m = _DUR_LEGALITY.match(text.strip())
                    if m is not None and parse_duration(m.group(1)) is not None:
                        return f"{ent}{m.group(1)}{m.group(2)}"
            except Exception:
                pass
        if not self.is_short_ask(text):
            return None
        if not ent:
            return None
        # MEM4 → D69 when pin is a judge topic; keep the user's trigger wording
        t = text.strip()
        if _LEGALITY_ONLY.fullmatch(t):
            try:
                from para.judge import judge_topics

                if ent in judge_topics():
                    cue = _LEGALITY_ONLY.match(t).group(1)  # type: ignore[union-attr]
                    return f"{ent}{cue}"
            except Exception:
                pass
            # Legality short-ask on non-judge pin must not become D67 content
            return None
        return f"{ent}的内容是什么"

    def note(self, *, src: str = "", dst: str = "", mark: str = "", event: str = "") -> None:
        if src:
            self.last_from = src
            self.last_agent = src
            self._coref_mention(src)
        if dst:
            self.last_to = dst
            self.last_patient = dst
            self._coref_mention(dst)
        if mark:
            self.last_mark = mark
        if event:
            self.last_event = event
            self.push_event(event)
