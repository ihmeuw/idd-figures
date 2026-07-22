# idd-figures feedback inbox

Consumer Claude sessions write feedback here during normal workflow sessions.
Bobby processes it at the start of an idd-figures session.

## How to submit (consumer sessions)

Write a file named `YYYY-MM-DD_<repo-slug>_<slug>.md` in this directory.
Commit and push it (or open a PR). The maintainer will triage it.

Example filename: `2026-07-22_idd-tc-mortality_association-aware-point-labeling.md`

### Required frontmatter

```yaml
---
from_repo: idd-tc-mortality
date: 2026-07-22
slug: association-aware-point-labeling
category: bug | feature-request | question | usage-pattern
priority: high | medium | low
---
```

### Body

```markdown
## Summary
One sentence.

## Context
What were you trying to do? Which idd-figures feature (or gap)? Code snippet or call site.

## Details
Error messages, unexpected behavior, concrete reproduction steps.

## Suggested fix (optional)
Specific suggestion if you have one.
```

## Rules

- Do not write to `inbox/processed/` — that directory is managed by the maintainer's triage.
- Do not edit files already in `inbox/processed/`.
- One issue per file. If you have two unrelated issues, write two files.
