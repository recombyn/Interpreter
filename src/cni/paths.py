"""Project folders: package world data vs user overrides."""

from __future__ import annotations

from pathlib import Path

# src/cni/paths.py → package root is parent
PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parents[1]

# Bundled world data (lang/ontology/lex/forms), shipped with the cni package — not a 'system rules table'
WORLD_DIR = PKG_DIR / "data" / "world"

# User-editable config, still under knowledge/user/ in the repo
KNOWLEDGE_DIR = ROOT / "knowledge"
USER_DIR = KNOWLEDGE_DIR / "user"

RUNTIME_DIR = ROOT / "runtime"
