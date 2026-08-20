"""REN1–REN2 helpers (also inlined in decode for spoken forms)."""

from __future__ import annotations

from cni.render.forms import form


def bare(pred: str, *args: str) -> str:
    return f"[原始逻辑] {pred}({','.join(args)})"


def unknown_q() -> str:
    return form("unknown_q") or ""


def unknown_info() -> str:
    return form("unknown_info") or ""


def teach_err() -> str:
    return form("teach_err") or ""
