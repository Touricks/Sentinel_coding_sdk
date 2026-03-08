# ---
# input: progress.yaml file path
# output: ProgressEntry, Candidate dataclasses; parse/write/query functions
# pos: .sentinel/writeback/progress_format.py
# last_modified: 2026-03-06
# ---

"""progress.yaml parser and writer.

Handles structured session log entries with typed candidates
(rule / fact) for the compaction promotion gate. Uses YAML for
reliable machine parsing instead of regex on markdown.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from writeback import dump_yaml


@dataclass
class Candidate:
    """A typed candidate for promotion to CLAUDE.md or ARCHITECTURE.md."""

    type: str  # "rule" | "fact"
    text: str
    id: str = ""
    scope: str = "global"  # "global" | "module" | "incident-only"
    confidence: str = "med"  # "high" | "med" | "low"
    needs_approval: bool = True
    subsystem: str | None = None  # for fact candidates
    promotion_targets: list[str] = field(default_factory=list)


@dataclass
class ProgressEntry:
    """A single session log entry in progress.yaml."""

    date: str
    title: str
    status: str = "unprocessed"  # "unprocessed" | "absorbed"
    session_report: str = ""
    absorbed_to: str | None = None
    next_steps: list[str] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)


def generate_candidate_id(
    date: str, text: str, existing_ids: set[str] | None = None
) -> str:
    """Generate a stable candidate ID from date and text.

    Format: cand-{date}-{kebab-of-first-5-words}
    Appends -2, -3 etc. on collision with existing_ids.
    """
    words = re.sub(r"[^a-z0-9\s]", "", text.lower()).split()[:5]
    slug = "-".join(words) if words else "unnamed"
    base_id = f"cand-{date}-{slug}"

    if existing_ids is None or base_id not in existing_ids:
        return base_id

    counter = 2
    while f"{base_id}-{counter}" in existing_ids:
        counter += 1
    return f"{base_id}-{counter}"


def _candidate_from_dict(d: dict) -> Candidate:
    """Construct a Candidate from a YAML dict."""
    return Candidate(
        type=d.get("type", "rule"),
        text=d.get("text", ""),
        id=d.get("id", ""),
        scope=d.get("scope", "global"),
        confidence=d.get("confidence", "med"),
        needs_approval=d.get("needs_approval", True),
        subsystem=d.get("subsystem"),
        promotion_targets=d.get("promotion_targets", []),
    )


def _candidate_to_dict(c: Candidate) -> dict:
    """Serialize a Candidate to a plain dict for YAML output."""
    d: dict = {
        "id": c.id,
        "type": c.type,
        "text": c.text,
        "scope": c.scope,
        "confidence": c.confidence,
        "needs_approval": c.needs_approval,
    }
    if c.subsystem:
        d["subsystem"] = c.subsystem
    if c.promotion_targets:
        d["promotion_targets"] = c.promotion_targets
    return d


def parse_progress(path: str) -> list[ProgressEntry]:
    """Parse a progress.yaml file into structured entries."""
    content = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    if data is None or "entries" not in data:
        return []

    version = data.get("schema_version")
    if version != 1:
        raise ValueError(
            f"Unsupported progress.yaml schema_version: {version} (expected 1)"
        )

    entries: list[ProgressEntry] = []
    for raw in data["entries"]:
        candidates = [_candidate_from_dict(c) for c in raw.get("candidates", [])]
        entry = ProgressEntry(
            date=str(raw.get("date", "")),
            title=raw.get("title", ""),
            status=raw.get("status", "unprocessed"),
            session_report=raw.get("session_report", ""),
            absorbed_to=raw.get("absorbed_to"),
            next_steps=raw.get("next_steps", []),
            candidates=candidates,
        )
        entries.append(entry)

    return entries


def format_entry(entry: ProgressEntry) -> dict:
    """Format a ProgressEntry as a plain dict for YAML serialization."""
    d: dict = {
        "date": entry.date,
        "title": entry.title,
        "status": entry.status,
        "session_report": entry.session_report,
    }
    if entry.absorbed_to:
        d["absorbed_to"] = entry.absorbed_to
    if entry.next_steps:
        d["next_steps"] = entry.next_steps
    d["candidates"] = [_candidate_to_dict(c) for c in entry.candidates]
    return d


def add_entry(path: str, entry: ProgressEntry) -> None:
    """Append a new entry to progress.yaml."""
    p = Path(path)
    if p.exists():
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    else:
        data = None

    if data is None:
        data = {"schema_version": 1, "entries": []}

    data["entries"].append(format_entry(entry))
    p.write_text(
        dump_yaml(data),
        encoding="utf-8",
    )


def get_unprocessed(path: str) -> list[ProgressEntry]:
    """Return entries with status == 'unprocessed'."""
    return [e for e in parse_progress(path) if e.status == "unprocessed"]


def mark_absorbed(
    path: str, entry_date: str, entry_title: str, absorbed_to: str
) -> None:
    """Update an entry's status to 'absorbed' and set absorbed_to."""
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))

    if data is None or "entries" not in data:
        return

    for raw in data["entries"]:
        if str(raw.get("date", "")) == entry_date and raw.get("title") == entry_title:
            raw["status"] = "absorbed"
            raw["absorbed_to"] = absorbed_to
            break

    p.write_text(
        dump_yaml(data),
        encoding="utf-8",
    )
