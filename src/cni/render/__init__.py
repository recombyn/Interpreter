"""REN1–REN2 helpers (also inlined in decode for spoken forms)."""

from __future__ import annotations

from cni.decode.lex import form_of


def bare(pred: str, *args: str) -> str:
    return f"[原始逻辑] {pred}({','.join(args)})"


def unknown_q() -> str:
    return form_of("unknown_q") or "我不知道"


def unknown_info() -> str:
    return form_of("unknown_info") or "我不了解这个信息"


def teach_err() -> str:
    return form_of("teach_err") or "教学格式错误"
