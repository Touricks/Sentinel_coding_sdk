# ---
# input: .sentinel/manifest.json, project root
# output: clean production copy at --dest
# pos: .sentinel/scripts/extract.py
# last_modified: 2026-03-06
# ---

"""Extract a clean production copy from the dogfood Sentinel directory.

Reads .sentinel/manifest.json to determine which paths to exclude.
Deterministic: same input always produces same output (minus timestamps).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Always skip these regardless of manifest
_ALWAYS_SKIP = {
    "__pycache__",
    ".pytest_cache",
    ".DS_Store",
    ".git",
}

_PRODUCTION_README = """\
# Project

> This project uses [Sentinel](docs/getting-started.md) for AI-managed documentation.

## Quick Start

1. Run `/start` in Claude Code to initialize
2. Run `/routing` to select project tools
3. Run `/boundary` to load tools
4. Start developing with `/sentinel-loop` or ad-hoc

## Sentinel Documentation

- [Getting Started](docs/getting-started.md)

## Requirements

- Python 3.11+
- Git
- Claude Code
"""


def _load_manifest(source: Path) -> dict:
    manifest_path = source / ".sentinel" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest at {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _should_exclude(rel_path: str, exclude_set: set[str]) -> bool:
    """Check if a relative path matches any exclusion rule."""
    for excl in exclude_set:
        if excl.endswith("/"):
            # Directory prefix match
            if rel_path == excl.rstrip("/") or rel_path.startswith(excl):
                return True
        else:
            # Exact file match
            if rel_path == excl:
                return True
    return False


def _get_git_sha(source: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source, capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def extract(source: Path, dest: Path, dry_run: bool = False, force: bool = False) -> dict:
    """Extract production copy from source to dest.

    Returns summary dict with counts and metadata.
    """
    manifest = _load_manifest(source)

    # Build exclusion set — only production_exclude, NOT start_scan_excluded
    # (start_scan_excluded is for /start scanning, not for extraction)
    exclude_set: set[str] = set(manifest.get("production_exclude", []))

    # Check destination safety
    if dest.exists() and any(dest.iterdir()) and not force:
        raise RuntimeError(
            f"Destination {dest} is not empty. Use --force to overwrite."
        )

    copied: list[str] = []
    excluded: list[str] = []

    # Walk source directory
    for root, dirs, files in os.walk(source):
        # Filter dirs in-place to skip excluded directories
        dirs[:] = [
            d for d in dirs
            if d not in _ALWAYS_SKIP
            and not _should_exclude(
                os.path.relpath(os.path.join(root, d), source) + "/",
                exclude_set,
            )
        ]

        for fname in files:
            if fname in _ALWAYS_SKIP:
                continue

            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, source)

            if _should_exclude(rel_path, exclude_set):
                excluded.append(rel_path)
                continue

            dest_path = dest / rel_path

            if dry_run:
                copied.append(rel_path)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full_path, dest_path)
                copied.append(rel_path)

    # Generate production README (replaces dogfood README)
    readme_dest = dest / "README.md"
    if not dry_run:
        readme_dest.parent.mkdir(parents=True, exist_ok=True)
        readme_dest.write_text(_PRODUCTION_README, encoding="utf-8")
    if "README.md" not in [c for c in copied]:
        copied.append("README.md (generated)")

    # Ensure docs/export/output/ exists
    output_dir = dest / "docs" / "export" / "output"
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        gitkeep = output_dir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")

    # Write extraction metadata
    manifest_text = (source / ".sentinel" / "manifest.json").read_text(encoding="utf-8")
    metadata = {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _get_git_sha(source),
        "manifest_sha256": hashlib.sha256(manifest_text.encode()).hexdigest(),
        "files_copied": len(copied),
        "files_excluded": len(excluded),
    }

    if not dry_run:
        meta_path = dest / ".sentinel" / "extraction.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "copied": copied,
        "excluded": excluded,
        "metadata": metadata,
        "dry_run": dry_run,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract clean production copy from Sentinel dogfood"
    )
    parser.add_argument(
        "--dest", required=True,
        help="Destination directory for production copy",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be copied without writing",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite non-empty destination",
    )
    args = parser.parse_args()

    # Source is the project root (parent of .sentinel/)
    source = Path(__file__).resolve().parent.parent.parent
    dest = Path(args.dest).resolve()

    print(f"Source:      {source}")
    print(f"Destination: {dest}")
    print(f"Mode:        {'DRY RUN' if args.dry_run else 'EXTRACT'}")
    print()

    result = extract(source, dest, dry_run=args.dry_run, force=args.force)

    print(f"Files copied:   {len(result['copied'])}")
    print(f"Files excluded: {len(result['excluded'])}")
    print()

    if args.dry_run:
        print("Would copy:")
        for f in sorted(result["copied"]):
            print(f"  + {f}")
        print()
        print("Would exclude:")
        for f in sorted(result["excluded"]):
            print(f"  - {f}")
    else:
        print(f"Extraction complete: {dest}")
        meta = result["metadata"]
        if meta["source_commit"]:
            print(f"Source commit: {meta['source_commit'][:12]}")


if __name__ == "__main__":
    main()
