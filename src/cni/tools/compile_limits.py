"""Compile statute lines → knowledge/user/**/limits.tm (P2).

Scans user *.text/*.txt/*.md (including domain subfolders) for
「主题…不得超过/不少于…数值+单位」. Topics come from rules.tm (le/ge rules).

Usage: python -m cni.tools.compile_limits [--write]
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re

from cni.judge import load_judge_rules, parse_cn_int
from cni.paths import USER_DIR

# {topic}…不得超过|不多于|最长…不得超过 {num}{unit}
_CAP_TMPL = (
    r"(?P<topic>TOPICS).{0,40}?(?:最\s*长)?(?:不得\s*超过|不得\s*多于|不超过)"
    r"(?P<num>\d+|[一二两三四五六七八九十零〇]+)\s*"
    r"(?P<unit>个?月|个月|月|天|日|年)"
)
# {topic}…不得低于|不少于 {num}{unit}
_FLOOR_TMPL = (
    r"(?P<topic>TOPICS).{0,40}?(?:不得\s*低于|不得\s*少于|不少于)"
    r"(?P<num>\d+|[一二两三四五六七八九十零〇]+)\s*"
    r"(?P<unit>个?月|个月|月|天|日|年)"
)


@dataclass
class Extracted:
    topic: str
    key: str  # 上限 | 下限
    value: int
    unit: str
    source: str  # e.g. 劳动法第84行
    line_text: str


def _norm_unit(raw: str) -> str:
    if "月" in raw:
        return "月"
    if raw in {"天", "日"}:
        return "天"
    if "年" in raw:
        return "年"
    return raw


def extract_from_text(
    text: str,
    *,
    stem: str,
    line_no: int,
    topics: list[str],
) -> list[Extracted]:
    if not topics:
        return []
    # longest topics first in alternation
    alt = "|".join(re.escape(t) for t in sorted(topics, key=len, reverse=True))
    cap_re = re.compile(_CAP_TMPL.replace("TOPICS", alt))
    floor_re = re.compile(_FLOOR_TMPL.replace("TOPICS", alt))
    out: list[Extracted] = []
    source = f"{stem}第{line_no}行"
    for cre, key in ((cap_re, "上限"), (floor_re, "下限")):
        for m in cre.finditer(text):
            val = parse_cn_int(m.group("num"))
            if val is None:
                continue
            out.append(
                Extracted(
                    topic=m.group("topic"),
                    key=key,
                    value=val,
                    unit=_norm_unit(m.group("unit")),
                    source=source,
                    line_text=text.strip()[:80],
                )
            )
    return out


def scan_user_docs(user_dir: Path | None = None) -> list[Extracted]:
    from cni.knowledge.text_doc import list_user_texts

    root = user_dir or USER_DIR
    topics = sorted(
        {r.topic for r in load_judge_rules() if r.op in {"le", "ge", "lt", "gt", "eq"}},
        key=len,
        reverse=True,
    )
    found: list[Extracted] = []
    for path in list_user_texts(root):
        stem = path.stem
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines, start=1):
            cleaned = line.replace("**", "").replace("　", "")
            found.extend(
                extract_from_text(cleaned, stem=stem, line_no=i, topics=topics)
            )
    return found


def merge_limits(extracted: list[Extracted]) -> dict[tuple[str, str], Extracted]:
    """One (topic, key): for 上限 take max value; for 下限 take min."""
    best: dict[tuple[str, str], Extracted] = {}
    for ex in extracted:
        k = (ex.topic, ex.key)
        cur = best.get(k)
        if cur is None:
            best[k] = ex
            continue
        if ex.key == "上限" and ex.value > cur.value:
            best[k] = ex
        elif ex.key == "下限" and ex.value < cur.value:
            best[k] = ex
    return best


def render_limits_tm(
    merged: dict[tuple[str, str], Extracted],
    *,
    extra_lines: list[str] | None = None,
) -> str:
    lines = [
        "# 由 python -m cni.tools.compile_limits --write 生成（可手工改）",
        "# 多档上限取最大；多档下限取最小。出处 → of(出处, 主题, {stem}第N行)",
        "",
    ]
    entities: set[str] = set()
    nums: set[str] = set()
    units: set[str] = set()
    sources: set[str] = set()
    for ex in merged.values():
        entities.add(ex.topic)
        nums.add(str(ex.value))
        units.add(ex.unit)
        sources.add(ex.source)
    for name in sorted(entities | nums | units | sources | {"月", "天", "年"}):
        lines.append(f"! {name} : e")
    lines.append("")
    for (topic, key), ex in sorted(merged.items(), key=lambda x: (x[0][0], x[0][1])):
        lines.append(f"# {ex.source}: …{ex.line_text[:40]}…")
        lines.append(f"+ of({key}, {topic}, {ex.value})")
        lines.append(f"+ of(单位, {topic}, {ex.unit})")
        lines.append(f"+ of(出处, {topic}, {ex.source})")
        lines.append("")
    if extra_lines:
        lines.append("# --- 手工 / 枚举许可（compile 不覆盖此段时可另存）---")
        lines.extend(extra_lines)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


_ENUM_BLOCK = """
# --- 枚举许可 / 合取样本（compile 保留）---
! 合同类型 : e
! 固定期限 : e
! 无固定期限 : e
! 以完成一定工作任务为期限 : e
! 书面约定 : e
! 是 : e
+ of(许可, 合同类型, 固定期限)
+ of(许可, 合同类型, 无固定期限)
+ of(许可, 合同类型, 以完成一定工作任务为期限)
+ of(书面约定, 试用期, 是)
""".strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile statute caps → limits.tm")
    parser.add_argument("--write", action="store_true", help="write knowledge/user/limits.tm")
    parser.add_argument("--dir", default=str(USER_DIR))
    args = parser.parse_args(argv)
    root = Path(args.dir)
    extracted = scan_user_docs(root)
    merged = merge_limits(extracted)
    body = render_limits_tm(merged, extra_lines=_ENUM_BLOCK.splitlines())
    # Prefer domain folder when present (knowledge/user/劳动法/limits.tm)
    labor_dir = root / "劳动法"
    out = (labor_dir / "limits.tm") if labor_dir.is_dir() else (root / "limits.tm")
    if args.write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
        print(f"wrote {out} ({len(merged)} limit(s), {len(extracted)} hit(s))")
    else:
        print(body)
        print(f"# dry-run: {len(merged)} limit(s) from {len(extracted)} hit(s); pass --write to save")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
