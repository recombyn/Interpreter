"""Sync knowledge/user/*.{text,txt,md,mk,markdown} → sibling .tm memory files.

Usage: python -m para.tools.sync_user_docs [--force]
"""

from __future__ import annotations

import argparse

from para.knowledge.text_doc import TEXT_SUFFIXES, sync_user_docs
from para.paths import USER_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync user text docs to .tm")
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild even if .tm is newer than source",
    )
    parser.add_argument(
        "--dir",
        default=str(USER_DIR),
        help="user knowledge directory (default: knowledge/user)",
    )
    args = parser.parse_args(argv)
    from pathlib import Path

    written = sync_user_docs(Path(args.dir), force=args.force)
    print(f"synced {len(written)} file(s); suffixes={', '.join(TEXT_SUFFIXES)}")
    for path in written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
