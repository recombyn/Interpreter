"""Dim8: domain isolation via separate user_dir (L4 partial)."""

from __future__ import annotations

from pathlib import Path

import pytest

from para.app import Para
from para.judge import clear_judge_cache, judge_topics
from para.user_config import clear_user_config_cache


def _write_pack(root: Path, name: str, topic: str, limit: int) -> Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "rules.tm").write_text(
        f"rule {topic} le 上限 合法吗|合不合法\n",
        encoding="utf-8",
    )
    (d / "limits.tm").write_text(
        "\n".join(
            [
                f"! {topic} : e",
                f"! {limit} : e",
                "! 月 : e",
                f"+ of(上限, {topic}, {limit})",
                f"+ of(单位, {topic}, 月)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return d


@pytest.mark.L4
def test_separate_user_dir_isolation(tmp_path: Path):
    """Two Para instances with distinct user_dir must not share judge topics."""
    clear_judge_cache()
    clear_user_config_cache()
    a = _write_pack(tmp_path, "域甲", "试用期甲", 6)
    b = _write_pack(tmp_path, "域乙", "试用期乙", 3)

    pa = Para(remember=False, load_user_docs=True, user_dir=a)
    assert "试用期甲" in judge_topics()
    oa = pa.decode("试用期甲六个月合法吗", write=False)

    clear_judge_cache()
    clear_user_config_cache()
    pb = Para(remember=False, load_user_docs=True, user_dir=b)
    topics_b = judge_topics()
    assert "试用期乙" in topics_b
    assert "试用期甲" not in topics_b
    ob = pb.decode("试用期乙三个月合法吗", write=False)
    cross = pb.decode("试用期甲六个月合法吗", write=False)

    assert oa.rule in {"D69", "D69.ask"}
    assert "合法" in (oa.spoken or "") or "请问" in (oa.spoken or "")

    assert ob.rule in {"D69", "D69.ask"}
    assert cross.rule == "REN2" or (
        "不知道" in (cross.spoken or "")
    ) or cross.rule not in {"D69"}

    clear_judge_cache()
    clear_user_config_cache()
