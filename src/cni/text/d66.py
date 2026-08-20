"""D66 content-clause match and body clipping (shared by preprocess / decode)."""

from __future__ import annotations

from functools import lru_cache
import re

from cni.system_tm import load_system

D66_CONTENT_RE = re.compile(r"^(.+?)\s*的内容是\s*(.+)$")
_D66_STOP = re.compile(r"[。！？!?]")


@lru_cache(maxsize=4)
def _next_subj_re(subs: tuple[str, ...]) -> re.Pattern[str] | None:
    if not subs:
        return None
    return re.compile(r"[，,](" + "|".join(re.escape(s) for s in subs) + ")")


def clip_d66_content(text: str) -> str:
    """Stop at sentence-final punctuation, or a following subject after a comma (system.tm d66_next_subj)."""
    text = text.strip()
    m = _D66_STOP.search(text)
    if m:
        text = text[: m.start()]
    nxt = _next_subj_re(load_system().d66_next_subj)
    if nxt is not None:
        m2 = nxt.search(text)
        if m2:
            text = text[: m2.start()]
    return text.strip()


def clear_d66_cache() -> None:
    _next_subj_re.cache_clear()
