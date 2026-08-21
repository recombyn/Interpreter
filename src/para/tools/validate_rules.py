"""Dev-time rules/config sanity checks (opt 6: pairwise D-pattern conflicts).

Usage: python -m para.tools.validate_rules
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from pathlib import Path
import re

from para.decode.route_table import load_route_groups
from para.kernel.tmutil import clean
from para.paths import USER_DIR, WORLD_DIR
from para.preprocess import load_user_dict
from para.system_tm import check_lex_skeleton, load_system

PATTERNS_PATH = WORLD_DIR / "patterns.tm"


@dataclass(frozen=True)
class RulePattern:
    rule: str
    pattern: str


@lru_cache(maxsize=1)
def load_patterns(path: Path | None = None) -> tuple[tuple[RulePattern, ...], frozenset[tuple[str, str]]]:
    path = path or PATTERNS_PATH
    patterns: list[RulePattern] = []
    prios: set[tuple[str, str]] = set()
    if not path.is_file():
        return (), frozenset()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = clean(raw)
        if not line:
            continue
        if line.startswith("pattern "):
            rest = line[len("pattern ") :].strip()
            rid, _, body = rest.partition(" ")
            patterns.append(RulePattern(rid.strip(), body.strip()))
        elif line.startswith("priority "):
            rest = line[len("priority ") :].strip()
            left, _, right = rest.partition(">")
            a, b = left.strip(), right.strip()
            if a and b:
                prios.add((a, b))
    return tuple(patterns), frozenset(prios)


def pattern_literals(pattern: str) -> tuple[str, ...]:
    """Extract fixed literals from a pattern (drop {slots})."""
    parts = re.split(r"\{[^}]+\}", pattern)
    return tuple(p.strip() for p in parts if p.strip())


def _is_subseq(short: tuple[str, ...], long: tuple[str, ...]) -> bool:
    if not short:
        return True
    i = 0
    for item in long:
        if item == short[i]:
            i += 1
            if i == len(short):
                return True
    return False


def patterns_overlap(a: RulePattern, b: RulePattern) -> bool:
    """Literal-token conflict: same tokens, pure-slot generalization, or one is an ordered subsequence of the other.

    Avoids false positives from .*? swallowing literals like ba/shi (e.g. D1 wrongly hitting D9).
    """
    la = pattern_literals(a.pattern)
    lb = pattern_literals(b.pattern)
    if la == lb:
        return True  # both empty of literals (D1↔D2) or identical tokens
    if not la or not lb:
        return True  # pure-slot generalization vs marked → needs priority
    if _is_subseq(la, lb) or _is_subseq(lb, la):
        return True
    return False


def has_priority(prios: frozenset[tuple[str, str]], a: str, b: str) -> bool:
    return (a, b) in prios or (b, a) in prios


def check_pattern_conflicts() -> list[str]:
    patterns, prios = load_patterns()
    errors: list[str] = []
    for left, right in combinations(patterns, 2):
        if not patterns_overlap(left, right):
            continue
        if has_priority(prios, left.rule, right.rule):
            continue
        errors.append(
            f"Rules {left.rule} and {right.rule} have overlapping matches: "
            f"'{left.pattern}' ∩ '{right.pattern}'; "
            f"suggestion: add priority {left.rule} > {right.rule} or tighten patterns"
        )
    return errors


def main() -> int:
    errors: list[str] = []
    warns: list[str] = []

    if (WORLD_DIR / "lex.en.tm").is_file():
        errors.append("Found lex.en.tm: system must not load an English lexicon directly")

    forbid = load_system().forbid_user_dict
    if not forbid:
        warns.append("system.tm did not load forbid_user_dict")

    dict_path = USER_DIR / "user_dict.tm"
    if dict_path.is_file():
        for raw in dict_path.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line.startswith("map "):
                continue
            src = line[4:].strip().split()[0].strip('"')
            if src in forbid:
                # File may contain the entry, but the load layer must ignore it
                warns.append(f"user_dict file contains forbidden source '{src}' (load layer should ignore)")

    loaded = {src for src, _ in load_user_dict()}
    for bad in forbid & loaded:
        errors.append(f"Loaded user_dict still contains forbidden entry '{bad}'")

    warns.extend(check_lex_skeleton().warns())

    if not (USER_DIR / "config.tm").is_file():
        warns.append("Missing knowledge/user/config.tm (G7–G10 will use built-in defaults)")

    if not load_route_groups():
        errors.append("route.tm did not load any groups")

    if not (WORLD_DIR / "patterns.tm").is_file():
        errors.append("Missing patterns.tm (cannot run D conflict checks)")
    else:
        errors.extend(check_pattern_conflicts())

    for w in warns:
        print(f"[WARN] {w}")
    for e in errors:
        print(f"[ERROR] {e}")
    if errors:
        return 1
    print("[OK] validate_rules passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
