# Review Report Template (v2)

> Generated when a developer proposes a feature change. Claude analyzes impact, developer decides.
> Saved to `review/{topic}_{timestamp}.md`. Remains in write layer as compaction input.

## Template

```markdown
---
report_id: {topic}_{timestamp}
topic: {topic}
created_at: {YYYY-MM-DD}
requester: {developer}
status: pending_review  # pending_review | approved | rejected | superseded
change_type: feature    # feature | refactor | migration | bugfix | api_change
risk_level: medium      # low | medium | high
confidence: 0.8         # 0.0-1.0, AI self-assessment of analysis quality
modules_affected: 2
files_affected: 4
---

# Review: {topic}

## 1. Change Summary

{1-3 sentences describing what the developer wants to change and why.}

## 2. Impact Map

| File | Module | Current Role | Expected Change | Dependency Direction |
|------|--------|-------------|-----------------|----------------------|
| {path} | {module} | {current role} | {what changes} | {modified/upstream/downstream} |

**Cross-module dependencies touched:** {list or "none"}

Dependency edges:
- {file_a} → {file_b} ({relationship})

## 3. Effort and Risk

**Complexity signals:**
- Lines of code estimated: {range}
- New dependencies introduced: {list or "none"}
- Breaking changes to existing interfaces: {yes/no, details}
- Test coverage impact: {new tests needed, existing tests affected}

**Risk rationale:** {1-2 sentences explaining the risk assessment}

## 4. Constraints from Prior Execution

{Relevant entries from progress.yaml, if any. Otherwise: "No known constraints."}

## 5. Assumptions and Open Questions

**Assumptions made by this analysis:**
- {assumption}

**Questions requiring human decision:**
- {question}

## 6. Suggested Approach

{Claude's recommended implementation strategy. Advisory only.}

**Alternatives considered** (max 2):

| Approach | Trade-off | Why not default |
|----------|-----------|-----------------|
| {alt} | {pro vs con} | {reason} |

## 7. Post-Change Maintenance

**Required updates:**
- Directory CLAUDE.md: {list of paths}
- File headers: {list of paths}

**Possibly affected (review needed):**
- ARCHITECTURE.md: {yes/no, what section}
- Root CLAUDE.md: {yes/no, what rule}

## 8. Decision

> Filled by reviewer after reading this report.

**Decision:** pending
**Reviewer:** {name}
**Date:** {YYYY-MM-DD}
**Notes:** {conditions, modifications, or rejection reason}
```

## Front Matter Enums

| Field | Values |
|-------|--------|
| `status` | `pending_review` / `approved` / `rejected` / `superseded` |
| `change_type` | `feature` / `refactor` / `migration` / `bugfix` / `api_change` |
| `risk_level` | `low` / `medium` / `high` |
| `confidence` | `0.0` – `1.0` (float) |

## Lifecycle

1. Claude generates report → saves to `review/{topic}_{timestamp}.md`
2. Developer reviews — checks assumptions, answers open questions, evaluates risk
3. Developer fills Decision block (approved/rejected + notes)
4. If approved: Claude executes, updates directory CLAUDE.md + file headers
5. Report remains in write layer as compaction input and decision audit trail
