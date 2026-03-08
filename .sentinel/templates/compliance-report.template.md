# Compliance Report — {file_name}

Generated: {timestamp}

## Summary

| Type | Count | Auto-fixable |
|------|-------|--------------|
| Chain-of-thought (T1) | {t1_count} | 0 |
| Structural tells (T2) | {t2_count} | {t2_auto} |
| Phantom references (T3) | {t3_count} | 0 |
| Statistical (T4) | {t4_count} | 0 |

**Total:** {total} findings ({auto_fixable} auto-fixable, {human_review} need human review)

## Findings

### Type 1: Chain-of-Thought
{t1_findings}

### Type 2: Structural Tells
{t2_findings}

### Type 3: Phantom References
{t3_findings}

### Type 4: Statistical Fingerprint
{t4_findings}

## Actions

- [ ] Review suggest_fix findings and rewrite as needed
- [ ] Review human_review findings — these require structural changes
- [ ] Re-run compliance after fixes to verify
