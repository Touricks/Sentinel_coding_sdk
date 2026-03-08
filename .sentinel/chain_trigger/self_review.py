# ---
# input: header dict, source_code str, manifest content, directory path
# output: ConfidenceItem dataclass; self_review_header, self_review_manifest, flag_low_confidence
# pos: .sentinel/chain_trigger/self_review.py
# last_modified: 2026-03-06
# ---

"""Tier 3 fallback: checklist-based self-review with confidence scoring.

Used when Codex (Tier 2) is unavailable. Applies heuristic checks and
assigns confidence levels so that low-confidence items can be flagged
for human attention (Decision #19).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass
class ConfidenceItem:
    item: str
    confidence: str  # "high" | "med" | "low"
    reason: str


def self_review_header(header: dict, source_code: str) -> list[ConfidenceItem]:
    """Checklist-based verification of file header against code.

    Checks:
    - input: do the listed imports/deps appear in the code?
    - output: do the listed exports appear in the code?
    - pos: is the described role consistent with imports/exports?

    Confidence levels:
    - high: directly verifiable from code (imports, return types)
    - med: requires inference (architectural role, module boundaries)
    - low: uncertain (complex dependencies, ambiguous role)
    """
    items: list[ConfidenceItem] = []

    # ── Check input field ────────────────────────────────────────────
    input_val = header.get("input", "")
    if input_val:
        # Extract tokens that might be import/dependency names
        tokens = re.findall(r"\b([A-Za-z_][\w.]*)\b", input_val)
        # Noise words to skip
        noise = {
            "and", "or", "the", "a", "an", "from", "with", "for", "to",
            "in", "of", "str", "int", "bool", "list", "dict", "path",
            "file", "files", "directory", "input", "output",
        }
        import_pattern = re.compile(
            r"(?:^|\n)\s*(?:import|from)\s+([\w.]+)",
        )
        imports_found = set(import_pattern.findall(source_code))
        # Flatten dotted imports: "os.path" -> {"os", "os.path"}
        flat_imports: set[str] = set()
        for imp in imports_found:
            flat_imports.add(imp)
            for part in imp.split("."):
                flat_imports.add(part)

        for token in tokens:
            if token.lower() in noise:
                continue
            if token in flat_imports or token in source_code:
                items.append(ConfidenceItem(
                    item=f"input dependency: {token}",
                    confidence="high",
                    reason=f"'{token}' found in source imports/code",
                ))
            else:
                items.append(ConfidenceItem(
                    item=f"input dependency: {token}",
                    confidence="low",
                    reason=f"'{token}' not found in source imports/code",
                ))

    # ── Check output field ───────────────────────────────────────────
    output_val = header.get("output", "")
    if output_val:
        # Look for symbol-like tokens
        symbol_pattern = re.compile(r"\b([A-Z_][A-Za-z_]\w{1,})\b")
        symbols = symbol_pattern.findall(output_val)

        definition_pattern = re.compile(
            r"(?:^|\n)\s*(?:class|def|export\s+(?:default\s+)?"
            r"(?:function|class|const|let|var))\s+(\w+)",
        )
        defined = set(definition_pattern.findall(source_code))

        for sym in symbols:
            if sym in defined:
                items.append(ConfidenceItem(
                    item=f"output symbol: {sym}",
                    confidence="high",
                    reason=f"'{sym}' defined in source code",
                ))
            elif sym in source_code:
                items.append(ConfidenceItem(
                    item=f"output symbol: {sym}",
                    confidence="med",
                    reason=f"'{sym}' appears in source but not as definition",
                ))
            else:
                items.append(ConfidenceItem(
                    item=f"output symbol: {sym}",
                    confidence="low",
                    reason=f"'{sym}' not found in source code",
                ))

    # ── Check pos field ──────────────────────────────────────────────
    pos_val = header.get("pos", "")
    if pos_val:
        # Heuristic: check if role description words appear in imports/exports
        role_words = re.findall(r"\b([a-z]{4,})\b", pos_val.lower())
        matches = sum(1 for w in role_words if w in source_code.lower())
        ratio = matches / max(len(role_words), 1)

        if ratio >= 0.5:
            items.append(ConfidenceItem(
                item=f"pos: {pos_val}",
                confidence="med",
                reason=f"{matches}/{len(role_words)} role keywords found in source",
            ))
        else:
            items.append(ConfidenceItem(
                item=f"pos: {pos_val}",
                confidence="low",
                reason=f"Only {matches}/{len(role_words)} role keywords found in source",
            ))

    return items


def self_review_manifest(
    manifest_content: str,
    directory: str,
) -> list[ConfidenceItem]:
    """Checklist-based verification of directory manifest.

    Checks:
    - All files in directory are listed
    - No deleted files are listed
    - Role descriptions are non-empty
    - Status values are valid (active/planned/deprecated)
    """
    items: list[ConfidenceItem] = []

    # Parse table rows: | filename | role | status |
    row_pattern = re.compile(
        r"^\|\s*(\S+)\s*\|\s*(.*?)\s*\|\s*(\S+)\s*\|",
        re.MULTILINE,
    )
    listed: dict[str, tuple[str, str]] = {}  # name -> (role, status)
    for match in row_pattern.finditer(manifest_content):
        name = match.group(1).strip()
        role = match.group(2).strip()
        status = match.group(3).strip()
        # Skip header and separator rows
        if name.startswith("-") or name.lower() == "file":
            continue
        listed[name] = (role, status)

    # Gather actual files
    exclude = {"CLAUDE.md", "__pycache__", ".DS_Store"}
    actual_files: set[str] = set()
    valid_statuses = {"active", "planned", "deprecated"}

    try:
        for entry in os.listdir(directory):
            if entry in exclude or entry.startswith("."):
                continue
            full = os.path.join(directory, entry)
            if os.path.isfile(full) and not entry.endswith(".pyc"):
                actual_files.add(entry)
    except OSError:
        items.append(ConfidenceItem(
            item=f"directory: {directory}",
            confidence="low",
            reason="Cannot list directory",
        ))
        return items

    # Check completeness
    missing = actual_files - set(listed.keys())
    for f in sorted(missing):
        items.append(ConfidenceItem(
            item=f"manifest entry: {f}",
            confidence="high",
            reason="File exists on disk but not listed in manifest",
        ))

    # Check for stale entries
    stale = set(listed.keys()) - actual_files
    for f in sorted(stale):
        items.append(ConfidenceItem(
            item=f"manifest entry: {f}",
            confidence="high",
            reason="Listed in manifest but file not found on disk",
        ))

    # Check role descriptions and status values
    for name, (role, status) in listed.items():
        if not role or role == "---":
            items.append(ConfidenceItem(
                item=f"manifest role: {name}",
                confidence="med",
                reason="Role description is empty",
            ))

        if status.lower() not in valid_statuses:
            items.append(ConfidenceItem(
                item=f"manifest status: {name}",
                confidence="high",
                reason=f"Invalid status '{status}'; expected one of {valid_statuses}",
            ))
        else:
            items.append(ConfidenceItem(
                item=f"manifest entry: {name}",
                confidence="high",
                reason=f"File listed with valid status '{status}'",
            ))

    return items


def flag_low_confidence(items: list[ConfidenceItem]) -> list[ConfidenceItem]:
    """Return items with confidence='low' for human attention (Decision #19)."""
    return [i for i in items if i.confidence == "low"]
