# File Header Template

> YAML front matter for source files. Declares inputs, outputs, and position in module.
> Updated automatically when the file's code changes (chain-trigger §4.4).

## Required Keys

| Key | Description | Example |
|-----|-------------|---------|
| `input` | External dependencies: imports, parameters, accepted formats | `sqlalchemy, pydantic` |
| `output` | What this file provides: return values, exports, side effects | `UserModel, SessionFactory` |
| `pos` | Position in the module: architectural role, consumers | `data layer, consumed by auth module` |
| `last_modified` | Date of last meaningful change | `2026-03-05` |

## Examples

### Python (.py)

```python
# ---
# input: sqlalchemy, pydantic
# output: UserModel, SessionFactory
# pos: data layer, consumed by auth module
# last_modified: 2026-03-05
# ---

from sqlalchemy import create_engine
```

### TypeScript (.ts)

```typescript
// ---
// input: express, jsonwebtoken
// output: authMiddleware, validateToken
// pos: auth module, consumed by routes
// last_modified: 2026-03-05
// ---

import express from 'express';
```

### Shell (.sh)

```bash
#!/usr/bin/env bash
# ---
# input: git, staged files
# output: warnings to stderr
# pos: pre-commit hook, part of hooks suite
# last_modified: 2026-03-05
# ---
```

### Markdown (.md)

```markdown
---
input: design discussion, stakeholder feedback
output: architectural decision record
pos: write layer, consumed by compaction
last_modified: 2026-03-05
---

# Design Decision: {topic}
```

## Constraints
- Header must be the FIRST content in the file (after shebang for .sh)
- All four keys required; empty values allowed (e.g., `output: none`)
- Values are comma-separated lists or short phrases
- Updated by chain-trigger; verified by Tier 1 prechecks (schema validation)
