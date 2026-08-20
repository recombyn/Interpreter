"""User-layer document import: plain text → D66 memory .tm + sharded content store.

Any .text/.txt/.md under knowledge/user/ becomes line-addressable:
  of(content, 第N行, …) / of(content, {stem}第N行, …) in .tm (hot path)
  plus knowledge/user/.content shards (D67 scale path)

No format-specific parsers (articles, 以下称, …).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cni.decode import effects as fx
from cni.kernel.machine import boot, save_world
from cni.knowledge.content_store import ContentStore, default_content_root
from cni.paths import USER_DIR

TEXT_SUFFIXES = (".text", ".txt", ".md", ".mk", ".markdown")

_SKIP_TM = frozenset(
    {
        "user_dict.tm",
        "config.tm",
        "entity_defaults.tm",
        "form.tm",
        "rules.tm",
    }
)
_SKIP_DIRS = frozenset({".content", ".pytest_cache", "__pycache__", ".git"})


def _under_skipped_dir(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    return any(p in _SKIP_DIRS for p in parts[:-1])


@dataclass
class DocLine:
    no: int  # 1-based physical line number in source file
    text: str


@dataclass
class ParsedDoc:
    stem: str
    lines: list[DocLine] = field(default_factory=list)


def is_user_text(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in TEXT_SUFFIXES


def list_user_texts(user_dir: Path | None = None) -> list[Path]:
    """User docs under knowledge/user/ including domain subfolders (e.g. 劳动法/)."""
    root = user_dir or USER_DIR
    if not root.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not is_user_text(path):
            continue
        if _under_skipped_dir(path, root):
            continue
        out.append(path)
    return out


def parse_user_text(path: Path) -> ParsedDoc:
    """Read a user text file as ordered physical lines (no domain structure)."""
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    lines = [DocLine(no=i, text=raw.rstrip("\n")) for i, raw in enumerate(raw_lines, start=1)]
    return ParsedDoc(stem=path.stem, lines=lines)


def _content_body(text: str) -> str:
    """Line text as a D66 content const (no spaces; TM-safe)."""
    text = (text or "").strip() or "（空行）"
    text = text.lstrip("#").strip() or "（空行）"
    text = "".join(ch for ch in text if not ch.isspace())
    text = text.replace("#", "＃").replace(":", "：").replace("*", "")
    return text or "（空行）"


def render_memory_tm(
    doc: ParsedDoc,
    *,
    source: Path | None = None,
    store: ContentStore | None = None,
) -> str:
    """D66 write_content per line → .tm; mirror bodies into sharded ContentStore."""
    machine = boot()
    stem = doc.stem
    fx.ensure(machine, stem)
    if store is not None:
        store.clear_doc(stem)
    for line in doc.lines:
        body = _content_body(line.text)
        e1 = f"第{line.no}行"
        e2 = f"{stem}第{line.no}行"
        fx.write_content(machine, e1, body)
        fx.write_content(machine, e2, body)
        if store is not None:
            store.put(e1, body, doc=stem)
            store.put(e2, body, doc=stem)
    if store is not None:
        store.flush()

    try:
        from cni.preprocess import load_user_dict

        for src, dst in load_user_dict():
            for t in (src, dst):
                if 2 <= len(t) <= 16 and any("\u4e00" <= c <= "\u9fff" for c in t):
                    fx.ensure(machine, t)
    except Exception:
        pass

    dest = tm_path_for(source) if source is not None else None
    out_path = dest or (USER_DIR / f"{stem}.tm")
    save_world(machine, out_path)
    header = (
        f"# Auto-generated from user text via D66 (of content) — do not edit by hand\n"
        f"# source: {source.name if source else stem}\n"
        f"# lines: {len(doc.lines)}\n"
        f"# content-store: sharded under .content/ (D67)\n"
    )
    body = out_path.read_text(encoding="utf-8")
    if body.startswith("# remembered world"):
        body = body.replace("# remembered world", header.rstrip(), 1)
    else:
        body = header + body
    return body


def tm_path_for(text_path: Path) -> Path:
    return text_path.with_suffix(".tm")


def _store_ready(user_dir: Path) -> bool:
    shards = default_content_root(user_dir) / "shards"
    return shards.is_dir() and any(shards.glob("*.json"))


def sync_user_text(path: Path, *, force: bool = False, user_dir: Path | None = None) -> Path | None:
    """Parse one user text file and write sibling .tm + content store if stale/missing."""
    if not is_user_text(path):
        return None
    root = user_dir or path.parent
    dest = tm_path_for(path)
    if (
        not force
        and dest.is_file()
        and dest.stat().st_mtime >= path.stat().st_mtime
        and _store_ready(root)
    ):
        return dest
    doc = parse_user_text(path)
    store = ContentStore(default_content_root(root))
    dest.write_text(render_memory_tm(doc, source=path, store=store), encoding="utf-8")
    return dest


def sync_user_docs(user_dir: Path | None = None, *, force: bool = False) -> list[Path]:
    """Convert all user text/md files under knowledge/user/ to .tm + content store."""
    root = user_dir or USER_DIR
    written: list[Path] = []
    for path in list_user_texts(root):
        got = sync_user_text(path, force=force, user_dir=root)
        if got is not None:
            written.append(got)
    return written


def list_user_memory_tms(user_dir: Path | None = None) -> list[Path]:
    """Memory .tm files under user dir (root + domain subfolders)."""
    root = user_dir or USER_DIR
    if not root.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(root.rglob("*.tm")):
        if _under_skipped_dir(path, root):
            continue
        if path.name in _SKIP_TM:
            continue
        try:
            sample = path.read_text(encoding="utf-8")[:4000]
        except OSError:
            continue
        if any(line.lstrip().startswith(("!", "+")) for line in sample.splitlines()):
            out.append(path)
    return out


def load_user_memories(machine, user_dir: Path | None = None) -> list[Path]:
    """Sync texts, attach ContentStore, load user memory .tm into the machine world."""
    from cni.kernel.machine import load_msgs

    root = user_dir or USER_DIR
    sync_user_docs(root)
    store = ContentStore(default_content_root(root))
    machine.content_store = store
    loaded: list[Path] = []
    for path in list_user_memory_tms(root):
        load_msgs(machine, path)
        loaded.append(path)
    return loaded
