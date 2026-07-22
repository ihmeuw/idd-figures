---
from_repo: idd-tc-mortality
date: 2026-07-22
slug: association-aware-point-labeling
category: feature-request
priority: medium
---

## Summary
idd-figures needs a point-labeling utility that guarantees both (a) no overlap with
other labels, scatter points, or axes edges AND (b) unambiguous label-to-point
association — the existing automatic placers (adjustText, textalloc) optimize only (a)
and produced a label sitting closer to the *wrong* point on a real figure.

## Context
Figure A in `idd-tc-mortality/notebooks/20260722/heavy_tail_simple_and_real.ipynb`:
a two-panel scatter (deaths vs wind speed, deaths vs SDI; symlog y) with two
highlighted "giant" storms per panel (2008 Nargis, 1991 Bangladesh/Gorky) sitting at
the very top of each panel, each needing a text label. Six placement approaches were
tried in one session; every one failed on at least one panel.

## Details
What was tried, and how each failed:

1. **Fixed manual offsets** (`annotate` with constant `xytext`): labels overlapped
   each other when the two points sat close in x (SDI panel: 0.31 vs 0.51 with a
   22-character label).
2. **adjustText, default config**: only repels labels from *point coordinates*, not
   marker extents — labels sat on top of the s=150 markers.
3. **adjustText with `objects=` (marker artists as obstacles)**: repulsion pushed
   labels outside their axes (annotations are not clipped), where the two panels'
   labels collided in the wspace gap between subplots.
4. **Deterministic outward left/right rule**: same cross-panel overflow failure.
5. **Hand-rolled measured-extent greedy** (place at preferred offset after
   `tight_layout`, measure `get_window_extent`, drop a colliding label one 13-pt row
   until clear): correct output — every label under its own marker, no overlap — but
   it's a repo-local snippet with a single escape direction, not a reusable tool.
6. **textalloc 1.2.3** (candidate-scan placer; scatter obstacles + sizes passed;
   allocation run after `tight_layout`): no overlaps, but it placed Gorky's label
   nearer to Nargis's marker than to Gorky's in *both* panels — silently wrong
   association, which is worse than overlap. Notably it looked fine on a synthetic
   replica of the same layout, so per-dataset behavior is unpredictable.

Root cause for 2/3/6: these tools' cost functions contain "find a legal box, prefer
close to my point" but nothing that says "and NOT close to anyone else's point."
With a few isolated markers surrounded by empty space there are hundreds of legal
positions, and nothing stops the scan from picking one in another marker's
neighborhood.

## Suggested fix (optional)
Something like `idd_figures.lib.label_points(ax, x, y, labels, ...)`:

- Runs after final layout (caller responsibility, or force a draw internally) and
  measures real text extents via the renderer — no width heuristics.
- Generates candidate offsets per point (below, above, left, right, diagonals ×
  increasing distance rows), tried in order of proximity to the owning point.
- **Association as a hard constraint**: reject any candidate whose box center is
  closer to a different labeled point than to its own (equivalently: candidates must
  stay inside the owning point's Voronoi cell). This is the term the libraries lack.
- Obstacles: previously placed labels, scatter points with their marker sizes, axes
  bounding box (labels must stay inside their own axes).
- Optional leader line when the accepted candidate is beyond some distance threshold.
- Deterministic given inputs; N is small (2–10 highlighted points) so brute force is
  fine.

The measured-extent greedy from failure-mode 5 is a working starting skeleton; it
needs the multi-direction candidate set and the association constraint generalized.
