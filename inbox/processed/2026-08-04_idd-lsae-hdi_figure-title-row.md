---
from_repo: idd-lsae-hdi
date: 2026-08-04
slug: figure-title-row
category: feature-request
priority: high
---

## Summary
`map_facet` has no figure-level title row, so per-spec suptitles have nowhere
to live — this blocks the maps-group swap in the idd-lsae-hdi phase-5
migration.

## Context
Phase-5 swap of `figure_maps_indices` / `figure_maps_data_to_hdi` onto
`map_facet`. Each rendered spec carries a figure-level suptitle today (their
legacy save path drew it with `fig.suptitle` and `bbox_inches="tight"`
absorbed whatever space it needed). Under the engine's explicit-geometry
rules there is no slack for a suptitle to borrow: every inch is a grid cell
or a declared allowance, and `panel_title_h` only budgets per-panel titles.

## Details
Relayed by Bobby from the lsae CC's phase-5 progress report (2026-08-04):
"no figure-level title row — the per-spec suptitles have nowhere to live."
Prerequisites, B3, the save switch, and swap group 1 (style/palettes/numbers)
are all committed on their side; the maps group is blocked on this and on
colorbar tick control (separate note).

## Suggested fix (optional)
A declared title band in the grid tree — an explicit top row with an inch
allowance (house rule: an allowance, never slack), consistent with how
`panel_title_h` and the inter-row title gaps already work. Consumer passes
the title text + height; omitting it costs nothing.

## Resolution
Built and shipped 2026-08-04 in 3863de5 (map_facet title band: title/title_h/title_fontsize; spanning grid cell named "title").
