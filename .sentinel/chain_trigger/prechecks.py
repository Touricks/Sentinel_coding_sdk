# ---
# input: project_root, changed_files list, YAML front-matter headers
# output: PrecheckResult dataclass; run_all_prechecks orchestrator
# pos: .sentinel/chain_trigger/prechecks.py
# last_modified: 2026-03-06
# ---

"""Tier 1 deterministic validation: schema, file references, symbol references, manifests."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PrecheckResult:
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def merge(self, other: PrecheckResult) -> None:
        """Merge another result into this one."""
        if not other.passed:
            self.passed = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def _simple_yaml_parse(text: str) -> dict:
    """Parse simple key: value YAML (no nesting needed for headers).

    Handles single-line ``key: value`` pairs. Values are kept as strings.
    Lines starting with ``#`` (inside the front-matter block) are ignored.
    """
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key:
                result[key] = value
    return result


def parse_yaml_header(file_path: str) -> dict | None:
    """Extract YAML front matter from a source file.

    Handles both ``# ---`` (Python/bash) and ``// ---`` (TypeScript) comment
    styles, as well as bare ``---`` (markdown) front matter.

    Returns ``None`` if no front matter is found.
    """
    try:
        content = Path(file_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    lines = content.splitlines()
    if not lines:
        return None

    # Detect opening delimiter
    first = lines[0].strip()
    if first in ("# ---", "// ---", "---"):
        # Determine the comment prefix so we can strip it
        if first.startswith("# "):
            prefix = "# "
        elif first.startswith("// "):
            prefix = "// "
        else:
            prefix = ""

        header_lines: list[str] = []
        for line in lines[1:]:
            stripped = line.strip()
            # Closing delimiter
            if stripped in ("# ---", "// ---", "---"):
                break
            # Strip the comment prefix if present
            if prefix and stripped.startswith(prefix):
                stripped = stripped[len(prefix):]
            elif prefix and stripped.startswith(prefix.rstrip()):
                # Handle lines like "#---" with no space
                stripped = stripped[len(prefix.rstrip()):]
            header_lines.append(stripped)

        if header_lines:
            return _simple_yaml_parse("\n".join(header_lines))

    return None


# ── Tier 1 checks ───────────────────────────────────────────────────────


def check_header_schema(header: dict) -> PrecheckResult:
    """Validate YAML front matter has required keys: input, output, pos."""
    result = PrecheckResult()
    required = ("input", "output", "pos")
    for key in required:
        if key not in header:
            result.passed = False
            result.errors.append(f"Missing required header key: {key}")

    if "last_modified" not in header:
        result.warnings.append("Header missing recommended key: last_modified")

    return result


def check_file_references(header: dict, project_root: str) -> PrecheckResult:
    """Verify referenced files in header exist on disk.

    Scans header values for tokens that look like file paths (contain ``/``
    or end with a known extension) and checks whether they exist under
    *project_root*.
    """
    result = PrecheckResult()
    path_pattern = re.compile(r"[\w./-]+(?:\.(?:py|ts|js|md|yaml|yml|json|sh|toml))")

    for _key, value in header.items():
        for match in path_pattern.finditer(str(value)):
            ref = match.group(0)
            # Only check things that look like relative paths
            if "/" in ref or ref.count(".") <= 1:
                full = os.path.join(project_root, ref)
                if not os.path.exists(full):
                    result.warnings.append(f"Referenced path not found: {ref}")

    return result


def check_symbol_references(header: dict, source_code: str) -> PrecheckResult:
    """Verify referenced symbols exist in code (basic regex).

    For the ``output`` field, splits on ``,`` / ``;`` / whitespace and checks
    that each token that looks like a Python/JS identifier appears somewhere
    in the source as a class, function, or export definition.
    """
    result = PrecheckResult()
    output_val = header.get("output", "")
    if not output_val:
        return result

    # Extract potential symbol names (PascalCase or snake_case identifiers)
    symbol_pattern = re.compile(r"\b([A-Za-z_]\w{2,})\b")
    symbols = symbol_pattern.findall(output_val)

    # Common noise words to skip
    noise = {
        "dataclass", "dataclasses", "function", "functions", "class",
        "classes", "module", "export", "returns", "list", "dict", "str",
        "int", "bool", "None", "True", "False", "and", "the", "for",
        "with", "from", "import", "output", "input", "pos",
    }

    definition_pattern = re.compile(
        r"(?:^|\n)\s*(?:class|def|export\s+(?:default\s+)?(?:function|class|const|let|var))\s+(\w+)",
    )
    defined = set(definition_pattern.findall(source_code))

    for sym in symbols:
        if sym.lower() in noise:
            continue
        if sym not in defined and sym not in source_code:
            result.warnings.append(f"Symbol '{sym}' from output field not found in source")

    return result


def check_directory_manifest(manifest_path: str, directory: str) -> PrecheckResult:
    """Verify manifest includes all files, excludes deleted, no duplicates.

    Parses the file-manifest table from a directory ``CLAUDE.md`` and cross-
    references with the actual files on disk.
    """
    result = PrecheckResult()

    try:
        manifest_text = Path(manifest_path).read_text(encoding="utf-8")
    except OSError:
        result.passed = False
        result.errors.append(f"Cannot read manifest: {manifest_path}")
        return result

    # Parse table rows: | filename | ... | ... |
    table_pattern = re.compile(r"^\|\s*([^\s|]+)\s*\|", re.MULTILINE)
    listed_files: list[str] = []
    for match in table_pattern.finditer(manifest_text):
        name = match.group(1).strip()
        # Skip header row and separator
        if name.startswith("-") or name.lower() == "file":
            continue
        listed_files.append(name)

    # Gather actual files (exclude CLAUDE.md, __pycache__, .pyc, etc.)
    exclude = {"CLAUDE.md", "__pycache__", ".DS_Store"}
    actual_files: set[str] = set()
    try:
        for entry in os.listdir(directory):
            if entry in exclude:
                continue
            if entry.startswith("."):
                continue
            full = os.path.join(directory, entry)
            if os.path.isfile(full) and not entry.endswith(".pyc"):
                actual_files.add(entry)
            elif os.path.isdir(full) and entry != "__pycache__":
                # Directories like tests/ may or may not be listed
                pass
    except OSError:
        result.passed = False
        result.errors.append(f"Cannot list directory: {directory}")
        return result

    listed_set = set(listed_files)

    # Check for duplicates
    if len(listed_files) != len(listed_set):
        result.passed = False
        seen: set[str] = set()
        for f in listed_files:
            if f in seen:
                result.errors.append(f"Duplicate manifest entry: {f}")
            seen.add(f)

    # Check for missing files
    missing = actual_files - listed_set
    for f in sorted(missing):
        result.passed = False
        result.errors.append(f"File not in manifest: {f}")

    # Check for stale entries
    stale = listed_set - actual_files
    for f in sorted(stale):
        result.passed = False
        result.errors.append(f"Stale manifest entry (file not on disk): {f}")

    return result


def run_all_prechecks(project_root: str, changed_files: list[str]) -> PrecheckResult:
    """Orchestrate all Tier 1 checks for changed files.

    For each changed file:
      1. Parse its YAML header
      2. Run ``check_header_schema``
      3. Run ``check_file_references``
      4. Run ``check_symbol_references``

    For each affected directory:
      5. Run ``check_directory_manifest``

    Returns an aggregated ``PrecheckResult``.
    """
    aggregate = PrecheckResult()
    affected_dirs: set[str] = set()

    for fpath in changed_files:
        full_path = (
            fpath
            if os.path.isabs(fpath)
            else os.path.join(project_root, fpath)
        )

        # Track the directory
        parent = os.path.dirname(full_path)
        if parent:
            affected_dirs.add(parent)

        # Parse header
        header = parse_yaml_header(full_path)
        if header is None:
            aggregate.warnings.append(f"No YAML header found: {fpath}")
            continue

        # 1. Schema check
        aggregate.merge(check_header_schema(header))

        # 2. File references
        aggregate.merge(check_file_references(header, project_root))

        # 3. Symbol references
        try:
            source = Path(full_path).read_text(encoding="utf-8")
        except OSError:
            source = ""
        aggregate.merge(check_symbol_references(header, source))

    # 4. Directory manifests
    for d in affected_dirs:
        manifest = os.path.join(d, "CLAUDE.md")
        if os.path.isfile(manifest):
            aggregate.merge(check_directory_manifest(manifest, d))

    return aggregate
