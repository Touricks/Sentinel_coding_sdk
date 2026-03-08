# Export Directory

Store templates and rubrics here. The `/export` skill reads this directory to find format templates and grading rubrics.

## Templates

Place format-specific templates in this directory:
- `.tex` — LaTeX templates for PDF export
- `.pptx` — PowerPoint templates for slide export
- `.docx` — Word templates for document export

**Non-markdown exports require a template.** The export skill will refuse to generate non-markdown output without one.

## Rubrics

Place rubric files here (any file with "rubric" in the name). The export skill will automatically check content against rubric criteria if one exists.

## Output

Generated exports are written to `output/`. Source documents are never overwritten.

## Compliance

Before rendering, the export skill runs a compliance lint pass that detects:
1. Chain-of-thought leaks (self-correction, reasoning traces)
2. Structural tells (AI vocabulary, em dash density, emoji)
3. Phantom references (appendix/figure/section refs with no target)
4. Statistical fingerprint (opt-in, uniform sentence/paragraph lengths)

Auto-fixable findings can be applied automatically. Non-fixable findings are flagged for manual review.
