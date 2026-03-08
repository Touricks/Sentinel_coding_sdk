# Directory CLAUDE.md Template

> AI-managed, descriptive manifest. ≤3 lines of context + file manifest table.
> Updated automatically when files in the directory change (chain-trigger §4.4).

## Usage

Replace `{placeholders}` with directory-specific values. Remove this usage section after instantiation.

## Template

```markdown
# {directory_name}/

{1-3 lines describing the module's purpose and architectural role.}

| File | Role | Status |
|------|------|--------|
| {filename} | {what this file does} | {active/planned/deprecated} |
```

## Constraints
- Maximum 3 lines of context before the table
- Table must include ALL files in the directory (no omissions)
- Table must exclude deleted files (no stale entries)
- Status values: `active` (in use), `planned` (not yet implemented), `deprecated` (scheduled for removal)
- Updated by chain-trigger propagation when files change
- Changes propagate upward: directory manifest → root notification
