"""Compile domain .text → article→line maps (*.maps.tm) for user_dict merge.

Surface article labels are user-language (Chinese labor-law corpus).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from para.paths import USER_DIR

_ART = re.compile(r"\*\*第(?P<no>[一二三四五六七八九十百零〇\d]+)条\*\*")
_DEFAULT_STEM = "劳动法"


def extract_article_lines(text_path: Path) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for i, line in enumerate(text_path.read_text(encoding="utf-8").splitlines(), 1):
        m = _ART.search(line)
        if m:
            out.append((m.group("no"), i))
    return out


def render_maps(articles: list[tuple[str, int]], stem: str = _DEFAULT_STEM) -> str:
    lines = [
        f"# Auto from {stem}.text — map article → line (merged by load_user_dict)",
        "",
    ]
    for no, line_no in articles:
        lines.append(f"map {stem}第{no}条 {stem}第{line_no}行")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--dir", default=str(USER_DIR / _DEFAULT_STEM))
    args = parser.parse_args(argv)
    root = Path(args.dir)
    text = root / f"{_DEFAULT_STEM}.text"
    if not text.is_file():
        print(f"missing {text}")
        return 1
    arts = extract_article_lines(text)
    body = render_maps(arts)
    out = root / "article.maps.tm"
    if args.write:
        out.write_text(body, encoding="utf-8")
        print(f"wrote {out} ({len(arts)} maps)")
    else:
        print("\n".join(body.splitlines()[:8]))
        print(f"# {len(arts)} articles; pass --write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
