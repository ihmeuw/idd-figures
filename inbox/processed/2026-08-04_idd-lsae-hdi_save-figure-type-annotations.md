---
from_repo: idd-lsae-hdi
date: 2026-08-04
slug: save-figure-type-annotations
category: bug
priority: low
---

## Summary
`io.save_figure` is unannotated even though the package ships `py.typed`, so
strict-mypy consumers flag every call site.

## Context
idd-lsae-hdi's pre-commit gate runs mypy over its render layer, which now
calls `save_figure` at five sites after the phase-5 save switch.

## Details
Relayed by Bobby from the lsae CC's phase-5 progress report (2026-08-04):
"io.save_figure is unannotated despite py.typed, so strict consumers flag
its calls." Our own mypy posture is non-strict + check_untyped_defs (by
policy, DECISIONS 2026-08-02), which is why this never fired locally —
py.typed makes the gap a consumer-facing contract issue rather than a local
style one.

## Suggested fix (optional)
Annotate `save_figure`'s signature (and any other public `io` entry points)
— no behavior change.

## Resolution
Built and shipped 2026-08-04 in 81e9f3a (io.py fully annotated; no behavior change).
