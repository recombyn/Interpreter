"""Load src/para/data/world/system.tm — table-1 algorithm vocab/closed sets (not user dict)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from para.kernel.tmutil import clean
from para.paths import WORLD_DIR

SYSTEM_PATH = WORLD_DIR / "system.tm"


@dataclass
class SystemData:
    forbid_user_dict: frozenset[str] = frozenset()
    require_lex: frozenset[str] = frozenset()
    i_thanks: frozenset[str] = frozenset()
    i_greet: frozenset[str] = frozenset()
    i_bye: frozenset[str] = frozenset()
    i_ack: frozenset[str] = frozenset()
    i11_msg: str = "我擅长处理事实性问题，不懂诗词赏析。"
    i11_ask: tuple[str, ...] = ()
    i11_classical: tuple[str, ...] = ()
    i11_modern: tuple[str, ...] = ()
    teach_prefix: tuple[str, ...] = ()
    pin_groups: tuple[tuple[str, ...], ...] = ()
    f_verb_chars: str = ""
    f_verb_multi: tuple[str, ...] = ()
    f_adj_chars: str = ""
    f_complete: tuple[tuple[str, str], ...] = ()
    f_polar: tuple[tuple[str, str], ...] = ()
    f_prog_fixed: tuple[tuple[str, str], ...] = ()
    f_prog_map: tuple[tuple[str, str], ...] = ()
    f_source_suffix: str = "来的"
    f_source_rewrite: str = "是从哪里来"
    f_tell_pattern: str = r"讲(.+?)我知"
    f_tell_empty: str = "讲我知"
    f_tell_to: str = "告诉我"
    f_tail_many: tuple[str, ...] = ()
    rel_days: tuple[tuple[str, int], ...] = ()
    d66_next_subj: tuple[str, ...] = ()
    event_deixis: frozenset[str] = frozenset()
    struct_senses: frozenset[str] = frozenset()
    clause_pairs: tuple[tuple[tuple[str, str], str, str], ...] = ()
    # (mark, relation, rule, unless-contains — empty string means none)
    clause_singles: tuple[tuple[str, str, str, str], ...] = ()
    tag_tones: dict[str, str] = field(default_factory=dict)
    mem_reset: frozenset[str] = frozenset()


def _multi(store: dict[str, list[str]], key: str, rest: str) -> None:
    store.setdefault(key, []).extend(rest.split())


@lru_cache(maxsize=1)
def load_system(path: Path | None = None) -> SystemData:
    path = path or SYSTEM_PATH
    bag: dict[str, list[str]] = {}
    pairs: dict[str, list[tuple[str, ...]]] = {}
    clause_pairs: list[tuple[tuple[str, str], str, str]] = []
    clause_singles: list[tuple[str, str, str, str]] = []
    tag_tones: dict[str, str] = {}
    i11_msg = "我擅长处理事实性问题，不懂诗词赏析。"
    f_source_suffix = "来的"
    f_source_rewrite = "是从哪里来"
    f_tell_pattern = r"讲(.+?)我知"
    f_tell_empty = "讲我知"
    f_tell_to = "告诉我"

    if path.is_file():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = clean(raw)
            if not line:
                continue
            key, _, rest = line.partition(" ")
            rest = rest.strip()
            if not key:
                continue
            if key == "i11_msg":
                i11_msg = rest
            elif key == "f_source_suffix":
                f_source_suffix = rest
            elif key == "f_source_rewrite":
                f_source_rewrite = rest
            elif key == "f_tell_pattern":
                f_tell_pattern = rest
            elif key == "f_tell_empty":
                f_tell_empty = rest
            elif key == "f_tell_to":
                f_tell_to = rest
            elif key == "pin_group":
                parts = rest.split()
                if parts:
                    pairs.setdefault("pin_group", []).append(tuple(parts))
            elif key in {"f_complete", "f_polar", "f_prog_fixed", "f_prog_map"}:
                parts = rest.split(None, 1)
                if len(parts) == 2:
                    pairs.setdefault(key, []).append((parts[0], parts[1]))
            elif key == "rel_day":
                parts = rest.split()
                if len(parts) >= 2:
                    pairs.setdefault("rel_day", []).append((parts[0], parts[1]))
            elif key == "clause_pair":
                parts = rest.split()
                if len(parts) >= 4:
                    clause_pairs.append(((parts[0], parts[1]), parts[2], parts[3]))
            elif key == "clause_single":
                parts = rest.split()
                if len(parts) >= 3:
                    unless = parts[3] if len(parts) >= 4 else ""
                    clause_singles.append((parts[0], parts[1], parts[2], unless))
            elif key == "tag_tone":
                rid, _, tone = rest.partition(" ")
                if rid and tone:
                    tag_tones[rid.strip()] = tone.strip()
            elif key.startswith("f_verb_char") or key == "f_verb_char":
                _multi(bag, "f_verb_char", rest)
            elif key == "f_adj_char":
                _multi(bag, "f_adj_char", rest)
            else:
                _multi(bag, key, rest)

    def _fs(name: str) -> frozenset[str]:
        return frozenset(bag.get(name, ()))

    def _tu(name: str) -> tuple[str, ...]:
        return tuple(bag.get(name, ()))

    rel_days: list[tuple[str, int]] = []
    for word, off in pairs.get("rel_day", ()):
        try:
            rel_days.append((str(word), int(str(off))))
        except ValueError:
            continue

    return SystemData(
        forbid_user_dict=_fs("forbid_user_dict"),
        require_lex=_fs("require_lex"),
        i_thanks=_fs("i_thanks"),
        i_greet=_fs("i_greet"),
        i_bye=_fs("i_bye"),
        i_ack=_fs("i_ack"),
        i11_msg=i11_msg,
        i11_ask=_tu("i11_ask"),
        i11_classical=_tu("i11_classical"),
        i11_modern=_tu("i11_modern"),
        teach_prefix=_tu("teach_prefix"),
        pin_groups=tuple(pairs.get("pin_group", ())),
        f_verb_chars="".join(bag.get("f_verb_char", ())),
        f_verb_multi=_tu("f_verb_multi"),
        f_adj_chars="".join(bag.get("f_adj_char", ())),
        f_complete=tuple(pairs.get("f_complete", ())),  # type: ignore[arg-type]
        f_polar=tuple(pairs.get("f_polar", ())),  # type: ignore[arg-type]
        f_prog_fixed=tuple(pairs.get("f_prog_fixed", ())),  # type: ignore[arg-type]
        f_prog_map=tuple(pairs.get("f_prog_map", ())),  # type: ignore[arg-type]
        f_source_suffix=f_source_suffix,
        f_source_rewrite=f_source_rewrite,
        f_tell_pattern=f_tell_pattern,
        f_tell_empty=f_tell_empty,
        f_tell_to=f_tell_to,
        f_tail_many=_tu("f_tail_many"),
        rel_days=tuple(rel_days),
        d66_next_subj=_tu("d66_next_subj"),
        event_deixis=_fs("event_deixis"),
        struct_senses=_fs("struct_sense"),
        clause_pairs=tuple(clause_pairs),
        clause_singles=tuple(clause_singles),
        tag_tones=tag_tones,
        mem_reset=_fs("mem_reset"),
    )


def clear_system_cache() -> None:
    """Alias of clear_tm_caches (kept for older scripts)."""
    clear_tm_caches()


def clear_tm_caches() -> None:
    """Clear system.tm and dependent caches (user_dict filter, pin map, D66 regex)."""
    load_system.cache_clear()
    from para.text.d66 import clear_d66_cache

    clear_d66_cache()
    # Lazy imports: avoid circular deps with preprocess/repair at module load
    from para.preprocess import load_user_dict
    from para.repair import clear_pin_map_cache
    from para.render.forms import clear_forms_cache
    from para.user_config import clear_user_config_cache

    load_user_dict.cache_clear()
    clear_pin_map_cache()
    clear_forms_cache()
    clear_user_config_cache()


@dataclass(frozen=True)
class LexSkeletonReport:
    """Lex skeleton check result: require_lex ⊆ lex.ch.to_sense."""

    configured: bool
    required: frozenset[str]
    missing: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.configured and not self.missing

    def warns(self) -> list[str]:
        if not self.configured:
            return ["system.tm has no require_lex configured (skipping lex skeleton check)"]
        return [
            f"lex.ch missing structural surface '{s}' (system.tm require_lex)" for s in self.missing
        ]


def check_lex_skeleton(lex_vocab: set[str] | None = None) -> LexSkeletonReport:
    """Run skeleton check: read system.tm.require_lex against Chinese lex surfaces."""
    required = load_system().require_lex
    if not required:
        return LexSkeletonReport(configured=False, required=frozenset(), missing=())
    if lex_vocab is None:
        from para.decode.lex import lex_ch

        lex_vocab = set(lex_ch().to_sense)
    missing = tuple(sorted(s for s in required if s not in lex_vocab))
    return LexSkeletonReport(configured=True, required=required, missing=missing)
