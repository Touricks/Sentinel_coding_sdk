# ---
# input: document text (markdown/plain)
# output: ComplianceResult with findings; apply_auto_fixes returns cleaned text
# pos: .sentinel/export/compliance.py
# last_modified: 2026-03-06
# ---

"""Compliance lint pass: detect AI writing patterns and apply safe auto-fixes.

Four check types:
  1. Chain-of-thought / self-correction leaks
  2. Structural tells (em dash density, AI vocabulary, emoji, etc.)
  3. Phantom references (appendix/figure/section/table refs with no target)
  4. Statistical fingerprint (sentence/paragraph uniformity) — opt-in

Policy lives here; orchestration lives in SKILL.md.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum


# ── Enums ────────────────────────────────────────────────────────────────


class FindingType(IntEnum):
    COT = 1
    STRUCTURAL = 2
    PHANTOM = 3
    STATISTICAL = 4


class Severity(StrEnum):
    AUTO_FIXABLE = "auto_fixable"
    SUGGEST_FIX = "suggest_fix"
    HUMAN_REVIEW = "human_review_required"


# ── Data Structures ─────────────────────────────────────────────────────


@dataclass
class Span:
    start: int  # character offset in full document
    end: int
    line: int  # 1-based line number


@dataclass
class ComplianceFinding:
    type: FindingType
    severity: Severity
    span: Span
    pattern: str
    matched_text: str
    suggestion: str


@dataclass
class ComplianceResult:
    findings: list[ComplianceFinding] = field(default_factory=list)
    type_counts: dict[FindingType, int] = field(default_factory=lambda: {
        FindingType.COT: 0,
        FindingType.STRUCTURAL: 0,
        FindingType.PHANTOM: 0,
        FindingType.STATISTICAL: 0,
    })
    auto_fixable_count: int = 0
    human_review_count: int = 0


# ── Document Segmentation ───────────────────────────────────────────────


@dataclass
class ScannableRegion:
    text: str
    original_offset: int  # maps back to full document position


def _line_number_at(text: str, offset: int) -> int:
    """Return 1-based line number for a character offset."""
    return text[:offset].count("\n") + 1


def segment_document(text: str, exclude_blockquotes: bool = False) -> list[ScannableRegion]:
    """Extract scannable prose regions, excluding code/front-matter/math/URLs.

    Args:
        text: Full document text.
        exclude_blockquotes: If True, also exclude blockquote lines (for Type 1).
    """
    regions: list[ScannableRegion] = []

    # Strip YAML front matter
    fm_match = re.match(r"\A(?:#\s*)?---\n.*?\n(?:#\s*)?---\n", text, re.DOTALL)
    scan_start = fm_match.end() if fm_match else 0

    # Build exclusion zones
    exclusions: list[tuple[int, int]] = []

    # YAML front matter
    if fm_match:
        exclusions.append((0, fm_match.end()))

    # Fenced code blocks
    for m in re.finditer(r"```.*?```", text, re.DOTALL):
        exclusions.append((m.start(), m.end()))

    # Inline code
    for m in re.finditer(r"`[^`\n]+`", text):
        exclusions.append((m.start(), m.end()))

    # LaTeX math environments
    for m in re.finditer(r"\$\$.*?\$\$", text, re.DOTALL):
        exclusions.append((m.start(), m.end()))
    for m in re.finditer(r"(?<!\$)\$(?!\$)[^$\n]+\$(?!\$)", text):
        exclusions.append((m.start(), m.end()))
    for m in re.finditer(r"\\begin\{equation\}.*?\\end\{equation\}", text, re.DOTALL):
        exclusions.append((m.start(), m.end()))

    # URLs
    for m in re.finditer(r"https?://[^\s)>\]]+", text):
        exclusions.append((m.start(), m.end()))

    # Blockquotes (optional, for Type 1)
    if exclude_blockquotes:
        for m in re.finditer(r"^>.*$", text, re.MULTILINE):
            exclusions.append((m.start(), m.end()))

    # Sort and merge exclusions
    exclusions.sort()
    merged: list[tuple[int, int]] = []
    for start, end in exclusions:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # Build scannable regions from gaps
    pos = scan_start
    for ex_start, ex_end in merged:
        if ex_start < pos:
            ex_start = pos
        if ex_start > pos:
            region_text = text[pos:ex_start]
            if region_text.strip():
                regions.append(ScannableRegion(text=region_text, original_offset=pos))
        pos = max(pos, ex_end)
    # Trailing region
    if pos < len(text):
        region_text = text[pos:]
        if region_text.strip():
            regions.append(ScannableRegion(text=region_text, original_offset=pos))

    return regions


# ── AI Vocabulary ────────────────────────────────────────────────────────

AI_VOCAB_AUTO_FIX = {
    "delve": "examine",
    "tapestry": "combination",
    "synergy": "combination",
    "multifaceted": "complex",
    "holistic": "comprehensive",
}

AI_VOCAB_SUGGESTIONS = {
    "leverage": "use",
    "robust": "strong",
    "cutting-edge": "modern",
    "streamline": "simplify",
    "paradigm": "model",
    "pivotal": "important",
    "harness": "use",
    "foster": "encourage",
    "encompass": "include",
    "meticulous": "careful",
    "noteworthy": "notable",
    "groundbreaking": "significant",
    "intricate": "complex",
    "landscape": "field",
}

# Promotional phrases
PROMOTIONAL_PHRASES = [
    "game-changer",
    "revolutionize",
    "world-class",
    "best-in-class",
    "next-generation",
    "state-of-the-art",
    "unparalleled",
    "unprecedented",
    "transformative",
]

# Passive-voice hedging phrases
PASSIVE_HEDGING = [
    "it is important to note that",
    "it is worth considering",
    "it should be emphasized",
    "it is worth noting that",
    "it bears mentioning that",
]

# ── Pre-compiled Patterns ──────────────────────────────────────────────

_EMOJI_RE = re.compile(
    "[\U0001f300-\U0001f9ff\U0001fa00-\U0001fa6f\U0001fa70-\U0001faff"
    "\u2600-\u26ff\u2700-\u27bf]"
)
_LIST_ITEM_RE = re.compile(r"^[\s]*[-*]\s", re.MULTILINE)
_NEG_PAR_RE = re.compile(r"\bnot\s+(?:just|merely)\s+\w+.*?,\s*but\b", re.IGNORECASE)
_CONJ_RE = re.compile(r"\b(Furthermore|Moreover|Additionally|Consequently)\b")
_VAGUE_REF_RE = re.compile(r"[Aa]s\s+(?:mentioned|discussed|shown)\s+(?:above|below)", re.IGNORECASE)
_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]")


# ── Scan Helpers ────────────────────────────────────────────────────────


def _find_terms_in_regions(
    text: str,
    regions: list[ScannableRegion],
    terms: dict[str, str],
    pattern_id: str,
    severity: Severity,
    suggestion_fmt: str,
    use_word_boundary: bool = True,
) -> list[ComplianceFinding]:
    """Scan regions for term matches, returning findings.

    Args:
        terms: Mapping of lowercase term → replacement/suggestion text.
        suggestion_fmt: Format string with {matched} and {replacement} placeholders.
        use_word_boundary: Wrap pattern in \\b...\\b.
    """
    findings: list[ComplianceFinding] = []
    for region in regions:
        region_lower = region.text.lower()
        for term, replacement in terms.items():
            pat = rf"\b{re.escape(term)}\b" if use_word_boundary else re.escape(term)
            for m in re.finditer(pat, region_lower):
                abs_start = region.original_offset + m.start()
                abs_end = region.original_offset + m.end()
                matched = region.text[m.start():m.end()]
                findings.append(ComplianceFinding(
                    type=FindingType.STRUCTURAL,
                    severity=severity,
                    span=Span(start=abs_start, end=abs_end, line=_line_number_at(text, abs_start)),
                    pattern=pattern_id,
                    matched_text=matched,
                    suggestion=suggestion_fmt.format(matched=matched, replacement=replacement),
                ))
    return findings


# ── Type 1: Chain-of-Thought ────────────────────────────────────────────

_T1_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("T1-01", re.compile(r"\b(Wait|Actually|Hmm)\s*[\u2014\-:,]", re.IGNORECASE), "Chain-of-thought marker"),
    ("T1-02", re.compile(r"\b(let us|let me)\s+(reconsider|revisit|redo|rethink)\b", re.IGNORECASE), "Self-revision phrase"),
    ("T1-03", re.compile(r"\b(on second thought|more carefully)\b", re.IGNORECASE), "Reconsideration phrase"),
    ("T1-04", re.compile(r"\bStep \d+:"), "Numbered step in prose"),
    ("T1-05", re.compile(r"\bNo[.,]\s+The\s+(correct|actual|right|proper)\b"), "Self-correction pattern"),
]


def _check_type1(text: str, regions: list[ScannableRegion]) -> list[ComplianceFinding]:
    """Detect chain-of-thought / self-correction leaks."""
    findings: list[ComplianceFinding] = []

    for region in regions:
        for pattern_id, regex, desc in _T1_PATTERNS:
            for m in regex.finditer(region.text):
                abs_start = region.original_offset + m.start()
                abs_end = region.original_offset + m.end()
                findings.append(ComplianceFinding(
                    type=FindingType.COT,
                    severity=Severity.SUGGEST_FIX,
                    span=Span(start=abs_start, end=abs_end, line=_line_number_at(text, abs_start)),
                    pattern=pattern_id,
                    matched_text=m.group(0),
                    suggestion=f"{desc}. Consider rewriting to remove AI reasoning trace.",
                ))
    return findings


# ── Type 2: Structural Tells ────────────────────────────────────────────


def _check_type2(text: str, regions: list[ScannableRegion]) -> list[ComplianceFinding]:
    """Detect structural AI writing patterns."""
    findings: list[ComplianceFinding] = []
    scannable = "".join(r.text for r in regions)

    # T2-A: Em dash density
    em_dashes = list(re.finditer("\u2014", scannable))
    if len(scannable) > 0 and len(em_dashes) / max(len(scannable), 1) * 1000 > 3:
        for region in regions:
            for m in re.finditer("\u2014", region.text):
                abs_start = region.original_offset + m.start()
                findings.append(ComplianceFinding(
                    type=FindingType.STRUCTURAL,
                    severity=Severity.AUTO_FIXABLE,
                    span=Span(start=abs_start, end=abs_start + 1, line=_line_number_at(text, abs_start)),
                    pattern="T2-A",
                    matched_text="\u2014",
                    suggestion="High em dash density. Replace with comma or period.",
                ))

    # T2-B: Emoji
    for region in regions:
        for m in _EMOJI_RE.finditer(region.text):
            abs_start = region.original_offset + m.start()
            findings.append(ComplianceFinding(
                type=FindingType.STRUCTURAL,
                severity=Severity.AUTO_FIXABLE,
                span=Span(start=abs_start, end=abs_start + len(m.group(0)), line=_line_number_at(text, abs_start)),
                pattern="T2-B",
                matched_text=m.group(0),
                suggestion="Remove emoji from formal text.",
            ))

    # T2-C: Rule-of-three
    lists: list[int] = []
    current_count = 0
    in_list = False
    for line in text.splitlines():
        if _LIST_ITEM_RE.match(line):
            if not in_list:
                in_list = True
                current_count = 0
            current_count += 1
        else:
            if in_list and current_count > 0:
                lists.append(current_count)
                in_list = False
                current_count = 0
    if in_list and current_count > 0:
        lists.append(current_count)

    if len(lists) >= 3:
        three_count = sum(1 for n in lists if n == 3)
        if three_count / len(lists) > 0.5:
            findings.append(ComplianceFinding(
                type=FindingType.STRUCTURAL,
                severity=Severity.SUGGEST_FIX,
                span=Span(start=0, end=0, line=1),
                pattern="T2-C",
                matched_text=f"{three_count}/{len(lists)} lists have exactly 3 items",
                suggestion="Rule-of-three pattern. Vary list lengths for natural feel.",
            ))

    # T2-D: High-confidence AI vocabulary (auto_fixable)
    findings.extend(_find_terms_in_regions(
        text, regions, AI_VOCAB_AUTO_FIX, "T2-D", Severity.AUTO_FIXABLE,
        "AI vocabulary. Replace '{matched}' with '{replacement}'.",
    ))

    # T2-D2: Borderline AI vocabulary (suggest_fix)
    findings.extend(_find_terms_in_regions(
        text, regions, AI_VOCAB_SUGGESTIONS, "T2-D2", Severity.SUGGEST_FIX,
        "Borderline AI vocabulary. Consider replacing '{matched}' with '{replacement}'.",
    ))

    # T2-E: Promotional language
    promo_terms = {phrase: "" for phrase in PROMOTIONAL_PHRASES}
    findings.extend(_find_terms_in_regions(
        text, regions, promo_terms, "T2-E", Severity.SUGGEST_FIX,
        "Promotional language. Tone down or remove.",
    ))

    # T2-F: Negative parallelism
    for region in regions:
        for m in _NEG_PAR_RE.finditer(region.text):
            abs_start = region.original_offset + m.start()
            abs_end = region.original_offset + m.end()
            findings.append(ComplianceFinding(
                type=FindingType.STRUCTURAL,
                severity=Severity.SUGGEST_FIX,
                span=Span(start=abs_start, end=abs_end, line=_line_number_at(text, abs_start)),
                pattern="T2-F",
                matched_text=m.group(0),
                suggestion="Negative parallelism ('not just X, but Y'). Consider simpler phrasing.",
            ))

    # T2-G: Conjunctive density
    conj_matches = list(_CONJ_RE.finditer(scannable))
    word_count = len(scannable.split())
    if word_count > 0 and len(conj_matches) / max(word_count, 1) * 500 > 2:
        for region in regions:
            for m in _CONJ_RE.finditer(region.text):
                abs_start = region.original_offset + m.start()
                abs_end = region.original_offset + m.end()
                findings.append(ComplianceFinding(
                    type=FindingType.STRUCTURAL,
                    severity=Severity.SUGGEST_FIX,
                    span=Span(start=abs_start, end=abs_end, line=_line_number_at(text, abs_start)),
                    pattern="T2-G",
                    matched_text=m.group(0),
                    suggestion="High conjunctive density. Vary sentence transitions.",
                ))

    # T2-H: Sandwich structure
    lines = text.strip().splitlines()
    if len(lines) > 5:
        first_para = ""
        for line in lines:
            if line.strip():
                first_para = line.strip().lower()
                break
        sandwich_openers = [
            "in the modern", "in today's", "in the ever-evolving",
            "in the rapidly", "in the world of", "in the realm of",
        ]
        for opener in sandwich_openers:
            if first_para.startswith(opener):
                findings.append(ComplianceFinding(
                    type=FindingType.STRUCTURAL,
                    severity=Severity.SUGGEST_FIX,
                    span=Span(start=0, end=len(first_para), line=1),
                    pattern="T2-H",
                    matched_text=first_para[:80],
                    suggestion="Generic AI opening. Start with specific, concrete content.",
                ))
                break

    # T2-I: Passive-voice hedging
    hedging_terms = {phrase: "" for phrase in PASSIVE_HEDGING}
    findings.extend(_find_terms_in_regions(
        text, regions, hedging_terms, "T2-I", Severity.SUGGEST_FIX,
        "Passive-voice hedging. State the point directly.",
        use_word_boundary=False,
    ))

    return findings


# ── Type 3: Phantom References ──────────────────────────────────────────


def parse_document_structure(text: str) -> dict:
    """Extract headings, figures, tables, and appendices from document text."""
    structure: dict = {
        "headings": [],      # list of (level, number_str, text)
        "has_appendix": False,
        "figures": set(),    # set of figure numbers found
        "tables": set(),     # set of table numbers found
    }

    heading_re = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    for m in heading_re.finditer(text):
        level = len(m.group(1))
        heading_text = m.group(2).strip()
        structure["headings"].append((level, heading_text))
        if "appendix" in heading_text.lower():
            structure["has_appendix"] = True

    # Figures: ![...](...)  or  <img ...>  or  Figure N caption
    fig_def_re = re.compile(r"!\[.*?\]\(.*?\)|<img\s|[Ff]igure\s+(\d+)[.:]\s")
    for m in fig_def_re.finditer(text):
        if m.group(1):
            structure["figures"].add(int(m.group(1)))

    # Tables: detect markdown tables or "Table N:" captions
    table_def_re = re.compile(r"[Tt]able\s+(\d+)[.:]\s")
    for m in table_def_re.finditer(text):
        structure["tables"].add(int(m.group(1)))

    return structure


def _check_type3(text: str, regions: list[ScannableRegion]) -> list[ComplianceFinding]:
    """Detect phantom references (refs to non-existent targets)."""
    findings: list[ComplianceFinding] = []
    structure = parse_document_structure(text)

    for region in regions:
        # T3-A: Appendix references
        for m in re.finditer(r"[Ss]ee\s+[Aa]ppendix", region.text):
            if not structure["has_appendix"]:
                abs_start = region.original_offset + m.start()
                findings.append(ComplianceFinding(
                    type=FindingType.PHANTOM,
                    severity=Severity.SUGGEST_FIX,
                    span=Span(start=abs_start, end=region.original_offset + m.end(),
                              line=_line_number_at(text, abs_start)),
                    pattern="T3-A",
                    matched_text=m.group(0),
                    suggestion="References appendix that doesn't exist in document.",
                ))

        # T3-B: Figure references
        for m in re.finditer(r"[Ff]ig(?:ure)?\s*(\d+)", region.text):
            fig_num = int(m.group(1))
            if fig_num not in structure["figures"]:
                abs_start = region.original_offset + m.start()
                findings.append(ComplianceFinding(
                    type=FindingType.PHANTOM,
                    severity=Severity.SUGGEST_FIX,
                    span=Span(start=abs_start, end=region.original_offset + m.end(),
                              line=_line_number_at(text, abs_start)),
                    pattern="T3-B",
                    matched_text=m.group(0),
                    suggestion=f"Figure {fig_num} not found in document.",
                ))

        # T3-C: Section references
        for m in re.finditer(r"[Ss]ection\s+(\d+(?:\.\d+)*)", region.text):
            abs_start = region.original_offset + m.start()
            findings.append(ComplianceFinding(
                type=FindingType.PHANTOM,
                severity=Severity.SUGGEST_FIX,
                span=Span(start=abs_start, end=region.original_offset + m.end(),
                          line=_line_number_at(text, abs_start)),
                pattern="T3-C",
                matched_text=m.group(0),
                suggestion="Numbered section reference. Verify section exists.",
            ))

        # T3-D: Vague cross-references
        for m in _VAGUE_REF_RE.finditer(region.text):
            abs_start = region.original_offset + m.start()
            findings.append(ComplianceFinding(
                type=FindingType.PHANTOM,
                severity=Severity.SUGGEST_FIX,
                span=Span(start=abs_start, end=region.original_offset + m.end(),
                          line=_line_number_at(text, abs_start)),
                pattern="T3-D",
                matched_text=m.group(0),
                suggestion="Vague cross-reference. Use specific section/heading name.",
            ))

        # T3-E: Table references
        for m in re.finditer(r"[Tt]able\s+(\d+)", region.text):
            table_num = int(m.group(1))
            # Skip if this is a table definition ("Table 1: ..." or "Table 1. ...")
            after = region.text[m.end():m.end() + 2] if m.end() + 2 <= len(region.text) else ""
            if after.startswith(":") or after.startswith("."):
                continue
            if table_num not in structure["tables"]:
                abs_start = region.original_offset + m.start()
                findings.append(ComplianceFinding(
                    type=FindingType.PHANTOM,
                    severity=Severity.SUGGEST_FIX,
                    span=Span(start=abs_start, end=region.original_offset + m.end(),
                              line=_line_number_at(text, abs_start)),
                    pattern="T3-E",
                    matched_text=m.group(0),
                    suggestion=f"Table {table_num} not found in document.",
                ))

    return findings


# ── Type 4: Statistical Fingerprint ─────────────────────────────────────


def _check_type4(text: str) -> list[ComplianceFinding]:
    """Detect statistical uniformity patterns (opt-in)."""
    findings: list[ComplianceFinding] = []

    # Split into paragraphs (non-empty blocks separated by blank lines)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    # Filter out code blocks and headings
    prose_paragraphs = [
        p for p in paragraphs
        if not p.startswith("```") and not p.startswith("#") and len(p.split()) > 10
    ]

    if len(prose_paragraphs) < 3:
        return findings

    # T4-A: Sentence length std dev
    sentence_re = re.compile(r"[^.!?]+[.!?]")
    all_sentence_lengths: list[int] = []
    for para in prose_paragraphs:
        sentences = sentence_re.findall(para)
        for s in sentences:
            all_sentence_lengths.append(len(s.split()))

    if len(all_sentence_lengths) >= 5:
        std_dev = statistics.stdev(all_sentence_lengths)
        if std_dev < 5:
            findings.append(ComplianceFinding(
                type=FindingType.STATISTICAL,
                severity=Severity.HUMAN_REVIEW,
                span=Span(start=0, end=0, line=1),
                pattern="T4-A",
                matched_text=f"Sentence length std dev: {std_dev:.1f}",
                suggestion="Very uniform sentence lengths. Auto-fix cannot address "
                           "statistical patterns. Consider rewriting in your own words.",
            ))

    # T4-B: Paragraph length uniformity
    para_lengths = [len(p.split()) for p in prose_paragraphs]
    if len(para_lengths) >= 3:
        para_variance = statistics.variance(para_lengths)
        mean_len = statistics.mean(para_lengths)
        # Coefficient of variation < 0.15 is suspiciously uniform
        if mean_len > 0 and (para_variance ** 0.5) / mean_len < 0.15:
            findings.append(ComplianceFinding(
                type=FindingType.STATISTICAL,
                severity=Severity.HUMAN_REVIEW,
                span=Span(start=0, end=0, line=1),
                pattern="T4-B",
                matched_text=f"Paragraph length CV: {(para_variance ** 0.5) / mean_len:.2f}",
                suggestion="Very uniform paragraph lengths. Auto-fix cannot address "
                           "statistical patterns. Consider rewriting in your own words.",
            ))

    # T4-C: Unique word ratio uniformity
    unique_ratios: list[float] = []
    for para in prose_paragraphs:
        words = para.lower().split()
        if words:
            unique_ratios.append(len(set(words)) / len(words))

    if len(unique_ratios) >= 3:
        ratio_variance = statistics.variance(unique_ratios)
        if ratio_variance < 0.002:
            findings.append(ComplianceFinding(
                type=FindingType.STATISTICAL,
                severity=Severity.HUMAN_REVIEW,
                span=Span(start=0, end=0, line=1),
                pattern="T4-C",
                matched_text=f"Unique word ratio variance: {ratio_variance:.4f}",
                suggestion="Very uniform vocabulary density across paragraphs. Auto-fix "
                           "cannot address statistical patterns. Consider rewriting in your own words.",
            ))

    return findings


# ── Orchestrator ─────────────────────────────────────────────────────────


def check_compliance(
    text: str,
    skip_types: set[int] | None = None,
    enable_type4: bool = False,
) -> ComplianceResult:
    """Run all compliance checks.

    Type 4 (statistical) is skipped by default; pass enable_type4=True to include it.
    """
    if skip_types is None:
        skip_types = set()
    if not enable_type4:
        skip_types = skip_types | {4}

    all_findings: list[ComplianceFinding] = []

    # Segment once: type1 excludes blockquotes, type2+type3 share standard regions
    regions = segment_document(text)
    regions_no_bq = segment_document(text, exclude_blockquotes=True)

    if FindingType.COT not in skip_types:
        all_findings.extend(_check_type1(text, regions_no_bq))
    if FindingType.STRUCTURAL not in skip_types:
        all_findings.extend(_check_type2(text, regions))
    if FindingType.PHANTOM not in skip_types:
        all_findings.extend(_check_type3(text, regions))
    if FindingType.STATISTICAL not in skip_types:
        all_findings.extend(_check_type4(text))

    result = ComplianceResult(findings=all_findings)
    for f in all_findings:
        result.type_counts[f.type] = result.type_counts.get(f.type, 0) + 1
        if f.severity == Severity.AUTO_FIXABLE:
            result.auto_fixable_count += 1
        elif f.severity == Severity.HUMAN_REVIEW:
            result.human_review_count += 1

    return result


def apply_auto_fixes(text: str, findings: list[ComplianceFinding]) -> str:
    """Apply severity=auto_fixable fixes in reverse span order.

    Skips overlapping spans. After applying, caller should re-run
    check_compliance() to get fresh offsets for remaining findings.
    """
    auto_fixes = sorted(
        [f for f in findings if f.severity == Severity.AUTO_FIXABLE],
        key=lambda f: f.span.start,
        reverse=True,
    )

    result = text
    last_start = len(text)  # Track to skip overlapping spans

    for finding in auto_fixes:
        if finding.span.end > last_start:
            continue  # Skip overlapping span

        if finding.pattern == "T2-A":
            # Replace em dash with comma
            result = result[:finding.span.start] + "," + result[finding.span.end:]
        elif finding.pattern == "T2-B":
            # Remove emoji
            result = result[:finding.span.start] + result[finding.span.end:]
        elif finding.pattern == "T2-D":
            # Replace high-confidence AI vocab
            original = result[finding.span.start:finding.span.end]
            replacement = AI_VOCAB_AUTO_FIX.get(original.lower(), original)
            # Preserve original casing for first letter
            if original[0].isupper():
                replacement = replacement[0].upper() + replacement[1:]
            result = result[:finding.span.start] + replacement + result[finding.span.end:]

        last_start = finding.span.start

    return result


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Compliance lint for AI writing patterns")
    parser.add_argument("--input", required=True, help="Path to input file")
    parser.add_argument("--enable-type4", action="store_true", help="Enable statistical fingerprint checks")
    parser.add_argument("--auto-fix", action="store_true", help="Apply auto-fixes and print cleaned text")
    args = parser.parse_args()

    from pathlib import Path

    content = Path(args.input).read_text(encoding="utf-8")
    result = check_compliance(content, enable_type4=args.enable_type4)

    if args.auto_fix:
        cleaned = apply_auto_fixes(content, result.findings)
        print(cleaned)
    else:
        output = {
            "file": args.input,
            "findings": [
                {
                    "type": f.type.name,
                    "severity": f.severity.value,
                    "line": f.span.line,
                    "pattern": f.pattern,
                    "matched_text": f.matched_text,
                    "suggestion": f.suggestion,
                }
                for f in result.findings
            ],
            "type_counts": {t.name: c for t, c in result.type_counts.items()},
            "auto_fixable_count": result.auto_fixable_count,
            "human_review_count": result.human_review_count,
            "total_findings": len(result.findings),
        }
        print(json.dumps(output, indent=2))
