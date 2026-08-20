"""Preprocess: E → user_dict → F41–50 → G → I(硬编码).

表1写死：E / F41–50 / G / I1–3 / I7–8 / I10–I11
表2查表：F1–40 / H / I4–6 / I9 → knowledge/user/user_dict.tm
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
import re

from cni.kernel.tmutil import clean
from cni.paths import USER_DIR
from cni.repair import repair

DEFAULTS_PATH = USER_DIR / "entity_defaults.tm"
USER_DICT_PATH = USER_DIR / "user_dict.tm"

_I_THANKS = {"谢谢", "thanks", "thx", "thank you"}
_I_GREET = {"你好", "hi", "hello", "您好"}
_I_BYE = {"再见", "bye", "拜拜"}
_I_ACK = {"哦", "嗯", "行"}
_I11_MSG = "我擅长处理事实性问题，不懂诗词赏析。"
_I11_ASK = ("谁", "什么", "吗", "哪儿", "哪里", "怎么", "为什么", "多少", "几个")
_I11_CLASSICAL = ("之", "乎", "者", "也", "矣", "焉", "哉")
# 现代痕迹：有则不作五七言/古汉语拦截（「是」单独放行，以免误伤「疑是地上霜」）
_I11_MODERN = (
    "有",
    "在",
    "把",
    "被",
    "的",
    "了",
    "着",
    "过",
    "呢",
    "吧",
    "啊",
    "不",
    "没",
    "能",
    "会",
    "要",
    "吃",
    "喝",
    "看",
    "去",
    "来",
    "走",
    "到",
    "对",
    "给",
    "帮",
    "让",
    "做",
    "说",
    "讲",
    "介绍",
    "我",
    "你",
    "他",
    "她",
    "们",
    "这",
    "那",
    "发明",
    "电脑",
    "机器",
    "内容",
    "因为",
    "所以",
    "但是",
    "如果",
    "正在",
    "知道",
    "喜欢",
)
_D66_CONTENT = re.compile(r"^(.+?)\s*的内容是\s*(.+)$")


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
    """G7–G10 系统默认（表1）；可选文件仅作同键覆盖，不新增表2词条逻辑。"""
    path = path or DEFAULTS_PATH
    out: dict[str, str] = {
        "几十": "30",
        "大半": "70%",
        "一小会儿": "5分钟",
        "三五": "3-5",
    }
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = clean(raw)
        if not line.startswith("default"):
            continue
        parts = line.split(maxsplit=2)
        if len(parts) == 3 and parts[1] in out:
            out[parts[1]] = parts[2]
    return out


@lru_cache(maxsize=1)
def load_user_dict(path: Path | None = None) -> list[tuple[str, str]]:
    """表2：用户维护的 原文→标准词。返回按原文长度降序，便于最长匹配。"""
    path = path or USER_DICT_PATH
    pairs: list[tuple[str, str]] = []
    if not path.is_file():
        return pairs
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = clean(raw)
        if not line.startswith("map "):
            continue
        rest = line[4:].strip()
        if not rest:
            continue
        parts = rest.split(None, 1)
        src = parts[0]
        dst = parts[1] if len(parts) > 1 else ""
        pairs.append((src, dst))
    pairs.sort(key=lambda item: len(item[0]), reverse=True)
    return pairs


def apply_user_dict(text: str, mapping: list[tuple[str, str]] | None = None) -> str:
    """查表替换（大小写不敏感的拉丁段 + 原文精确替换）。"""
    mapping = mapping if mapping is not None else load_user_dict()
    if not mapping:
        return text
    # latin tokens (check, yyds, thx…)
    lower_map = {src.casefold(): dst for src, dst in mapping if src.isascii()}

    def latin_sub(match: re.Match[str]) -> str:
        key = match.group(0).casefold()
        if key in lower_map:
            return lower_map[key]
        return match.group(0)

    text = re.sub(r"[A-Za-z][A-Za-z0-9]*", latin_sub, text)
    for src, dst in mapping:
        if src.isascii():
            continue
        text = text.replace(src, dst)
    return text


def apply_f_order(text: str) -> str:
    """F41–F50 方言语序/形态重排（算法，非查表）。"""
    # F41 / F48: …V先 / 去X先 → 先…
    text = re.sub(r"([去来吃看做喝说走读写听玩])先", r"先\1", text)
    text = re.sub(r"去(.+?)先", r"先去\1", text)

    # F42: 有+V → 曾V过
    text = re.sub(r"有(吃|看|做|去|来|喝|说|走|读|写|听|玩)", r"曾\1过", text)

    # F43: 给…我$ → 给我…
    text = re.sub(r"给(.+?)我$", r"给我\1", text)

    # F44: X形过Y → X比Y形
    text = re.sub(
        r"([\u4e00-\u9fff]{1,6})([高矮大小好坏强弱快慢长短新旧])过([\u4e00-\u9fff]{1,6})",
        r"\1比\3\2",
        text,
    )

    # F45 / F46
    text = text.replace("咗", "了")
    text = text.replace("有冇", "有没有")

    # F47: 进行体标记归一
    text = re.sub(r"紧食饭", "正在吃饭", text)
    text = re.sub(r"紧(食|吃|看|做|去|说|走|读|写)", r"正在\1", text)

    # F49 / F50
    text = re.sub(r"([\u4e00-\u9fff]{1,8})来的$", r"\1是从那里来", text)
    text = re.sub(r"讲(.+?)我知", r"告诉我\1", text)

    return text


# 兼容旧测试名
def apply_f(text: str) -> str:
    return apply_f_order(text)


def apply_g(text: str, *, today: date | None = None) -> str:
    """G1–G10 实体归一化（写死）。"""
    today = today or date.today()
    defaults = load_entity_defaults()

    def mul(match: re.Match[str], factor: int) -> str:
        return str(int(match.group(1)) * factor)

    text = re.sub(r"(\d+)\s*[wW万]", lambda m: mul(m, 10_000), text)
    text = re.sub(r"(\d+)\s*[kK千]", lambda m: mul(m, 1_000), text)
    text = re.sub(r"(\d+)\s*[mM]", lambda m: mul(m, 1_000_000), text)
    text = re.sub(r"(\d+)\s*百万", lambda m: mul(m, 1_000_000), text)
    # G1–G3：中文个位数字 × 万/千/百万
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

    for word, off in {
        "昨天": -1,
        "前天": -2,
        "明天": 1,
        "后天": 2,
        "今天": 0,
    }.items():
        if word in text:
            text = text.replace(word, (today + timedelta(days=off)).isoformat())

    for fuzzy, val in defaults.items():
        if fuzzy == "三五":
            text = re.sub(r"三五个?", val, text)
        else:
            text = text.replace(fuzzy, val)

    return text


def apply_i(text: str) -> PrepResult:
    """I1–I3 / I7–I8 / I10–I11（写死）。I4–I6/I9 已迁 user_dict。"""
    notes: list[str] = []
    emphasis = ""
    raw = text.strip()
    low = raw.casefold()

    if low in _I_THANKS or raw in _I_THANKS:
        return PrepResult(text=raw, intercept="不客气", intercept_rule="I1", notes=["I1"])

    if low in _I_GREET or raw in _I_GREET:
        return PrepResult(
            text="你好",
            intercept="你好！",
            intercept_rule="I2",
            greet=True,
            notes=["I2"],
        )

    if low in _I_BYE or raw in _I_BYE:
        return PrepResult(
            text=raw,
            intercept="再见！",
            intercept_rule="I3",
            farewell=True,
            mood="farewell",
            notes=["I3"],
        )

    # I11：在 I1–I3 之后、D 之前；含疑问词则不触发
    if _i11_poetry(raw):
        return PrepResult(
            text=raw,
            intercept=_I11_MSG,
            intercept_rule="I11",
            notes=["I11"],
        )

    if raw in _I_ACK:
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
    """纯诗句/古汉语：五七言，或含之乎者也且无现代词；有疑问词则否。"""
    raw = text.strip()
    if not raw:
        return False
    if any(q in raw for q in _I11_ASK):
        return False
    body = re.sub(r"[\s，。！？、；：,.!?;:\"'“”‘’《》【】（）()]+", "", raw)
    if not body or not re.fullmatch(r"[\u4e00-\u9fff]+", body):
        return False
    modern = any(m in raw for m in _I11_MODERN)
    if any(p in raw for p in _I11_CLASSICAL) and not modern:
        return True
    if _is_wuyan_qiyan(raw) and not modern and not _is_factual_copula_line(raw):
        return True
    return False


def _is_factual_copula_line(text: str) -> bool:
    """单句「双字+是+双字」类事实（苹果是水果），与「疑是地上霜」区分。"""
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
    """分句后每句（去标点）为 5 或 7 汉字。"""
    parts = re.split(r"[，。！？；、,.!?;:\s]+", text.strip())
    clauses = [re.sub(r"[^\u4e00-\u9fff]", "", p) for p in parts if p.strip()]
    if not clauses:
        return False
    return all(len(c) in {5, 7} for c in clauses)


def preprocess(
    text: str,
    *,
    vocab: set[str],
    known: set[str],
    today: date | None = None,
) -> PrepResult:
    """E → user_dict → F41–50 → G → I。D66 正文在 E 之前截出，原样保留。"""
    stripped = text.strip()
    d66 = _D66_CONTENT.match(stripped)
    if d66:
        entity = d66.group(1).strip()
        content = d66.group(2)  # 不分词、不经 E/G
        entity = repair(entity, vocab, known)
        entity = apply_user_dict(entity)
        entity = apply_f_order(entity)
        entity = apply_g(entity, today=today)
        return apply_i(f"{entity}的内容是{content}")

    text = repair(text, vocab, known)
    text = apply_user_dict(text)
    text = apply_f_order(text)
    text = apply_g(text, today=today)
    return apply_i(text)


# 旧名：H 已删，保留 stub 以免外部误用时无属性
def apply_h(text: str) -> str:
    """已删除内置 H；走 user_dict。"""
    return apply_user_dict(text)
