# progress.yaml Template

> Machine-readable intake funnel. Compaction engine processes typed candidates:
> rule → CLAUDE.md, fact → ARCHITECTURE.md.
> Absorbed entries archived to progress-archive.yaml.
> Human-readable session narratives live in docs/sessions/.

## Schema

```yaml
schema_version: 1
entries:
  - date: "YYYY-MM-DD"
    title: "{session title}"
    status: unprocessed       # unprocessed | absorbed
    session_report: ""        # path to docs/sessions/ report, if generated
    absorbed_to: null         # set when status → absorbed
    next_steps:               # optional, used by /sentinel-loop for task resolution
      - "{what to do next}"
    candidates:
      - id: cand-{date}-{kebab-slug}
        type: rule
        text: "{rule text}"
        scope: global         # global | module | incident-only
        confidence: high      # high | med | low
        needs_approval: true
        promotion_targets: [CLAUDE.md]
      - id: cand-{date}-{kebab-slug}
        type: fact
        text: "{fact text}"
        subsystem: "{module name}"
        confidence: med
        promotion_targets: [ARCHITECTURE.md]
```

## Candidate Types

### rule
Prescriptive rules (do X, don't do Y) discovered during execution.

| Field | Values | Description |
|-------|--------|-------------|
| scope | `global` / `module` / `incident-only` | Where this rule applies |
| confidence | `high` / `med` / `low` | How certain we are this is a real pattern |
| needs_approval | `true` / `false` | Whether human must approve before promotion |

Promotion: `global` + `high` + `needs_approval=false` → auto-add to CLAUDE.md.
All others require human approval or stay as log entries.

### fact
Factual observations about the project state.

| Field | Values | Description |
|-------|--------|-------------|
| subsystem | module name | Which part of the system this describes |
| confidence | `high` / `med` / `low` | How certain we are this is accurate |

Promotion: absorbed into ARCHITECTURE.md by compaction engine.

## Archive

When status changes to `absorbed`:
- Entry's `absorbed_to` field records the target (e.g., `CLAUDE.md#rule-name`)
- Entry moves to progress-archive.yaml during next archive cycle
- Active progress.yaml stays short and high-signal
