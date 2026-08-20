"""Sharded on-disk content store for D66/D67 scale.

Bodies under knowledge/user/.content, keyed by entity.
D67 does O(1) point lookup (memory ∪ disk). No Chinese lexicon and no
open-search API here — chat content questions go through D67 only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

from cni.paths import USER_DIR


def default_content_root(user_dir: Path | None = None) -> Path:
    return (user_dir or USER_DIR) / ".content"


@dataclass
class ContentStore:
    """Entity → bodies; shards flushed on flush()."""

    root: Path
    shards_dir: Path = field(init=False)
    _shards: dict[str, dict] = field(default_factory=dict, init=False)
    _dirty_shards: set[str] = field(default_factory=set, init=False)
    _loaded_shards: set[str] = field(default_factory=set, init=False)

    def __init__(self, root: Path | None = None) -> None:
        object.__setattr__(self, "root", Path(root) if root else default_content_root())
        object.__setattr__(self, "shards_dir", self.root / "shards")
        object.__setattr__(self, "_shards", {})
        object.__setattr__(self, "_dirty_shards", set())
        object.__setattr__(self, "_loaded_shards", set())

    def ensure_dirs(self) -> None:
        self.shards_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sid(key: str) -> str:
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:2]

    def flush(self) -> None:
        self.ensure_dirs()
        for sid in list(self._dirty_shards):
            path = self.shards_dir / f"{sid}.json"
            path.write_text(
                json.dumps(self._shards.get(sid, {}), ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
        self._dirty_shards.clear()

    def _shard_map(self, entity: str) -> dict:
        sid = self._sid(entity)
        if sid not in self._loaded_shards:
            path = self.shards_dir / f"{sid}.json"
            data: dict = {}
            if path.is_file():
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        data = raw
                except (OSError, json.JSONDecodeError):
                    data = {}
            self._shards[sid] = data
            self._loaded_shards.add(sid)
        return self._shards[sid]

    def get(self, entity: str) -> list[str]:
        entry = self._shard_map(entity).get(entity)
        if not isinstance(entry, dict):
            return []
        bodies = entry.get("bodies") or []
        return [str(b) for b in bodies] if isinstance(bodies, list) else []

    def doc_of(self, entity: str) -> str:
        entry = self._shard_map(entity).get(entity)
        if isinstance(entry, dict):
            return str(entry.get("doc") or "")
        return ""

    def put(self, entity: str, body: str, *, doc: str = "") -> None:
        if not entity or not body:
            return
        sid = self._sid(entity)
        data = self._shard_map(entity)
        entry = data.get(entity)
        if not isinstance(entry, dict):
            entry = {"bodies": [], "doc": doc or ""}
        bodies: list[str] = list(entry.get("bodies") or [])
        if body not in bodies:
            bodies.append(body)
        if doc:
            entry["doc"] = doc
        entry["bodies"] = bodies
        data[entity] = entry
        self._dirty_shards.add(sid)

    def drop(self, entity: str, body: str | None = None) -> None:
        sid = self._sid(entity)
        data = self._shard_map(entity)
        entry = data.get(entity)
        if not isinstance(entry, dict):
            return
        bodies: list[str] = list(entry.get("bodies") or [])
        if body is None:
            data.pop(entity, None)
        else:
            bodies = [b for b in bodies if b != body]
            if bodies:
                entry["bodies"] = bodies
                data[entity] = entry
            else:
                data.pop(entity, None)
        self._dirty_shards.add(sid)

    def clear_doc(self, doc: str) -> None:
        self.ensure_dirs()
        if self.shards_dir.is_dir():
            for path in self.shards_dir.glob("*.json"):
                sid = path.stem
                if sid not in self._loaded_shards:
                    try:
                        raw = json.loads(path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        raw = {}
                    self._shards[sid] = raw if isinstance(raw, dict) else {}
                    self._loaded_shards.add(sid)
        for sid, data in list(self._shards.items()):
            changed = False
            for ent in list(data.keys()):
                entry = data[ent]
                if isinstance(entry, dict) and entry.get("doc") == doc:
                    data.pop(ent, None)
                    changed = True
            if changed:
                self._dirty_shards.add(sid)
