"""Opt 3: short-circuit by route.tm feature groups (social in preprocess; D groups here)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import re

from para.kernel.tmutil import clean
from para.paths import WORLD_DIR

ROUTE_PATH = WORLD_DIR / "route.tm"


@dataclass
class RouteGroup:
    name: str
    features: list[str] = field(default_factory=list)
    rules: str = ""


@lru_cache(maxsize=1)
def load_route_groups(path: Path | None = None) -> tuple[RouteGroup, ...]:
    path = path or ROUTE_PATH
    if not path.is_file():
        return ()
    groups: list[RouteGroup] = []
    cur: RouteGroup | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = clean(raw)
        if not line:
            continue
        if line.startswith("group "):
            if cur:
                groups.append(cur)
            cur = RouteGroup(name=line.split(None, 1)[1].strip())
            continue
        if cur is None:
            continue
        if line.startswith("features"):
            rest = line[len("features") :].strip()
            cur.features = rest.split() if rest else []
        elif line.startswith("rules"):
            cur.rules = line[len("rules") :].strip()
    if cur:
        groups.append(cur)
    return tuple(groups)


def classify_buckets(text: str, names: list[str] | None = None) -> list[str]:
    """Return group names to try in order (excludes social — handled by I in preprocess).

    Rules: collect feature hits first; keep table order; basic always last.
    When query features hit, do not insert special before query (table: special and non-interrogative).
    """
    groups = load_route_groups()
    if not groups:
        return ["query", "compound", "special", "deixis", "basic"]

    hit: list[str] = []
    query_hit = False
    for g in groups:
        if g.name == "social":
            continue
        if g.name == "basic":
            continue
        if not g.features:
            continue
        if any(f in text for f in g.features):
            if g.name == "query":
                query_hit = True
            if g.name == "special" and query_hit:
                continue
            if g.name not in hit:
                hit.append(g.name)

    # Sense-name supplements (after tokenize)
    name_set = set(names or ())
    if name_set & {
        "ask",
        "who",
        "what",
        "where",
        "how",
        "why",
        "howmany",
        "or",
        "polar_isa",
        "polar_have",
        "polar_can",
        "tag_right",
        "tag_isa",
        "rhetorical",
    }:
        if "query" not in hit:
            hit.insert(0, "query")
        query_hit = True
    if name_set & {"ba", "bei", "give_mark", "let", "help", "cmp", "less", "dest_mark", "target_mark"}:
        if not query_hit and "special" not in hit:
            # Insert after compound, before basic
            if "compound" in hit:
                i = hit.index("compound") + 1
                hit.insert(i, "special")
            else:
                hit.append("special")

    # 意合: has comma but no conj feature → still try compound (D37y/D40y)
    if ("，" in text or "," in text) and "compound" not in hit:
        hit.append("compound")

    # Stable table order: query → compound → special → deixis → basic
    order = ["query", "compound", "special", "deixis", "basic"]
    ordered = [g for g in order if g in hit]
    if "basic" not in ordered:
        ordered.append("basic")
    return ordered
