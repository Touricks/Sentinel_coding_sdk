# ---
# input: progress.yaml, progress-archive.yaml paths
# output: archived entries count
# pos: .sentinel/writeback/compact_progress.py
# last_modified: 2026-03-06
# ---

"""Archive absorbed progress.yaml entries to progress-archive.yaml."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import yaml

from writeback import dump_yaml


def ensure_archive(archive_path: str) -> None:
    """Create progress-archive.yaml if it doesn't exist."""
    p = Path(archive_path)
    if not p.exists():
        data = {
            "schema_version": 1,
            "description": "Absorbed entries from progress.yaml. Audit trail for promoted rules and facts.",
            "entries": [],
        }
        p.write_text(
            dump_yaml(data),
            encoding="utf-8",
        )


def compact(
    progress_path: str,
    archive_path: str,
    max_age_days: int = 30,
) -> int:
    """Move absorbed entries older than max_age_days to archive.

    Operates on raw YAML dicts — no dataclass round-trip needed.
    Returns count of entries moved.
    """
    p = Path(progress_path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))

    if data is None or "entries" not in data:
        return 0

    cutoff = datetime.now() - timedelta(days=max_age_days)

    to_archive: list[dict] = []
    to_keep: list[dict] = []

    for entry in data["entries"]:
        try:
            entry_date = datetime.strptime(str(entry.get("date", "")), "%Y-%m-%d")
        except ValueError:
            to_keep.append(entry)
            continue

        if entry.get("status") == "absorbed" and entry_date < cutoff:
            to_archive.append(entry)
        else:
            to_keep.append(entry)

    if not to_archive:
        return 0

    # Append to archive
    ensure_archive(archive_path)
    archive_data = yaml.safe_load(Path(archive_path).read_text(encoding="utf-8"))
    archive_data["entries"].extend(to_archive)
    Path(archive_path).write_text(
        yaml.dump(archive_data, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    # Rewrite progress.yaml with kept entries
    data["entries"] = to_keep
    p.write_text(
        dump_yaml(data),
        encoding="utf-8",
    )

    return len(to_archive)
