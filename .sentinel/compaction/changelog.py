# ---
# input: list of changed files and applied changes
# output: markdown-formatted changelog string
# pos: .sentinel/compaction/changelog.py
# last_modified: 2026-03-06
# ---

"""Changelog generator for compaction runs.

Produces a markdown-formatted summary of what the compaction engine
processed and what changes were applied.
"""

from __future__ import annotations

from datetime import datetime, timezone


def generate_changelog(
    changed_files: list[str],
    changes_applied: list[str],
    timestamp: str | None = None,
) -> str:
    """Generate a markdown changelog of what compaction did.

    Args:
        changed_files: Source files that were processed (with optional annotation).
        changes_applied: Descriptions of changes that were applied.
        timestamp: ISO-format timestamp; defaults to current UTC time.

    Returns:
        Markdown-formatted changelog string.

    Example output::

        ## Compaction Changelog -- 2026-03-05T10:30:00

        ### Sources Processed
        - docs/design-decision.md (modified)
        - progress.yaml (2 new entries)

        ### Changes Applied
        - ARCHITECTURE.md: updated module structure table
        - compaction/CLAUDE.md: added state.py to manifest

        ### Summary
        Processed 2 sources, applied 2 changes.
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    lines: list[str] = []
    lines.append(f"## Compaction Changelog -- {timestamp}")
    lines.append("")

    lines.append("### Sources Processed")
    if changed_files:
        for f in changed_files:
            lines.append(f"- {f}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("### Changes Applied")
    if changes_applied:
        for c in changes_applied:
            lines.append(f"- {c}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("### Summary")
    lines.append(
        f"Processed {len(changed_files)} source{'s' if len(changed_files) != 1 else ''}, "
        f"applied {len(changes_applied)} change{'s' if len(changes_applied) != 1 else ''}."
    )
    lines.append("")

    return "\n".join(lines)
