# ---
# input: project_root, changed_files, branch name; imports prechecks, cross_review, self_review
# output: PropagationResult dataclass; propagate orchestrator
# pos: .sentinel/chain_trigger/propagate.py
# last_modified: 2026-03-06
# ---

"""Three-layer propagation engine with tier-selected review.

Orchestrates the chain-trigger pipeline: detects operation types,
selects review tiers based on branch and change volume, runs Tier 1
prechecks, and optionally invokes Tier 2 (Codex) or falls back to
Tier 3 (self-review).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

from .prechecks import run_all_prechecks, PrecheckResult
from .cross_review import codex_available, review_with_codex, ReviewResult
from .self_review import (
    ConfidenceItem,
    self_review_header,
    self_review_manifest,
    flag_low_confidence,
)


@dataclass
class PropagationResult:
    headers_updated: list[str] = field(default_factory=list)
    manifests_updated: list[str] = field(default_factory=list)
    root_notifications: list[str] = field(default_factory=list)
    review_result: ReviewResult | None = None
    low_confidence_flags: list[ConfidenceItem] = field(default_factory=list)
    precheck_result: PrecheckResult | None = None


def detect_operation_type(changed_files: list[str]) -> dict[str, str]:
    """Classify files as CREATE (git A) or UPDATE (git M).

    Decision #26: Uses ``git diff --cached --name-status`` or
    ``git diff --name-status HEAD~1``.

    Returns dict mapping file path -> "A" (added/created) or "M" (modified/updated).
    Falls back to classifying everything as "M" if git is unavailable.
    """
    result: dict[str, str] = {}

    # Try git diff --cached first (staged changes)
    for cmd in (
        ["git", "diff", "--cached", "--name-status"],
        ["git", "diff", "--name-status", "HEAD~1"],
    ):
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                for line in proc.stdout.strip().splitlines():
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        status, path = parts
                        # Normalize: R (rename), C (copy) -> treat as A
                        status_char = status[0].upper()
                        if status_char in ("R", "C"):
                            status_char = "A"
                        elif status_char not in ("A", "M", "D"):
                            status_char = "M"
                        result[path] = status_char
                if result:
                    break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    # Fall back: if git didn't provide info, classify from changed_files list
    if not result:
        for f in changed_files:
            result[f] = "M"  # conservative default

    return result


def _get_current_branch() -> str | None:
    """Get current git branch name."""
    try:
        proc = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0:
            branch = proc.stdout.strip()
            return branch if branch else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def select_review_tier(
    branch: str | None,
    operation_types: dict[str, str],
) -> str:
    """Select review tier based on branch type and operation types.

    Decision #18 + #26:
    - Local/dev branch: "tier1" only
    - Feature branch + UPDATE >3 files: "tier1+tier2"
    - Feature branch + CREATE or UPDATE <=3: "tier1"
    - main/release: "tier1+tier2" (always)

    Returns: "tier1" or "tier1+tier2"
    """
    if branch is None:
        branch = _get_current_branch() or "unknown"

    # main/release branches always get full review
    if branch in ("main", "master", "release") or branch.startswith("release/"):
        return "tier1+tier2"

    # Local/dev branches: minimal review
    local_prefixes = ("dev/", "local/", "tmp/", "wip/")
    if branch.startswith(local_prefixes) or branch in ("dev", "local"):
        return "tier1"

    # Feature branches: check update count
    update_count = sum(1 for s in operation_types.values() if s == "M")
    if update_count > 3:
        return "tier1+tier2"

    return "tier1"


def propagate(
    project_root: str,
    changed_files: list[str],
    branch: str | None = None,
) -> PropagationResult:
    """Three-layer propagation with tier-selected review.

    1. Detect operation types (CREATE vs UPDATE)
    2. Select review tier
    3. Run Tier 1 prechecks (always)
    4. If tier includes Tier 2:
       a. Try Codex (cross_review)
       b. Fall back to self_review (Tier 3) if Codex unavailable
    5. Collect results

    Note: This function does NOT actually update the files -- it orchestrates
    the review process. The actual file updates are done by the calling code
    (typically the Claude Code agent during its normal operation).
    """
    result = PropagationResult()

    # 1. Detect operation types
    operation_types = detect_operation_type(changed_files)

    # 2. Select review tier
    tier = select_review_tier(branch, operation_types)

    # 3. Run Tier 1 prechecks (always)
    precheck = run_all_prechecks(project_root, changed_files)
    result.precheck_result = precheck

    # Track which headers and manifests were checked
    import os
    from pathlib import Path
    from .prechecks import parse_yaml_header

    affected_dirs: set[str] = set()
    for fpath in changed_files:
        full_path = (
            fpath
            if os.path.isabs(fpath)
            else os.path.join(project_root, fpath)
        )
        parent = os.path.dirname(full_path)
        if parent:
            affected_dirs.add(parent)

        header = parse_yaml_header(full_path)
        if header:
            result.headers_updated.append(fpath)

    for d in affected_dirs:
        manifest = os.path.join(d, "CLAUDE.md")
        if os.path.isfile(manifest):
            result.manifests_updated.append(manifest)

    # 4. If tier includes Tier 2, attempt cross-review
    if "tier2" in tier:
        if codex_available():
            # Build source and doc dicts
            source_files: dict[str, str] = {}
            generated_docs: dict[str, str] = {}

            for fpath in changed_files:
                full_path = (
                    fpath
                    if os.path.isabs(fpath)
                    else os.path.join(project_root, fpath)
                )
                try:
                    content = Path(full_path).read_text(encoding="utf-8")
                    source_files[fpath] = content
                except OSError:
                    continue

                header = parse_yaml_header(full_path)
                if header:
                    # Reconstruct header text as the "generated doc"
                    header_text = "\n".join(
                        f"{k}: {v}" for k, v in header.items()
                    )
                    generated_docs[fpath] = header_text

            if source_files and generated_docs:
                review = review_with_codex(source_files, generated_docs)
                result.review_result = review
        else:
            # Fall back to Tier 3: self-review
            for fpath in changed_files:
                full_path = (
                    fpath
                    if os.path.isabs(fpath)
                    else os.path.join(project_root, fpath)
                )
                try:
                    source = Path(full_path).read_text(encoding="utf-8")
                except OSError:
                    continue

                header = parse_yaml_header(full_path)
                if header:
                    confidence_items = self_review_header(header, source)
                    low = flag_low_confidence(confidence_items)
                    result.low_confidence_flags.extend(low)

            for d in affected_dirs:
                manifest = os.path.join(d, "CLAUDE.md")
                if os.path.isfile(manifest):
                    try:
                        manifest_content = Path(manifest).read_text(
                            encoding="utf-8",
                        )
                    except OSError:
                        continue
                    confidence_items = self_review_manifest(manifest_content, d)
                    low = flag_low_confidence(confidence_items)
                    result.low_confidence_flags.extend(low)

    # 5. Root notifications
    if precheck.errors:
        result.root_notifications.append(
            f"Tier 1 prechecks found {len(precheck.errors)} error(s)"
        )
    if result.review_result and result.review_result.escalated:
        result.root_notifications.append(
            "Tier 2 cross-review escalated: flags remain after max rounds"
        )
    if result.low_confidence_flags:
        result.root_notifications.append(
            f"Tier 3 self-review: {len(result.low_confidence_flags)} low-confidence item(s)"
        )

    return result
