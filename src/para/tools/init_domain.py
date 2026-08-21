"""Scaffold a new user-side domain pack (rules.tm + limits.tm).

Does not touch system world (data/world). Users only add under knowledge/user/.

Usage:
  python -m para.tools.init_domain 我司规章
  python -m para.tools.init_domain 考勤 --user-dir path/to/user
"""

from __future__ import annotations

import argparse
from pathlib import Path

from para.paths import USER_DIR

_RULES = """\
# 判定声明（用户侧）：不进系统世界库，由 D69 读取。
# 格式:
#   rule {主题} {算子} {关系键[&附加键…]} {触发1|触发2|…}
#   tier {主题} {合同月下限含} {合同月上限不含|0=+∞} {档位上限}
# 算子: le / ge / eq / in
# 关系键: 上限 / 下限 / 许可
#
# 示例（请改成你的主题；改完后填 limits.tm，再跑 validate_domain）:
# rule 试用期 le 上限 合法吗|合不合法|合规吗|可以吗
# rule 合同类型 in 许可 合法吗|合规吗|可以吗
# tier 试用期 3 12 1
"""

_LIMITS = """\
# 判定依据（用户侧世界事实）。compile_limits 可半自动生成数值段。
# 格式示例:
# ! 主题 : e
# ! 月 : e
# + of(上限, 主题, 6)
# + of(单位, 主题, 月)
# + of(出处, 主题, 文档第N行)
# + of(许可, 合同类型, 固定期限)
# + of(书面约定, 试用期, 是)
"""

_SAMPLES = """\
# 验收样例问句（手工或评测用；一行一句）
# 主题六个月合法吗
# 合同类型固定期限合法吗
"""

_README = """\
# {name}（用户知识包）

系统规则只读；本目录只放你自己的判定与事实。

| 文件 | 作用 |
| --- | --- |
| `rules.tm` | D69：`rule` / `tier` |
| `limits.tm` | 上限 / 单位 / 许可 / 出处 |
| `samples.txt` | 验收问句 |
| `*.text` | 可选正文 → `sync_user_docs` |

```bash
# 填完 rules + limits 后校验（不改系统）
python -m para.tools.validate_domain {name}

# 对话（加载整个 user_dir，含本领域）
python -m para reply "……合法吗" --user-dir <user根>
```
"""


def scaffold(name: str, user_dir: Path, *, force: bool = False) -> Path:
    name = name.strip().strip("/\\")
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError(f"invalid domain name: {name!r}")
    dest = user_dir / name
    if dest.exists() and not force:
        raise FileExistsError(f"domain already exists: {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    files = {
        "rules.tm": _RULES,
        "limits.tm": _LIMITS,
        "samples.txt": _SAMPLES,
        "README.md": _README.format(name=name),
    }
    for fname, body in files.items():
        path = dest / fname
        if path.exists() and not force:
            continue
        path.write_text(body, encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scaffold user-side domain pack")
    parser.add_argument("name", help="domain folder name under user_dir")
    parser.add_argument(
        "--user-dir",
        type=Path,
        default=None,
        help="knowledge root (default: knowledge/user)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite template files if present",
    )
    args = parser.parse_args(argv)
    root = args.user_dir or USER_DIR
    try:
        dest = scaffold(args.name, root, force=args.force)
    except (ValueError, FileExistsError) as e:
        print(f"[ERROR] {e}")
        return 1
    print(f"[OK] scaffolded {dest}")
    print(
        "  next: edit rules.tm + limits.tm → "
        f"python -m para.tools.validate_domain {args.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
