"""User config keys from knowledge/user/config.tm (reply_mode, ambig_mode, …)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from cni.kernel.tmutil import clean
from cni.paths import USER_DIR

_CONFIG = USER_DIR / "config.tm"


@lru_cache(maxsize=4)
def load_user_config(path: str | None = None) -> dict[str, str]:
    """Parse `key value` lines; skip `default …` (handled by entity defaults)."""
    p = Path(path) if path else _CONFIG
    out: dict[str, str] = {}
    if not p.is_file():
        return out
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = clean(raw)
        if not line or line.startswith("default "):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[0].replace("_", "").isalnum():
            out[parts[0]] = parts[1].strip()
    return out


def reply_mode(path: str | None = None) -> str:
    mode = load_user_config(path).get("reply_mode", "default").casefold()
    if mode in {"true_false", "tf"}:
        return "bool"
    if mode in {"default", "bool", "zh_bool"}:
        return mode
    return "default"


def ambig_mode(path: str | None = None) -> str:
    """first = keep first D hit; clarify = ask when multi-rule; warn = answer + note."""
    mode = load_user_config(path).get("ambig_mode", "first").casefold()
    if mode in {"first", "clarify", "warn"}:
        return mode
    return "first"


def judge_cite(path: str | None = None) -> bool:
    """Append（见{出处}）on D69 answers when of(出处,…) exists."""
    raw = load_user_config(path).get("judge_cite", "on").casefold()
    return raw not in {"off", "false", "0", "no"}


def clear_user_config_cache() -> None:
    load_user_config.cache_clear()
