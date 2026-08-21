"""Project folders: package world data vs user overrides."""

from __future__ import annotations

from pathlib import Path

# src/para/paths.py → repo root is parents[1]
PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parents[1]

# Bundled world data (lang/ontology/lex/forms), shipped with the package
WORLD_DIR = PKG_DIR / "data" / "world"

# User-editable config under knowledge/user/
KNOWLEDGE_DIR = ROOT / "knowledge"
USER_DIR = KNOWLEDGE_DIR / "user"

RUNTIME_DIR = ROOT / "runtime"

# Active plug-in knowledge root (Para sets this; tools/tests may override).
_active_user_dir: Path | None = None


def get_user_dir() -> Path:
    """Host knowledge directory for the current Para instance."""
    return _active_user_dir if _active_user_dir is not None else USER_DIR


def set_user_dir(path: Path | None) -> None:
    """Bind decode-time knowledge root (None → package default USER_DIR)."""
    global _active_user_dir
    _active_user_dir = Path(path) if path is not None else None
