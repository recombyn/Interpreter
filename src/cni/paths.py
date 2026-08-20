"""Project folders: package world data vs user overrides."""

from __future__ import annotations

from pathlib import Path

# src/cni/paths.py → package root is parent
PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parents[1]

# 引擎自带世界数据（语言/本体/词表/模板），随 cni 包分发 —— 不是「系统规则表」
WORLD_DIR = PKG_DIR / "data" / "world"

# 用户可改配置，仍在仓库 knowledge/user/
KNOWLEDGE_DIR = ROOT / "knowledge"
USER_DIR = KNOWLEDGE_DIR / "user"

RUNTIME_DIR = ROOT / "runtime"
