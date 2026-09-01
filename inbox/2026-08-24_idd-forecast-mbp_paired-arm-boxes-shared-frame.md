---
from_repo: idd-forecast-mbp
date: 2026-08-24
slug: paired-arm-boxes-shared-frame
category: feature-request
priority: low
---

## Summary
Two small generalisations of the existing `painters/bars.py` would have covered a
scenario-comparison panel we hand-rolled: (a) let the paired-within-category axis
be an arbitrary two-level *arm* column rather than hardcoded `years=(y0, y1)`, and
(b) offer a full five-number box (quartiles, 1.5xIQR whiskers, fliers) as an
alternative mark to the current lo/hi/med/mean bar. Separately, a layout helper for
two adjacent panels that share an edge with y-axes on the outside.

## Context
`idd-forecast-mbp` malaria vaccine impact figures
(`src/idd_forecast_mbp/08_visualization/plot_vaccine_impact.py`, output in
`07-figures/20260824_vaccine_impact/`). Each figure has a column showing, per RCP
scenario, the cumulative burden through 2100 under two arms side by side, then the
cumulative difference in an adjacent panel. Distributions are 100 forecast draws.

We did **not** use idd-figures here (it is not currently a dependency of this repo),
and most of what we wrote duplicates things you already have — `lib/numbers.py`
(`count_scale`, `smart_ui_format`) in particular would have saved us two separate
tick-formatting bugs. This note is only about the part that looked genuinely absent
after checking `painters/` and `layouts/`.

## Details

**What already exists and nearly fits.** `painters/bars.py::range_bars_panel`
already draws paired marks within each category, offset by `bar_width/2`, with
`lo/hi/med/mean` and optional jittered dots. That is most of the pattern.

**Gap 1 — the pairing dimension is hardcoded to year.** It pivots on
`values=["lo","hi","med","mean"]` by `year_id` and takes `years=(y0, y1)`, drawing
at `x[i] ± off`. Our pairing is a scenario *arm*, not two years:

- no-vaccine vs with-vaccine
- VE variant A vs VE variant B
- projected product rollout vs a counterfactual rollout

Generalising `years=(y0,y1)` to something like `arm_col=` + `arms=(a, b)` (year
remaining one valid choice of `arm_col`) would make the existing painter cover all
of these without new drawing code.

**Gap 2 — five-number box as an alternative mark.** We needed quartiles, 1.5xIQR
whiskers and fliers because the audience reads the box shape, not just the interval.
`_draw_bar` gives lo/hi/med/mean. A `mark="box"` option alongside `mark="bar"`,
sharing the same grouping/offset/colour machinery, would cover it.

**Gap 3 (layout, not painter) — shared-frame adjacent panels.** We wanted
"levels" and "difference" as two panels that touch, sharing one internal edge, with
the left panel's y-axis on the left and the right panel's on the right — because the
two quantities are on very different scales (14-18B cumulative cases vs 1.45-1.75B
averted) and cannot share a y-axis, but belong visually together. We did this with
`gs[row, 3].subgridspec(1, 2, wspace=0.0)` plus `ax.yaxis.tick_right()`. Nothing in
`layouts/` (`grids.py`, `composition.py`, `anatomy.py`) seemed to cover it, but that
is the judgement we are least sure of.

**Colour convention we landed on**, in case it is useful: within a pair, the
reference arm is a *lightened* version of the category colour and the comparison arm
the full-strength colour (`_lighten(c, 0.78)`, blend toward white). Keeps the
category (scenario) encoded by hue and the arm by value, so a single legend of two
neutral grey patches explains the pairing without repeating the scenario names. That
also let us pull long arm names out of the panel title, which was where our text
collisions were coming from.

## How niche is this?
Gap 1 feels general — "compare two arms per category" is a common scenario-analysis
shape. Gaps 2 and 3 may well be specific to us; treat them as lower priority. We are
not blocked: the hand-rolled version works and ships. Filing so the pattern is
visible rather than because we need it.
