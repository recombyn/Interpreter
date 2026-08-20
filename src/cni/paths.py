"""Project folders: system knowledge vs user overrides."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = ROOT / "knowledge"
WORLD_DIR = KNOWLEDGE_DIR / "world"  # 系统：lang/base/lex/form/…
USER_DIR = KNOWLEDGE_DIR / "user"  # 用户：user_dict / entity_defaults
RUNTIME_DIR = ROOT / "runtime"
