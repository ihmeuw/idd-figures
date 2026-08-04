---
kind: handoff-response
to: Bobby (idd-figures integration, phase 4 gate)
from: idd-lsae-hdi Claude Code session
date: 2026-08-04
re: answers to handoff.md §7 — no code changed
---

# Answers to the four §7 questions

## 1. The `anatomy.py` collision: rename and where the code lands

**Rename: `transform_anatomy.py`** (matching the module's own docstring, which
already calls it the "Transformation-anatomy figure"). The name says what the
figure is *about* — the anatomy of a goalpost/rank transform, outcome →
distribution shift → index — while the library's `layouts/anatomy.py` keeps the
generic meaning: `show_anatomy`, a diagnostic overlay that boxes panels, labels,
ticks, and margins on any finished figure. One is a published figure; the other
is a debugger you point at published figures. They must not share a name.

What the painter/layout vs published-figure split means for the module's code,
piece by piece:

- **Layout math leaves.** `anatomy_layout`, `anatomy_figsize`, and
  `anatomy_bottom` — the jointly-solved band constraints (colorbar gap + bar +
  text + legend + panel-title allowance) — are exactly the arithmetic the
  library engine makes first-class. In a `panel_grid` spec, the colorbar band,
  the legend band, and the title allowance are grid cells and explicit gaps,
  not a solved-for `hspace` and a hand-derived `bottom`. That whole block of
  the module is deleted, replaced by a declarative spec.
- **Drawing primitives leave.** The map rows stop importing `spec_maps.map_on`
  + `log_colorbar`/`plain_colorbar`/`colorbar_axes` and use
  `painters.maps.map_cell_painter` + bar cells. `outline_axes` (imported today
  for `show_boxes`) is replaced by the richer `show_anatomy`.
- **The figure definition stays, renamed.** `transform_anatomy.py` keeps what
  is genuinely this repo's: `DIMENSIONS` (a §4 contract constant — survives
  byte-for-byte), the row structure as a panel_grid config (map row / 1×2
  histogram row / map row), the histogram row's reuse of `spec_histograms.panel`
  (a repo-specific painter — the library has no reason to know about LE
  goalpost annotations or the all-years pool convention), and the tuning
  constants (`HIST_ROW_SHARE`, `BINS`, cmap choices per dimension).

Net: the renamed module becomes a *specification* of the figure — which cells,
which painters, which data keys, which ramps — with zero geometry arithmetic
left in it.

## 2. Why B3 must be fixed before adopting `save_figure`

The mechanics, from `spec_maps.py`: bottom-row map panels sit at
`BOTTOM = 0.04`. `colorbar_axes` places a bar at `union.y0 - gap - height` with
`CBAR_GAP = 0.015` and `CBAR_HEIGHT = 0.016`, so the shared bar's *box* spans
y ≈ 0.009–0.025 — technically inside the canvas, but its tick labels and axis
label hang *below* the box, i.e. below y ≈ 0.009 and past y = 0, **outside the
figure rectangle entirely** (the anatomy module measured this hang at ~0.56 in
of text; that's why it grew `anatomy_bottom`).

Today every save site uses `bbox_inches="tight"`, which recomputes the output
crop from actual *ink* extents — it silently expands the canvas to include
artists drawn outside `[0,1]×[0,1]`. That crop is the only reason the bar text
exists in the PNGs.

`save_figure` enforces `bbox_inches=None` as a hard rule (tight-cropping
defeats explicit layout — I agree with the rule). With `bbox_inches=None` the
output is exactly the declared figure rectangle. So if the saves are switched
first, everything hanging below y = 0 — the colorbar tick labels and label on
every multi-panel map figure — is clipped off. Not an error, not a warning:
the text just vanishes.

And the failure would poison the validation protocol itself: §6 says
acceptance fixtures are my *current* outputs, compared before/after. If I flip
saves before fixing the geometry, the "after" images are the clipped ones, and
the visual diff would show a spurious regression on every figure — or worse,
if fixtures got regenerated post-switch, the clipped version becomes the
baseline. Order is therefore: reserve the bar + text band inside the canvas
(the height-dependent-bottom fix `anatomy_layout`/`anatomy_bottom` already
implement — real inches converted to figure fraction at the actual height,
not a shared constant), verify against the current tight-cropped outputs,
*then* switch to `save_figure`.

## 3. Why the geometry kit dies instead of porting, and which lessons transferred

The kit's math is verified correct — but it is correct math *for the wrong
architecture*. It is post-hoc arithmetic bolted around a plain gridspec: it
predicts on the side what the gridspec will do (`map_figsize`,
`map_height_ratios`, `gap_factor`), then hangs colorbars into leftover figure
space with `fig.add_axes` after the fact (`colorbar_axes`), and relies on two
external disciplines to hold: every module sharing the same
`TOP/BOTTOM/HSPACE` constants, and `bbox_inches="tight"` sweeping up whatever
lands outside the canvas. In the library's engine those same quantities are
*inside* the layout — colorbars are grid cells spanning the panels they serve,
title clearance is an explicit allowance, row heights are derived by
`layouts.geometry` — so there is no leftover space for the kit's arithmetic to
manage. Ported, the kit would be a second geometry owner competing with the
engine: duplicated constants, two answers to "how tall is this row", and
nothing calling it. It would also import its known defects — the handoff's
(a) `COLORBAR_HEIGHT` leaking ~86% back into map rows, (b) missing `wspace` in
the per-row width math, (c) last-geopandas-plot-wins aspect. The asset was
never the functions; it was the lessons, which moved:

1. **Height is derived, never guessed.** A row of k fixed-aspect maps is
   `width/(k·aspect)` tall; hspace is measured against the *mean* axes height
   and must be costed explicitly (`gap_factor`). Hand-picked figsizes are what
   produced the dead bands. → `layouts.geometry`'s derived row heights and
   explicit gaps.
2. **The drawn aspect is a measured property of the box, not the extent
   ratio.** `map_aspect`'s discovery that GeoPandas sets
   `set_aspect(1/cos(mean lat), adjustable="box")` — 2.507, not 2.583 — is
   why the panels fit at all. The library kept the lesson and hardened it:
   explicit aspect plus a guard that RAISES when margins/hspace would break
   the derived box, instead of `set_aspect("auto")` silently stretching.
3. **Preview must lay out identically to final.** `map_on(preview=True)`
   returns a stand-in `ScalarMappable` built from the declared norm/cmap so
   colorbars construct without filling 47K polygons, and preview filenames get
   `_preview` so a draft can't overwrite a final. The library generalized
   both: mappables are *always* built from declared cmap/norm (never harvested
   from `ax.collections[0]`), and `save_figure` enforces the `_preview` suffix
   itself.

(Also transferred, beyond the asked-for three: `outline_axes` → the richer
`show_anatomy`; `pin_extent`'s kill-the-5%-margins rule; the anatomy module's
explicit panel-title allowance → `panel_title_h`.)

## 4. "A painter never loads data" — where each responsibility goes

`load_spec_map_frames` and `make_figures`/`make_map_figures` each fuse two or
three responsibilities. Unbundled:

- **Data loading and prep → `lib/render/`.** `load_spec_map_frames` (opens
  `hdi.nc` + `hdi_inputs.nc` via `constants.modeling_node_dir`, applies
  `HEALTH_TRANSFORMS`, extracts per-location frames) and the equivalent
  histogram loader calls move to the render layer — data prep is the caller's
  job. Render also owns joining frames to shapes (the `join_shapes` +
  `mask_artifacts` step inside `map_on` today), so what flows into panel dicts
  is prepared GeoDataFrames. All `constants.py` reach-ins (output roots, spec
  resolution, `START_YEAR/END_YEAR` passed explicitly per §4) live only here.
- **File writing → `lib/render/`, through `lib.io.save_figure`.** The
  `mkdir` / filename / dpi / `_preview`-suffix / `plt.close("all")` block at
  the bottom of each `make_*` function dissolves into the render group
  scripts, which call `save_figure` (with `dpi=200` for parity and an explicit
  `plt.close(fig)` per figure in the loop, since `save_figure` doesn't close).
  The manual `_preview` suffixing goes away — `save_figure` owns it. The
  `make_*` load-build-save bundles cease to exist as `lib/figures/` entry
  points; `render/spec_figures.py` keeps the stable CLI surface
  (`--spec/--group/--preview/--full`) and becomes the only place that knows
  the pipeline order load → build → save.
- **Figure assembly stays in `lib/figures/` as pure functions:** prepared
  data in → `Figure` out.

What that leaves inside `lib/figures/`: the repo-specific figure
*definitions* — `map_facet` row configs for `figure_maps_indices`
(`rows=[{1 panel, no bar}, {3 panels, shared bar}]`) and
`figure_maps_data_to_hdi`, the `panel_grid` spec in `transform_anatomy.py`,
the histogram panel painter and its conventions — plus the contract and
tuning constants (`RAW_PANELS`, `DIMENSIONS`, `INDEX_LIMITS`, `AROC_LIMITS`,
transforms, `HIST_ROW_SHARE`), and the KEEP-list modules (`interactive.py`,
spec system). No file opens, no output-path knowledge, no `savefig`: a module
in `lib/figures/` can be imported and exercised with synthetic frames in a
test without touching the filesystem — which is also what makes the
acceptance-fixture comparison in §6 clean.
