"""Load form.tm outs (REN templates)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from cni.kernel.tmutil import clean
from cni.paths import WORLD_DIR

_OUT = re.compile(r"^out\s+(\S+)\s+(.+)$")


@lru_cache(maxsize=1)
def load_forms(path: Path | None = None) -> dict[str, str]:
    path = path or (WORLD_DIR / "form.tm")
    if not path.is_file():
        return {}
    forms: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = clean(raw)
        if m := _OUT.match(line):
            forms[m.group(1)] = m.group(2)
    return forms


def form(const: str) -> str | None:
    return load_forms().get(const)
