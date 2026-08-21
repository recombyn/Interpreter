"""Knowledge patch suggestions for hosts (never auto-writes .tm).

Filled into DecodeOutcome.suggestions — separate from spoken / evidence.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from para.api import DecodeOutcome, KnowledgeSuggestion, Status
from para.judge import _LEGAL_TAILS, judge_topics
from para.paths import get_user_dir

_FILLER = re.compile(
    r"^(?:请问(?:一下)?|我想问|麻烦问一下|我们公司|公司|另外|那么|那)?"
)
_TOPIC_HEAD = re.compile(r"^([\u4e00-\u9fffA-Za-z]{2,12})")
_REFUSE_RULES = frozenset({"ren2", "ro3"})


def _guess_legal_topic(text: str) -> tuple[str, str] | None:
    """If ask ends with a legality tail, return (topic_guess, trigger)."""
    raw = (text or "").strip().rstrip("？?")
    trig = next((t for t in _LEGAL_TAILS if raw.endswith(t)), None)
    if trig is None:
        return None
    body = _FILLER.sub("", raw[: -len(trig)]).strip("，, 。 ")
    if not body:
        return None
    for topic in sorted(judge_topics(), key=len, reverse=True):
        if body == topic or body.startswith(topic):
            return topic, trig
    m = _TOPIC_HEAD.match(body)
    return (m.group(1) if m else body[:8], trig)


def _default_rules_relpath(user_dir: Path) -> str:
    if not user_dir.is_dir():
        return "rules.tm"
    for p in sorted(user_dir.iterdir()):
        if p.is_dir() and (p / "rules.tm").is_file():
            return f"{p.name}/rules.tm"
    return "rules.tm"


def _limits_relpath(rules_rel: str) -> str:
    return rules_rel.replace("rules.tm", "limits.tm")


def _is_gap(status: Status, rule_l: str, miss: bool) -> bool:
    return miss or status == "refuse" or rule_l in _REFUSE_RULES


def suggest_knowledge(
    *,
    text: str,
    status: Status,
    rule: str,
    miss: bool,
    user_dir: Path | None = None,
) -> tuple[KnowledgeSuggestion, ...]:
    """Propose user-side .tm patches; empty when in-scope / ask-slot / social."""
    rule_l = (rule or "").casefold()
    if status in {"write", "social"} or rule_l.endswith(".ask"):
        return ()

    root = Path(user_dir) if user_dir is not None else get_user_dir()
    rel_rules = _default_rules_relpath(root)
    rel_limits = _limits_relpath(rel_rules)
    topics = judge_topics()
    legal = _guess_legal_topic(text)

    if legal:
        topic, _trig = legal
        if topic in topics:
            if not _is_gap(status, rule_l, miss):
                return ()
            return (
                KnowledgeSuggestion(
                    kind="add_limit",
                    path=rel_limits,
                    text=(
                        f"+ of(上限, {topic}, <数值>)\n"
                        f"+ of(单位, {topic}, 月)\n"
                        f"+ of(出处, {topic}, <文档第N行>)"
                    ),
                    reason=(
                        f"主题「{topic}」已在 rules.tm，但本问未落到判定"
                        "（缺 limits 或未解析出时长）"
                    ),
                    topic=topic,
                ),
            )
        return (
            KnowledgeSuggestion(
                kind="add_rule",
                path=rel_rules,
                text=f"rule {topic} le 上限 合法吗|合不合法|合规吗|可以吗",
                reason=(
                    f"判定问句未命中已有主题；建议在用户侧新增「{topic}」"
                    "规则（需再配 limits.tm）"
                ),
                topic=topic,
            ),
            KnowledgeSuggestion(
                kind="add_limit",
                path=rel_limits,
                text=(
                    f"! {topic} : e\n"
                    f"! 月 : e\n"
                    f"+ of(上限, {topic}, <数值>)\n"
                    f"+ of(单位, {topic}, 月)"
                ),
                reason=f"新主题「{topic}」需要上限/单位事实，勿无依据填写",
                topic=topic,
            ),
        )

    if _is_gap(status, rule_l, miss):
        return (
            KnowledgeSuggestion(
                kind="need_doc",
                path="",
                text="",
                reason="库外问题：请上传相关正文到 user_dir，或教入事实；系统不会编造答案",
            ),
        )
    return ()


def attach_suggestions(
    outcome: DecodeOutcome,
    *,
    user_dir: Path | None = None,
) -> DecodeOutcome:
    """Fill suggestions on a decode outcome (does not write files)."""
    if outcome.suggestions:
        return outcome
    sug = suggest_knowledge(
        text=outcome.text,
        status=outcome.status,
        rule=outcome.rule,
        miss=outcome.miss,
        user_dir=user_dir,
    )
    return replace(outcome, suggestions=sug) if sug else outcome
