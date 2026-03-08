# Getting Started with Sentinel

## Prerequisites

- Python 3.11+
- Git
- Claude Code
- (Optional) [Codex CLI](https://github.com/openai/codex) for Tier 2 cross-LLM review
- (Optional) Ralph Loop plugin for iterative development — `claude plugin install ralph-loop`

## Quick Start

### 1. Clone the template

```bash
cp -r sentinel-template/ my-project/
cd my-project/ && git init
```

### 2. Run /start

In Claude Code, run `/start`. This:
- Walks you through an 8-module guided interview
- Generates PRD.md, ARCHITECTURE.md, CLAUDE.md, progress.yaml
- Creates directory structure with manifests
- Installs git hooks (soft warnings, never blocks)
- Optionally backfills YAML headers on existing source files
- Activates chain-trigger and compaction pipelines

### 3. Run /routing

In Claude Code, run `/routing`. This:
- Scans all available global skills and MCP tools against your project context
- Classifies each as Include / Exclude / Uncertain
- Generates `docs/tool-routing-report.md` for your review

Review the report. Fill in decisions for any "Uncertain" skills. Mark `status: approved` when ready.

### 4. Run /boundary

In Claude Code, run `/boundary`. This:
- Reads the approved routing report
- Generates `.claude/rules/tool-boundary.md` with capability declarations per tool
- Boundary declarations are auto-loaded in every future session

### 5. Start developing

Sentinel is now fully operational. Two ways to work:

**Iterative development (recommended):** Run `/sentinel-loop`. This reads your project state (progress.yaml, PRD.md), proposes a development task with a strict completion condition, and (with your approval) launches a Ralph Loop. Each iteration auto-updates headers and manifests via chain-triggers. Requires the Ralph Loop plugin — install with `claude plugin install ralph-loop`.

**Ad-hoc sessions:** Work directly in Claude Code. Sentinel's chain-triggers and hooks operate automatically. Run `/progress` at the end of each session to log discoveries.

Either way, as you code:
- Chain-trigger auto-updates file headers and directory manifests
- Pre-commit hook warns about stale documentation
- Tool boundaries prevent routing confusion across sessions
- Use `/progress` to log session discoveries and promote candidates to CLAUDE.md / ARCHITECTURE.md

## How It Works

### YAML Front Matter (auto-managed)

Every source file gets a YAML front matter header:

```python
# ---
# input: os, pathlib
# output: MyClass, helper_func
# pos: utility module for file operations
# last_modified: 2026-03-05
# ---
```

Required keys: `input`, `output`, `pos`. Recommended: `last_modified`.

Headers are added automatically during `/start` (with confirmation) and kept in sync by the chain-trigger pipeline when files change.

### Directory Manifests (auto-managed)

Each directory gets an AI-managed `CLAUDE.md`:

```markdown
# src/

Brief description of the directory's role.

| File | Role | Status |
|------|------|--------|
| module.py | Description of what it does | active |
```

Created during `/start` and updated automatically by chain-triggers when files are added, removed, or modified.

### progress.yaml (session logging)

After each work session, run `/progress`. This appends a structured entry to progress.yaml (intake funnel for compaction) and optionally generates a durable session report under `docs/sessions/` — a permanent record of what was accomplished, separate from the intake funnel.

Entry format (YAML):

```yaml
- date: "2026-03-05"
  title: Session title
  status: unprocessed
  session_report: docs/sessions/2026-03-05-session-title.md
  next_steps:
    - What to do next
  candidates:
    - id: cand-2026-03-05-always-do-x
      type: rule
      text: Always do X
      scope: global
      confidence: high
      needs_approval: true
      promotion_targets: [CLAUDE.md]
```

### Development Loops (via /sentinel-loop)

`/sentinel-loop` bridges Sentinel's documentation system with iterative development:
1. Reads progress.yaml and PRD.md to identify the next task
2. Builds a structured prompt with project rules (verbatim from CLAUDE.md) and maintenance requirements
3. Proposes a strict completion condition (task + headers + manifests + progress logging)
4. With your approval, launches a Ralph Loop that iterates until the condition is met

Each loop iteration exercises Sentinel's chain-trigger pipeline — file headers and directory manifests stay in sync automatically. After completion, run `/sentinel-loop` again to plan the next task (no auto-chaining).

### Tool Routing and Boundaries (Type 2 degradation prevention)

`/routing` and `/boundary` work together to prevent tool routing confusion — when the AI agent loses track of which tools are available, what they can do, and when to use them.

- `/routing` produces `docs/tool-routing-report.md` — an inventory of all skills classified as Include/Exclude/Uncertain, with rationale. The developer reviews and approves.
- `/boundary` reads the approved report and generates `.claude/rules/tool-boundary.md` — per-tool declarations of purpose, capabilities, limitations, input constraints, chain patterns, and failure behavior.

These boundary declarations are auto-loaded into every Claude Code session, reducing context degradation from tool confusion. Re-run `/routing` → `/boundary` when onboarding new tools or when the project's tool needs change.

### Prechecks (automatic via hooks)

The pre-commit hook runs prechecks that warn when:
- A file was modified but its header wasn't updated
- A directory's CLAUDE.md is stale

Hooks always exit 0 — soft warnings only, never blocks commits.

### Export (/export)

When you need submission-ready documents, run `/export`. This:
1. Asks which docs to export and what format (md, PDF, PPTX, DOCX)
2. Runs a compliance lint pass detecting AI writing patterns (chain-of-thought leaks, AI vocabulary, phantom references)
3. Offers auto-fix for safe mechanical fixes (emoji removal, high-confidence AI vocab substitution)
4. Renders output to `docs/export/output/` using user-provided templates

Non-markdown formats require a template in `docs/export/`. The skill will not generate random templates.

Compliance CLI can also be run independently:
```bash
PYTHONPATH=.sentinel python -m export.compliance --input myfile.md
```

### Compaction (integrated into /progress)

When you run `/progress`, the compaction engine processes candidates automatically:
- Rule candidates are proposed for addition to CLAUDE.md (you approve each one)
- Fact candidates are proposed for addition to ARCHITECTURE.md
- Processed entries are marked as absorbed in progress.yaml

The compaction CLI can also be run independently for batch processing:
```bash
PYTHONPATH=.sentinel python .sentinel/compaction/compact.py
```

## Templates

| Template | Purpose |
|----------|---------|
| `root-claude-md.template.md` | Root CLAUDE.md structure |
| `architecture-md.template.md` | ARCHITECTURE.md structure |
| `dir-claude-md.template.md` | Directory manifest structure |
| `file-header.template.md` | YAML front matter examples |
| `progress-yaml.template.md` | progress.yaml intake funnel format |
| `review-report.template.md` | Review report structure |

## Key Principles

1. **Soft enforcement**: Warnings, never blocks. Developer retains agency.
2. **Scope graduation**: Root docs = human-managed. Directory docs = AI-managed.
3. **Three-tier review**: Deterministic → cross-LLM → self-review fallback.
4. **progress.yaml as intake funnel**: All discoveries go here first, then promoted.
5. **Proposal-only for root**: Compaction proposes, human approves.
