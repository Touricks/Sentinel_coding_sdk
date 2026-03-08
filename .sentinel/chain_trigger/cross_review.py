# ---
# input: source_code files, generated headers/manifests
# output: Finding, ReviewResult dataclasses; review_with_codex orchestrator
# pos: .sentinel/chain_trigger/cross_review.py
# last_modified: 2026-03-06
# ---

"""Tier 2 cross-LLM review via Codex CLI.

Sends auto-generated documentation to Codex for independent verification
against actual source code. Uses zero-shot prompting with structured
markdown-table output (Decision #25).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field


@dataclass
class Finding:
    file: str
    claim: str
    status: str  # "pass" | "flag"
    reason: str


@dataclass
class ReviewResult:
    passed: bool = True
    findings: list[Finding] = field(default_factory=list)
    rounds_used: int = 0
    escalated: bool = False  # True if still failing after max_rounds


def codex_available() -> bool:
    """Check if ``codex`` binary is in PATH."""
    return shutil.which("codex") is not None


def build_review_prompt(
    source_code: str,
    generated_header: str,
    generated_manifest: str | None = None,
) -> str:
    """Build zero-shot prompt with output schema (Decision #25).

    The prompt asks Codex to review generated documentation against actual
    code and return a markdown table with columns:
    ``File | Claim | Status | Reason``

    NO few-shot examples (Decision #25). Just output schema specification.
    """
    parts: list[str] = [
        "Review this auto-generated documentation against the actual source code.",
        "For each claim in the documentation, output a markdown table:",
        "",
        "| File | Claim | Status | Reason |",
        "|------|-------|--------|--------|",
        "",
        "Status must be: pass or flag. Nothing else.",
        "Do NOT modify any files. Do NOT run any shell commands.",
        "Return ONLY structured findings as a markdown table.",
        "",
        "## Source Code",
        "```",
        source_code,
        "```",
        "",
        "## Generated Header",
        "```",
        generated_header,
        "```",
    ]

    if generated_manifest:
        parts.extend([
            "",
            "## Generated Manifest",
            "```",
            generated_manifest,
            "```",
        ])

    return "\n".join(parts)


def call_codex(prompt: str, output_path: str = "/tmp/codex_output.md") -> str:
    """Invoke ``codex exec --full-auto --skip-git-repo-check -o <output> -``.

    Uses stdin pipe to pass the prompt.
    Returns the content of the output file.
    """
    cmd = [
        "codex",
        "exec",
        "--full-auto",
        "--skip-git-repo-check",
        "-o",
        output_path,
        "-",
    ]

    try:
        subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""

    try:
        with open(output_path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def parse_findings(codex_output: str) -> list[Finding]:
    """Parse markdown table into structured findings.

    Expected format::

        | File | Claim | Status | Reason |
        |------|-------|--------|--------|
        | auth.py | input: sqlalchemy | pass | imports sqlalchemy on line 3 |
    """
    findings: list[Finding] = []

    # Match table rows (skip header and separator lines)
    row_pattern = re.compile(
        r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(pass|flag)\s*\|\s*([^|]+?)\s*\|",
        re.MULTILINE | re.IGNORECASE,
    )

    for match in row_pattern.finditer(codex_output):
        file_val = match.group(1).strip()
        claim = match.group(2).strip()
        status = match.group(3).strip().lower()
        reason = match.group(4).strip()

        # Skip the header row
        if file_val.lower() == "file" or file_val.startswith("-"):
            continue

        findings.append(Finding(
            file=file_val,
            claim=claim,
            status=status,
            reason=reason,
        ))

    return findings


def review_with_codex(
    source_files: dict[str, str],  # path -> content
    generated_docs: dict[str, str],  # path -> content
    max_rounds: int = 2,  # Decision #17: capped retry
) -> ReviewResult:
    """Full Tier 2 flow.

    1. Build review prompt from source files + generated docs
    2. Call codex
    3. Parse findings
    4. If any flags: return result for correction
    5. If correction applied: re-review (up to max_rounds)
    6. If still flagging after max_rounds: escalate=True
    """
    result = ReviewResult()

    if not codex_available():
        result.passed = False
        result.findings.append(Finding(
            file="(system)",
            claim="codex availability",
            status="flag",
            reason="codex binary not found in PATH",
        ))
        return result

    for round_num in range(1, max_rounds + 1):
        result.rounds_used = round_num

        # Build combined source and doc strings
        source_combined = "\n\n".join(
            f"# {path}\n{content}" for path, content in source_files.items()
        )
        doc_combined = "\n\n".join(
            f"# {path}\n{content}" for path, content in generated_docs.items()
        )

        prompt = build_review_prompt(source_combined, doc_combined)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, prefix="codex_review_",
        ) as tmp:
            output_path = tmp.name

        raw_output = call_codex(prompt, output_path=output_path)
        findings = parse_findings(raw_output)
        result.findings = findings

        flags = [f for f in findings if f.status == "flag"]
        if not flags:
            result.passed = True
            return result

        result.passed = False

        # If this is not the last round, allow correction opportunity
        if round_num < max_rounds:
            continue

    # Exhausted all rounds with flags still present
    result.escalated = True
    return result
