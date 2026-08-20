"""Load form.tm outs (REN templates).

World defaults: src/cni/data/world/form.tm
User overrides: knowledge/user/form.tm (out lines merge on top)
Reply mode: knowledge/user/config.tm → reply_mode bool|zh_bool|default
  bool    → polar yes/no spoken as true/false
  zh_bool → polar yes/no spoken as 是/否
  default → keep form outs as written
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from cni.kernel.tmutil import clean
from cni.paths import USER_DIR, WORLD_DIR
from cni.user_config import clear_user_config_cache, reply_mode as _cfg_reply_mode

_OUT = re.compile(r"^out\s+(\S+)\s+(.+)$")

_MODE_BOOL = {"yes": "true", "no": "false"}
_MODE_ZH_BOOL = {"yes": "是", "no": "否"}


def _parse_outs(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    forms: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = clean(raw)
        if m := _OUT.match(line):
            forms[m.group(1)] = m.group(2)
    return forms


@lru_cache(maxsize=8)
def _load_forms_cached(world: str, user: str, mode: str) -> dict[str, str]:
    forms = _parse_outs(Path(world))
    forms.update(_parse_outs(Path(user)))
    if mode == "bool":
        forms.update(_MODE_BOOL)
    elif mode == "zh_bool":
        forms.update(_MODE_ZH_BOOL)
    return forms


def load_forms(
    path: Path | None = None,
    *,
    user_path: Path | None = None,
    reply_mode: str | None = None,
    config_path: Path | None = None,
) -> dict[str, str]:
    world = str(path or (WORLD_DIR / "form.tm"))
    user = str(user_path or (USER_DIR / "form.tm"))
    mode = reply_mode if reply_mode is not None else _cfg_reply_mode(
        str(config_path) if config_path else None
    )
    return _load_forms_cached(world, user, mode)


def form(const: str) -> str | None:
    return load_forms().get(const)


def clear_forms_cache() -> None:
    clear_user_config_cache()
    _load_forms_cached.cache_clear()
