# ---
# input: file paths on disk
# output: .compaction-state.json (SHA-256 + mtime tracking)
# pos: .sentinel/compaction/state.py
# last_modified: 2026-03-06
# ---

"""CompactionState manager.

Tracks SHA-256 hashes and modification times for files in the write layer,
enabling incremental compaction by detecting which files have changed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class FileState:
    """Recorded state of a single tracked file."""

    path: str
    sha256: str
    mtime: float


class CompactionState:
    """Manages .compaction-state.json for incremental change detection."""

    def __init__(self, state_path: str = ".compaction-state.json") -> None:
        self.state_path = Path(state_path)

    def load(self) -> dict[str, FileState]:
        """Load state from JSON file. Returns empty dict if file doesn't exist."""
        if not self.state_path.exists():
            return {}

        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        result: dict[str, FileState] = {}
        for key, val in raw.items():
            result[key] = FileState(
                path=val["path"],
                sha256=val["sha256"],
                mtime=val["mtime"],
            )
        return result

    def save(self, states: dict[str, FileState]) -> None:
        """Save state to JSON file."""
        raw: dict[str, dict] = {}
        for key, fs in states.items():
            raw[key] = asdict(fs)

        self.state_path.write_text(
            json.dumps(raw, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def changed_since_last(self, paths: list[str]) -> list[str]:
        """Return paths whose SHA-256 hash has changed since last save."""
        previous = self.load()
        changed: list[str] = []

        for p in paths:
            current_hash = self._compute_hash(p)
            prev_state = previous.get(p)

            if prev_state is None or prev_state.sha256 != current_hash:
                changed.append(p)

        return changed

    def update(self, path: str) -> None:
        """Update state for a single file (compute hash, record mtime)."""
        p = Path(path)
        if not p.exists():
            return

        states = self.load()
        states[path] = FileState(
            path=path,
            sha256=self._compute_hash(path),
            mtime=p.stat().st_mtime,
        )
        self.save(states)

    @staticmethod
    def _compute_hash(path: str) -> str:
        """Compute SHA-256 hash of file content."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
