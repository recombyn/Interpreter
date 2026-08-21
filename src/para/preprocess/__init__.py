"""Preprocess: E → user_dict → F41–50 → G → I.

Table-1 algorithms + system.tm closed sets: E / F41–50 / G / I1–3 / I7–8 / I10–I11
Table-2 lookup: F1–40 / H / I4–6 / I9 → knowledge/user/user_dict.tm
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
import re

from para.kernel.tmutil import clean
from para.paths import WORLD_DIR, get_user_dir
from para.repair import repair
from para.system_tm import load_system
from para.text.d66 import D66_CONTENT_RE, clip_d66_content

SYSTEM_PATH = WORLD_DIR / "system.tm"


@dataclass
class PrepResult:
    text: str
    mood: str = ""
    emphasis: str = ""
    intercept: str | None = None
    intercept_rule: str = ""
    greet: bool = False
    farewell: bool = False
    notes: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def load_entity_defaults(path: Path | None = None) -> dict[str, str]:
    """G7–G10 defaults from knowledge/user/config.tm."""
    out: dict[str, str] = {
        "几十": "30",
        "大半": "70%",
        "一小会儿": "5分钟",
        "三五": "3-5",
    }
    p = path if path is not None else (get_user_dir() / "config.tm")
    if p.is_file():
        for raw in p.read_text(encoding="utf-8").splitlines():
            line = clean(raw)
            if not line.startswith("default"):
                continue
            parts = line.split(maxsplit=2)
            if len(parts) == 3 and parts[1] in out:
                out[parts[1]] = parts[2]
    return out


def _user_dict_src_allowed(src: str) -> bool:
    """Opt 1: forbid replacing structural words (by surface + lex.ch sense)."""
    sys = load_system()
    if src in sys.forbid_user_dict:
        return False
    try:
        from para.decode.lex import lex_ch

        sense = lex_ch().to_sense.get(src)
        if sense in sys.struct_senses:
            return False
    except Exception:
        pass
    return True


@lru_cache(maxsize=8)
def _load_user_dict_cached(path_key: str | None, root_key: str) -> list[tuple[str, str]]:
    """Table 2: user-maintained source→standard (+ domain *.maps.tm under active user_dir)."""
    pairs: list[tuple[str, str]] = []
    files: list[Path] = []
    if path_key is not None:
        files.append(Path(path_key))
    else:
        root = Path(root_key)
        files.append(root / "user_dict.tm")
        if root.is_dir():
            files.extend(sorted(root.rglob("*.maps.tm")))
    seen: set[Path] = set()
    for fpath in files:
        if fpath in seen or not fpath.is_file():
            continue
        seen.add(fpath)
        for raw in fpath.read_text(encoding="utf-8").splitlines():
            line = clean(raw)
            if not line.startswith("map "):
                continue
            rest = line[4:].strip()
            if not rest:
                continue
            if rest.startswith('"'):
                end = rest.find('"', 1)
                if end < 0:
                    continue
                src = rest[1:end]
                dst = rest[end + 1 :].strip()
            else:
                parts = rest.split()
                if len(parts) >= 2 and not parts[-1].isascii():
                    src = " ".join(parts[:-1])
                    dst = parts[-1]
                else:
                    src = parts[0]
                    dst = parts[1] if len(parts) > 1 else ""
            if not _user_dict_src_allowed(src):
                continue
            pairs.append((src, dst))
    pairs.sort(key=lambda item: len(item[0]), reverse=True)
    return pairs


def load_user_dict(path: Path | None = None) -> list[tuple[str, str]]:
    path_key = str(Path(path)) if path is not None else None
    return _load_user_dict_cached(path_key, str(get_user_dir()))


def clear_user_dict_cache() -> None:
    _load_user_dict_cached.cache_clear()


# Back-compat for call sites using load_user_dict.cache_clear()
load_user_dict.cache_clear = clear_user_dict_cache  # type: ignore[attr-defined]


def apply_user_dict(text: str, mapping: list[tuple[str, str]] | None = None) -> str:
    """Lookup replace (case-insensitive Latin spans + exact source replace)."""
    mapping = mapping if mapping is not None else load_user_dict()
    # Opt 1 defense-in-depth: filter skeleton words even if mapping is passed in
    mapping = [(src, dst) for src, dst in mapping if _user_dict_src_allowed(src)]
    if not mapping:
        return text
    # Multi-word English phrases before single-word replace (thank you, etc.)
    for src, dst in mapping:
        if src.isascii() and " " in src:
            text = re.sub(re.escape(src), dst, text, flags=re.IGNORECASE)
    # latin tokens (check, yyds, thx…)
    lower_map = {src.casefold(): dst for src, dst in mapping if src.isascii() and " " not in src}

    def latin_sub(match: re.Match[str]) -> str:
        key = match.group(0).casefold()
        if key in lower_map:
            return lower_map[key]
        return match.group(0)

    text = re.sub(r"[A-Za-z][A-Za-z0-9]*", latin_sub, text)
    # Chinese: longest source first; if dst already sits here, do not expand again
    # (map 试用→试用期 must not turn 试用期 into 试用期期).
    zh = [(src, dst) for src, dst in mapping if not src.isascii()]
    zh.sort(key=lambda p: len(p[0]), reverse=True)
    for src, dst in zh:
        text = _replace_zh_map(text, src, dst)
    return text


def _replace_zh_map(text: str, src: str, dst: str) -> str:
    if not src or src == dst or src not in text:
        return text
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith(src, i):
            if dst and text.startswith(dst, i):
                out.append(dst)
                i += len(dst)
            else:
                out.append(dst)
                i += len(src)
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def apply_f_order(text: str) -> str:
    """F41–F50 dialect word-order/morphology rewrite (algorithm; vocab from system.tm)."""
    sys = load_system()
    # Sentence-final punctuation: some rules anchor end-of-string; allow optional trailing punct
    _end = r"(?P<end>[。.!！？?]?)(?=\s*$)"

    _v1 = sys.f_verb_chars
    _v_multi = sys.f_verb_multi
    _v_alt = "|".join(re.escape(v) for v in _v_multi) + "|" + "|".join(_v1)
    _adj = sys.f_adj_chars

    # F48 before F41: "go OBJ first" → "first go OBJ"
    text = re.sub(rf"去(.+?)先{_end}", r"先去\1\g<end>", text)
    text = re.sub(r"去(.+?)先", r"先去\1", text)

    # F41: "V first" → "first V"; multi-char first; left neighbor not a verb char (avoid false splits)
    for vo in _v_multi:
        text = re.sub(rf"{re.escape(vo)}先", f"先{vo}", text)
    if _v1:
        text = re.sub(rf"(?<![{_v1}])([{_v1}])先", r"先\1", text)

    # F42: "have + V" → experiential "once V-ed" (keep dialect surfaces; later steps/dict normalize)
    if _v_alt.strip("|"):
        text = re.sub(rf"有({_v_alt})", r"曾\1过", text)

    # F43: "give COMPLEMENT me" (sentence-final, optional punct) → "give me COMPLEMENT"
    text = re.sub(rf"给(.+?)我{_end}", r"给我\1\g<end>", text)

    # F44: "X ADJ guo Y" → "X bi Y ADJ"; trailing intensifiers stay after adj
    def _f44(m: re.Match[str]) -> str:
        left, adj, right = m.group(1), m.group(2), m.group(3)
        tail = ""
        for t in sorted(sys.f_tail_many, key=len, reverse=True):
            if right.endswith(t):
                right, tail = right[: -len(t)], t
                break
        return f"{left}比{right}{adj}{tail}"

    if _adj:
        text = re.sub(
            rf"([\u4e00-\u9fff]{{1,6}})([{_adj}])过([\u4e00-\u9fff]{{1,8}})",
            _f44,
            text,
        )

    # F45: dialect perfective
    for dialect, std in sys.f_complete:
        text = text.replace(dialect, std)

    # F46: fused A-not-A → split form
    for dialect, std in sys.f_polar:
        text = text.replace(dialect, std)

    # F47: progressive prefixes (fixed strings, then map, then single-char verbs)
    for src, dst in sys.f_prog_fixed:
        text = text.replace(src, dst)
    for src, dst in sorted(sys.f_prog_map, key=lambda p: len(p[0]), reverse=True):
        text = text.replace(src, dst)
    if _v1:
        text = re.sub(rf"紧([{_v1}])", r"正在\1", text)

    # F49: {noun}+source suffix → source question form
    suf = re.escape(sys.f_source_suffix)
    text = re.sub(
        rf"([\u4e00-\u9fff]{{1,8}}){suf}{_end}",
        rf"\1{sys.f_source_rewrite}\g<end>",
        text,
    )

    # F50: dialect "tell … me know" → standard "tell me …"
    text = re.sub(sys.f_tell_pattern, sys.f_tell_to + r"\1", text)
    text = text.replace(sys.f_tell_empty, sys.f_tell_to)

    return text


def apply_g(text: str, *, today: date | None = None) -> str:
    """G1–G10 entity normalization (hard-coded)."""
    today = today or date.today()
    defaults = load_entity_defaults()

    def mul(match: re.Match[str], factor: int) -> str:
        return str(int(match.group(1)) * factor)

    text = re.sub(r"(\d+)\s*[wW万]", lambda m: mul(m, 10_000), text)
    text = re.sub(r"(\d+)\s*[kK千]", lambda m: mul(m, 1_000), text)
    text = re.sub(r"(\d+)\s*[mM]", lambda m: mul(m, 1_000_000), text)
    text = re.sub(r"(\d+)\s*百万", lambda m: mul(m, 1_000_000), text)
    # G1–G3: Chinese digit × wan / qian / million
    _cn1 = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    text = re.sub(
        r"([一二两三四五六七八九])\s*万",
        lambda m: str(_cn1[m.group(1)] * 10_000),
        text,
    )
    text = re.sub(r"十\s*万", "100000", text)
    text = re.sub(
        r"([一二两三四五六七八九])\s*千",
        lambda m: str(_cn1[m.group(1)] * 1_000),
        text,
    )
    text = re.sub(
        r"([一二两三四五六七八九])\s*百万",
        lambda m: str(_cn1[m.group(1)] * 1_000_000),
        text,
    )

    weekday_map = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}

    def next_weekday(m: re.Match[str]) -> str:
        target = weekday_map[m.group(1)]
        delta = (target - today.weekday() + 7) % 7
        if delta == 0:
            delta = 7
        return (today + timedelta(days=delta)).isoformat()

    text = re.sub(r"下周([一二三四五六日天])", next_weekday, text)

    def last_weekday(m: re.Match[str]) -> str:
        target = weekday_map[m.group(1)]
        delta = (today.weekday() - target) % 7
        if delta == 0:
            delta = 7
        return (today - timedelta(days=delta)).isoformat()

    def this_weekday(m: re.Match[str]) -> str:
        target = weekday_map[m.group(1)]
        delta = target - today.weekday()
        return (today + timedelta(days=delta)).isoformat()

    text = re.sub(r"上周([一二三四五六日天])", last_weekday, text)
    text = re.sub(r"这周([一二三四五六日天])", this_weekday, text)
    text = re.sub(r"本周([一二三四五六日天])", this_weekday, text)

    # Relative days: longest match first (avoid splitting longer compounds)
    for word, off in sorted(load_system().rel_days, key=lambda x: len(x[0]), reverse=True):
        if word in text:
            text = text.replace(word, (today + timedelta(days=off)).isoformat())

    for fuzzy, val in defaults.items():
        if fuzzy == "三五":
            text = re.sub(r"三五个?", val, text)
        else:
            text = text.replace(fuzzy, val)

    return text


def apply_i(text: str) -> PrepResult:
    """I1–I3 / I7–I8 / I10–I11. Closed sets from system.tm; I4–I6/I9 via user_dict."""
    sys = load_system()
    notes: list[str] = []
    emphasis = ""
    raw = text.strip()
    low = raw.casefold()

    if low in sys.i_thanks or raw in sys.i_thanks:
        return PrepResult(text=raw, intercept="不客气", intercept_rule="I1", notes=["I1"])

    if low in sys.i_greet or raw in sys.i_greet:
        return PrepResult(
            text="你好",
            intercept="你好！",
            intercept_rule="I2",
            greet=True,
            notes=["I2"],
        )

    if low in sys.i_bye or raw in sys.i_bye:
        return PrepResult(
            text=raw,
            intercept="再见！",
            intercept_rule="I3",
            farewell=True,
            mood="farewell",
            notes=["I3"],
        )

    # I11: after I1–I3, before D; skip if interrogative words present
    if _i11_poetry(raw):
        return PrepResult(
            text=raw,
            intercept=sys.i11_msg,
            intercept_rule="I11",
            notes=["I11"],
        )

    if raw in sys.i_ack:
        spoken = "我知道了" if raw in {"哦", "嗯"} else "可以"
        return PrepResult(
            text=raw,
            intercept=spoken,
            intercept_rule="I10",
            notes=["I10"],
        )

    if re.search(r"!{2,}", text) or "！！" in text:
        text = re.sub(r"!{2,}", "!", text)
        text = re.sub(r"！{2,}", "！", text)
        emphasis = "高"
        notes.append("I7")
    if re.search(r"\?{2,}", text) or "？？" in text:
        text = re.sub(r"\?{2,}", "?", text)
        text = re.sub(r"？{2,}", "？", text)
        notes.append("I8")

    return PrepResult(text=text.strip(), emphasis=emphasis, notes=notes)


def _i11_poetry(text: str) -> bool:
    """Pure verse/classical: 5/7-char lines, or classical particles without modern words; not if interrogative."""
    sys = load_system()
    raw = text.strip()
    if not raw:
        return False
    if any(q in raw for q in sys.i11_ask):
        return False
    body = re.sub(r"[\s，。！？、；：,.!?;:\"'“”‘’《》【】（）()]+", "", raw)
    if not body or not re.fullmatch(r"[\u4e00-\u9fff]+", body):
        return False
    modern = any(m in raw for m in sys.i11_modern)
    factual = _is_factual_copula_line(raw)
    # Classical particles (之乎者也…) — skip factual copula like「张三是劳动者」(dict → 员工)
    if any(p in raw for p in sys.i11_classical) and not modern and not factual:
        return True
    if _is_wuyan_qiyan(raw) and not modern and not factual:
        return True
    return False


def _is_factual_copula_line(text: str) -> bool:
    """Single-clause factual "X is Y" (both sides >=2 chars); distinguish from classical verse copulas."""
    parts = re.split(r"[，。！？；、,.!?;:\s]+", text.strip())
    clauses = [re.sub(r"[^\u4e00-\u9fff]", "", p) for p in parts if p.strip()]
    if len(clauses) != 1:
        return False
    clause = clauses[0]
    if "是" not in clause:
        return False
    left, right = clause.split("是", 1)
    return len(left) >= 2 and len(right) >= 2 and "是" not in right


def _is_wuyan_qiyan(text: str) -> bool:
    """After splitting, each clause (punct stripped) is 5 or 7 CJK chars."""
    parts = re.split(r"[，。！？；、,.!?;:\s]+", text.strip())
    clauses = [re.sub(r"[^\u4e00-\u9fff]", "", p) for p in parts if p.strip()]
    if not clauses:
        return False
    return all(len(c) in {5, 7} for c in clauses)


def apply_doc_query(text: str) -> str:
    """Normalize line-address questions to D67: …的内容是什么.

    Only physical-line forms (第N行 / 文档第N行). Other structure (条/章/…)
    must come from Para rules or user D66 teaching — not importer heuristics.
    """
    s = text.strip()
    s = re.sub(
        r"(第\d+行)(?:的内容)?(?:有什么|是什么|什么内容|什么)?\s*[？?]?\s*$",
        r"\1的内容是什么",
        s,
    )
    s = re.sub(
        r"([\u4e00-\u9fff]{2,30})(第\d+行)(?:的内容)?(?:有什么|是什么|什么内容|什么)?\s*[？?]?\s*$",
        r"\1\2的内容是什么",
        s,
    )
    return s


def preprocess(
    text: str,
    *,
    vocab: set[str],
    known: set[str],
    today: date | None = None,
) -> PrepResult:
    """E → user_dict → F41–50 → G → I. D66 body is clipped before E and kept verbatim."""
    stripped = apply_doc_query(text.strip())
    d66 = D66_CONTENT_RE.match(stripped)
    if d66:
        entity = d66.group(1).strip()
        content = clip_d66_content(d66.group(2))  # no tokenize; clip following questions
        entity = repair(entity, vocab, known)
        entity = apply_user_dict(entity)
        entity = apply_f_order(entity)
        entity = apply_g(entity, today=today)
        return apply_i(f"{entity}的内容是{content}")

    text = repair(stripped, vocab, known)
    text = apply_user_dict(text)
    text = apply_f_order(text)
    text = apply_g(text, today=today)
    text = apply_doc_query(text)
    return apply_i(text)
