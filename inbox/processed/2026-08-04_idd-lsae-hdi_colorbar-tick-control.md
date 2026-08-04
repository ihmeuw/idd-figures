---
from_repo: idd-lsae-hdi
date: 2026-08-04
slug: colorbar-tick-control
category: feature-request
priority: high
---

## Summary
`map_facet` colorbar cells expose no way to pass custom tick positions/labels,
so log-scaled ramps cannot show natural-unit ticks — blocks the maps-group
swap in the idd-lsae-hdi phase-5 migration.

## Context
Phase-5 swap of the lsae map figures onto `map_facet`. Their log ramps label
the bar in natural units at 0.2 / 0.5 / 1 / 2 / 5 / 10 (legacy
`log_colorbar` did this). The engine's `_bar_content` builds the colorbar
from the declared cmap/norm but accepts no tick positions or labels, so the
bar falls back to matplotlib's default locator/formatter.

## Details
Relayed by Bobby from the lsae CC's phase-5 progress report (2026-08-04):
"no way to pass custom colorbar tick positions/labels — our log ramps need
natural-unit ticks (0.2 / 0.5 / 1 / 2 / 5 / 10), which `_bar_content` can't
express." Blocks the same swap group as the figure-title-row request
(separate note).

## Suggested fix (optional)
Explicit `ticks=` / `tick_labels=` (or a `bar_style` entry, pending the
parked style-dict ruling) threaded through the bar-cell config to the
`colorbar` call — declared values only, no automatic tick inference beyond
matplotlib's existing default when unset.

## Resolution
Built and shipped 2026-08-04 in 3863de5 (row-level cbar_ticks/cbar_tick_labels -> ticks= on bin_legend_panel; declared values only).
