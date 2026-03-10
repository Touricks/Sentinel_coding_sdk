# Contributing to Sentinel-Coding

Thank you for your interest in contributing!

## Prerequisites

- Python 3.11+
- Git
- [Claude Code](https://claude.ai/code)
- (Optional) [Codex CLI](https://github.com/openai/codex) for `/call-codex`
- (Optional) [GitHub CLI](https://cli.github.com/) for `/submit-issue`

## Ways to Contribute

### Adding a New Skill

1. Create `.claude/skills/{skill-name}/SKILL.md`
2. Use existing skills as reference (e.g., `.claude/skills/start/SKILL.md`)
3. Required YAML front matter fields: `name`, `description`
4. Include: Overview, Workflow (numbered steps), Anti-patterns

### Extending Templates

Templates live in `.sentinel/templates/`. Each follows the `{purpose}.template.md` naming convention. See existing templates for format reference.

Available templates:
- `root-claude-md.template.md` — Root CLAUDE.md structure
- `architecture-md.template.md` — ARCHITECTURE.md layout
- `dir-claude-md.template.md` — Directory manifest
- `file-header.template.md` — YAML front matter
- `progress-yaml.template.md` — Session log format
- `review-report.template.md` — Review output format
- `compliance-report.template.md` — Compliance lint report

### Contributing Compliance Rules

The compliance engine lives at `.sentinel/export/compliance.py`. It detects 4 types of AI writing patterns:

- **T1**: Chain-of-thought leaks
- **T2**: Structural tells (AI vocabulary, em dashes, emoji)
- **T3**: Phantom references (missing figures/tables)
- **T4**: Statistical fingerprint (opt-in)

To add a new check, follow the existing pattern: each check function receives `(text, regions)` and returns `list[ComplianceFinding]`.

## Code Style

- Python 3.11+ features encouraged (`StrEnum`, type unions)
- Type hints required for function signatures
- Use `dataclasses` for structured data
- YAML front matter headers on Python files (`input`, `output`, `pos`, `last_modified`)

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Run compliance lint on documentation changes
4. Ensure pre-commit hooks pass (they warn but never block)
5. Update both `README.md` and `README-EN.md` if your change is user-facing
6. Update `CHANGELOG.md`
7. Submit PR using the provided template

## Reporting Issues

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) for bugs and the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md) for enhancements. If you are using Sentinel in Claude Code, you can also run `/submit-issue` to file an issue directly from your development session.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
