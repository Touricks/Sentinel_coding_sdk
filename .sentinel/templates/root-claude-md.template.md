# Root CLAUDE.md Template

> Human-managed, prescriptive rules only. Budget: ≤200 lines.
> This file tells the AI agent HOW to behave. Project state goes in ARCHITECTURE.md.

## Usage

Replace `{placeholders}` with project-specific values. Remove this usage section after instantiation.

## Template

```markdown
# {Project Name}

Architecture and stack: see ARCHITECTURE.md
Requirements: see PRD.md

## Rules

### Code Style
- {Language version and type annotation policy}
- {Naming conventions}
- {Dependency policy}

### Document Management
- Root CLAUDE.md (this file): human-managed, prescriptive rules only
- Directory CLAUDE.md: AI-managed, ≤3 line context + file manifest table
- File headers: YAML front matter with `input`, `output`, `pos`, `last_modified`
- ARCHITECTURE.md: pure markdown, no front matter — project state snapshot
- progress.yaml: machine-readable intake funnel (YAML schema), not a rule store

### Testing
- {Testing approach and location}

### Enforcement Philosophy
- Soft warnings, never hard blocks
- Low-confidence items flagged, not blocked
- Developer retains agency over all decisions
- Hooks always exit 0

### progress.yaml Conventions
- Typed candidates only: rule or fact (YAML format with stable IDs)
- needs_approval: true for anything that could become a permanent rule
- Scope: global / module / incident-only
- status: unprocessed → absorbed
- Archive old absorbed entries to progress-archive.yaml

## Workflow
- {Commit message format}
- {Branch strategy}
- {Review process}
```

## Constraints
- Maximum 200 lines after instantiation
- No architecture content — link to ARCHITECTURE.md instead
- No tool descriptions — those go in .claude/rules/tool-boundary.md
- Preserve human rules when AI proposes additions (append, don't overwrite)
