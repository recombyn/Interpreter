"""Validate a user-side domain pack (rules.tm ↔ limits.tm).

Read-only check of user knowledge; never writes system world.

Usage:
  python -m para.tools.validate_domain 劳动法
  python -m para.tools.validate_domain --all
  python -m para.tools.validate_domain 考勤 --user-dir path/to/user
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

from para.judge import _parse_rules_file
from para.kernel.tmutil import clean, split_args
from para.paths import USER_DIR

_OF_LINE = re.compile(r"^\+\s*of\((.+)\)\s*$")
_OPS = frozenset({"le", "ge", "eq", "lt", "gt", "in"})


@dataclass
class DomainReport:
    domain: str
    errors: list[str] = field(default_factory=list)
    warns: list[str] = field(default_factory=list)
    rules: int = 0
    tiers: int = 0
    of_facts: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _parse_of_facts(path: Path) -> list[tuple[str, str, str]]:
    """Return (key, topic, value) from + of(...) lines."""
    if not path.is_file():
        return []
    out: list[tuple[str, str, str]] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = clean(raw)
        m = _OF_LINE.match(line)
        if not m:
            continue
        try:
            args = split_args(m.group(1), filename=str(path), line=i)
        except ValueError:
            continue
        if len(args) >= 3:
            out.append((args[0], args[1], args[2]))
    return out


def _scan_malformed_rules(path: Path) -> list[str]:
    """Surface rule/tier lines that look intended but failed to parse."""
    bad: list[str] = []
    if not path.is_file():
        return bad
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = clean(raw)
        if not line:
            continue
        if line.startswith("tier "):
            parts = line.split()
            if len(parts) < 5:
                bad.append(f"{path.name}:{i}: tier needs 4 fields after 'tier'")
            else:
                try:
                    int(parts[2])
                    int(parts[3])
                    int(parts[4])
                except ValueError:
                    bad.append(f"{path.name}:{i}: tier bounds/limit must be ints")
            continue
        if not line.startswith("rule "):
            continue
        parts = line.split(maxsplit=4)
        if len(parts) < 5:
            bad.append(f"{path.name}:{i}: rule needs topic op key triggers")
            continue
        _, _topic, op, key_part, triggers = parts
        op_n = op.casefold()
        if op_n not in _OPS:
            bad.append(f"{path.name}:{i}: unknown op {op!r}")
        key_bits = [k.strip() for k in key_part.split("&") if k.strip()]
        if not key_bits:
            bad.append(f"{path.name}:{i}: empty relation key")
        else:
            key = key_bits[0]
            if op_n == "in" and key not in {"许可", "允许"}:
                bad.append(f"{path.name}:{i}: in-rule key must be 许可 (got {key})")
            elif op_n != "in" and key not in {"上限", "下限"}:
                bad.append(f"{path.name}:{i}: le/ge/eq key must be 上限|下限 (got {key})")
        if not any(t.strip() for t in triggers.split("|")):
            bad.append(f"{path.name}:{i}: empty triggers")
    return bad


def validate_domain_dir(domain_dir: Path) -> DomainReport:
    name = domain_dir.name
    report = DomainReport(domain=name)
    rules_path = domain_dir / "rules.tm"
    limits_path = domain_dir / "limits.tm"

    if not rules_path.is_file():
        report.errors.append(f"missing {rules_path.name}")
        return report
    if not limits_path.is_file():
        report.warns.append(f"missing {limits_path.name} (D69 needs of-facts)")

    report.errors.extend(_scan_malformed_rules(rules_path))
    rules, tiers = _parse_rules_file(rules_path)
    report.rules = len(rules)
    report.tiers = len(tiers)

    if not rules and not tiers:
        report.warns.append("no parsed rule/tier lines (template-only is OK until you author)")

    ofs = _parse_of_facts(limits_path)
    report.of_facts = len(ofs)
    by_kt: set[tuple[str, str]] = {(k, t) for k, t, _ in ofs}
    topics_with_unit = {t for k, t, _ in ofs if k == "单位"}
    topics_with_cite = {t for k, t, _ in ofs if k == "出处"}

    for r in rules:
        if r.op == "in":
            if (r.key, r.topic) not in by_kt:
                report.errors.append(
                    f"rule {r.topic} in {r.key}: no + of({r.key}, {r.topic}, …) in limits.tm"
                )
        else:
            if (r.key, r.topic) not in by_kt:
                if any(t.topic == r.topic for t in tiers):
                    report.warns.append(
                        f"rule {r.topic}: relies on tier only (no absolute of({r.key}, …))"
                    )
                else:
                    report.errors.append(
                        f"rule {r.topic} {r.op} {r.key}: no + of({r.key}, {r.topic}, …) "
                        f"and no tier for topic"
                    )
            if (
                r.topic not in topics_with_unit
                and r.op in {"le", "ge", "eq", "lt", "gt"}
                and not any(t.topic == r.topic for t in tiers)
            ):
                report.warns.append(
                    f"topic {r.topic}: missing + of(单位, {r.topic}, 月|天|年)"
                )
        for also in r.also:
            if (also, r.topic) not in by_kt:
                report.errors.append(
                    f"rule {r.topic} also={also}: no + of({also}, {r.topic}, …)"
                )

    cited_warned: set[str] = set()
    for r in rules:
        if r.topic not in topics_with_cite and r.topic not in cited_warned:
            cited_warned.add(r.topic)
            report.warns.append(f"topic {r.topic}: no + of(出处, …) (cite/evidence weaker)")

    for t in tiers:
        if not any(r.topic == t.topic for r in rules):
            report.warns.append(f"tier {t.topic}: no matching rule line")

    return report


def list_domain_dirs(user_dir: Path) -> list[Path]:
    if not user_dir.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(user_dir.iterdir()):
        if p.is_dir() and (p / "rules.tm").is_file():
            out.append(p)
    # root-level rules.tm stub is not a domain pack
    return out


def validate_user_tree(
    user_dir: Path,
    *,
    domain: str | None = None,
) -> list[DomainReport]:
    if domain:
        d = user_dir / domain
        if not d.is_dir():
            rep = DomainReport(domain=domain)
            rep.errors.append(f"domain dir not found: {d}")
            return [rep]
        return [validate_domain_dir(d)]
    dirs = list_domain_dirs(user_dir)
    if not dirs:
        rep = DomainReport(domain="(none)")
        rep.warns.append(f"no domain packs with rules.tm under {user_dir}")
        return [rep]
    return [validate_domain_dir(d) for d in dirs]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate user-side domain pack")
    parser.add_argument(
        "domain",
        nargs="?",
        default=None,
        help="domain folder name (omit with --all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="validate every domain under user_dir that has rules.tm",
    )
    parser.add_argument(
        "--user-dir",
        type=Path,
        default=None,
        help="knowledge root (default: knowledge/user)",
    )
    args = parser.parse_args(argv)
    root = args.user_dir or USER_DIR
    if not args.all and not args.domain:
        parser.error("pass a domain name or --all")
    reports = validate_user_tree(root, domain=None if args.all else args.domain)

    exit_code = 0
    for rep in reports:
        head = f"[{rep.domain}] rules={rep.rules} tiers={rep.tiers} of={rep.of_facts}"
        print(head)
        for w in rep.warns:
            print(f"  [WARN] {w}")
        for e in rep.errors:
            print(f"  [ERROR] {e}")
            exit_code = 1
        if rep.ok and not rep.warns:
            print("  [OK]")
        elif rep.ok:
            print("  [OK with warns]")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
