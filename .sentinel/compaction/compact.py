# ---
# input: project root path, mode, write-layer dirs, progress.yaml path
# output: CompactionResult with changelog, updates, and promotion decisions; JSON via CLI
# pos: .sentinel/compaction/compact.py
# last_modified: 2026-03-06
# ---

"""Main compaction entry point.

Orchestrates incremental compaction: detects changed write-layer files,
processes unabsorbed progress.yaml candidates through the promotion gate,
and produces a structured result for downstream consumers.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    from .state import CompactionState
    from .changelog import generate_changelog
except ImportError:
    from compaction.state import CompactionState  # type: ignore[no-redef]
    from compaction.changelog import generate_changelog  # type: ignore[no-redef]

# Import Candidate from writeback (use try/except for when writeback isn't available)
try:
    from writeback.progress_format import (
        Candidate,
        ProgressEntry,
        get_unprocessed,
        mark_absorbed,
    )
except ImportError:
    Candidate = None  # type: ignore[assignment,misc]
    ProgressEntry = None  # type: ignore[assignment,misc]
    get_unprocessed = None  # type: ignore[assignment]
    mark_absorbed = None  # type: ignore[assignment]


@dataclass
class CompactionResult:
    """Structured output of a compaction run."""

    changelog: str
    architecture_updates: list[str] = field(default_factory=list)
    dir_manifest_updates: dict[str, str] = field(default_factory=dict)
    root_suggestions: list[str] = field(default_factory=list)  # proposed, not auto-applied
    promoted_rules: list = field(default_factory=list)  # Candidate objects from progress.yaml
    promoted_facts: list = field(default_factory=list)
    reviewed_entries: list[dict] = field(default_factory=list)  # [{date, title, has_candidates}]


def _collect_write_layer_files(dirs: list[str]) -> list[str]:
    """Collect all files from write-layer directories."""
    files: list[str] = []
    for d in dirs:
        dp = Path(d)
        if dp.is_dir():
            for f in sorted(dp.rglob("*")):
                if f.is_file() and not f.name.startswith("."):
                    files.append(str(f))
    return files


def _apply_promotion_gate(
    candidates: list,
    result: CompactionResult,
    changes_applied: list[str],
) -> None:
    """Separate candidates through the promotion gate.

    - rule with needs_approval=false + confidence=high -> auto-promote
    - rule with needs_approval=true -> add to root_suggestions
    - fact -> add to architecture_updates
    """
    for c in candidates:
        if c.type == "rule":
            if not c.needs_approval and c.confidence == "high":
                # Auto-promote: add to promoted_rules
                result.promoted_rules.append(c)
                changes_applied.append(
                    f"Auto-promoted rule: {c.text} (scope: {c.scope})"
                )
            else:
                # Needs human review: propose for root CLAUDE.md
                result.root_suggestions.append(
                    f"[{c.confidence}] {c.text} (scope: {c.scope})"
                )
        elif c.type == "fact":
            result.promoted_facts.append(c)
            subsystem_info = f" [{c.subsystem}]" if c.subsystem else ""
            result.architecture_updates.append(
                f"{c.text}{subsystem_info}"
            )
            changes_applied.append(
                f"ARCHITECTURE.md: added fact — {c.text}"
            )


def compact(
    project_root: str,
    mode: str = "prompt-only",  # "prompt-only" | "auto"
    write_layer_dirs: list[str] | None = None,
    progress_path: str = "progress.yaml",
) -> CompactionResult:
    """Main compaction entry point.

    1. Load compaction state
    2. Scan write-layer dirs for changed files
    3. Process unabsorbed progress.yaml entries
    4. Separate candidates: rule vs fact
    5. Apply promotion gate:
       - rule with needs_approval=false + confidence=high -> auto-promote
       - rule with needs_approval=true -> add to root_suggestions
       - fact -> add to architecture_updates
    6. Generate changelog
    7. If mode == "prompt-only": return result with structured prompt text
       If mode == "auto": shell out to `claude --print` (optional, not implemented in v1)

    IMPORTANT: Root CLAUDE.md is NEVER auto-written. Only proposals in root_suggestions.

    progress_path defaults to 'progress.yaml' (YAML format).
    """
    root = Path(project_root)
    state_file = str(root / ".compaction-state.json")
    state = CompactionState(state_path=state_file)

    # Default write-layer dirs
    if write_layer_dirs is None:
        write_layer_dirs = [str(root)]

    # --- Step 1-2: Detect changed files ---
    all_files = _collect_write_layer_files(write_layer_dirs)
    changed_files = state.changed_since_last(all_files)

    changed_descriptions: list[str] = []
    changes_applied: list[str] = []

    for f in changed_files:
        rel = str(Path(f).relative_to(root)) if f.startswith(str(root)) else f
        changed_descriptions.append(f"{rel} (modified)")

    # --- Step 3-5: Process progress.yaml candidates ---
    progress_full = root / progress_path
    all_candidates: list = []
    reviewed_entries: list[dict] = []

    if get_unprocessed is not None and progress_full.exists():
        unprocessed = get_unprocessed(str(progress_full))
        for entry in unprocessed:
            reviewed_entries.append({
                "date": entry.date,
                "title": entry.title,
                "has_candidates": bool(entry.candidates),
            })
            if entry.candidates:
                all_candidates.extend(entry.candidates)
                changed_descriptions.append(
                    f"{progress_path} ({len(entry.candidates)} candidate(s) from {entry.date})"
                )

    result = CompactionResult(changelog="", reviewed_entries=reviewed_entries)

    # Apply promotion gate
    _apply_promotion_gate(all_candidates, result, changes_applied)

    # --- Step 6: Generate changelog ---
    result.changelog = generate_changelog(
        changed_files=changed_descriptions,
        changes_applied=changes_applied,
    )

    # --- Step 7: Update compaction state for changed files ---
    for f in changed_files:
        state.update(f)

    # mode == "auto" is reserved for future implementation
    if mode == "auto":
        # Not implemented in v1; fall through to prompt-only behavior
        pass

    return result


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Sentinel compaction CLI")
    parser.add_argument(
        "--progress", default="progress.yaml", help="Path to progress.yaml"
    )
    parser.add_argument(
        "--mark-absorbed",
        nargs=2,
        metavar=("DATE", "TITLE"),
        help="Mark an entry as absorbed",
    )
    parser.add_argument(
        "--absorbed-to",
        default="CLAUDE.md/ARCHITECTURE.md",
        help="Target of absorption",
    )
    args = parser.parse_args()

    if args.mark_absorbed:
        if mark_absorbed is not None:
            mark_absorbed(
                args.progress,
                args.mark_absorbed[0],
                args.mark_absorbed[1],
                args.absorbed_to,
            )
            print(
                json.dumps(
                    {
                        "status": "absorbed",
                        "date": args.mark_absorbed[0],
                        "title": args.mark_absorbed[1],
                    }
                )
            )
        else:
            print(json.dumps({"error": "writeback module not available"}))
        sys.exit(0)

    result = compact(".", progress_path=args.progress)
    output = {
        "auto_promote_rules": [
            {"text": c.text, "scope": c.scope} for c in result.promoted_rules
        ],
        "suggested_rules": result.root_suggestions,
        "architecture_facts": result.architecture_updates,
        "reviewed_entries": result.reviewed_entries,
        "changelog": result.changelog,
    }
    print(json.dumps(output, indent=2))
