# ARCHITECTURE.md Template

> Pure markdown, no YAML front matter (Decision #6). Agent reads as natural language.
> This file describes WHAT the project IS. Behavioral rules go in CLAUDE.md.

## Usage

Replace `{placeholders}` with project-specific values. Remove this usage section after instantiation.

## Template

```markdown
# {Project Name} — Architecture

## 1. Tech Stack
- **Language**: {languages and versions}
- **Frameworks**: {frameworks or "None"}
- **External services**: {APIs, databases, tools}
- **Package manager**: {pip/npm/cargo/etc}

## 2. Module Structure

| Directory | Responsibility | Key Files |
|-----------|---------------|-----------|
| {dir/} | {what this module does} | {important files} |

## 3. Data Flow

{Describe how data moves between modules. Use ASCII diagrams for clarity.}

```
{source} → {processor} → {output}
```

## 4. Constraints
- {Technical limitations that affect architecture}
- {Performance requirements}
- {Compatibility requirements}
```

## Constraints
- Pure markdown — no YAML front matter, no structured headers
- Updated by compaction engine (periodic) and chain-trigger notifications
- Factual content only — no prescriptive rules (those belong in CLAUDE.md)
