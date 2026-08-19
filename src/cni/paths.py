"""Project folders."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = ROOT / "knowledge"
WORLD_DIR = KNOWLEDGE_DIR / "world"
RUNTIME_DIR = ROOT / "runtime"
