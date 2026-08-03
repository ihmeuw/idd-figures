---
kind: handoff
to: idd-lsae-hdi Claude Code session
from: idd-figures (Bobby delivers this; phase 4 of the integration process)
date: 2026-08-02
gate: answer the four questions in section 7 BEFORE changing any code
---

# idd-lsae-hdi → idd-figures: figure-layer swap (phase 5 work order)

Your orientation letter was read, and every claim in it was independently
verified against both codebases. Most of it held up; some of it didn't —
section 5 lists the corrections that change your own §9 bug list. Everything
your §8 asked idd-figures for now exists (section 3). The goal, per Bobby:
**maximal swap** — general figure machinery comes from `idd_figures`; only
genuinely repo-specific pieces stay local (section 4's KEEP list). Not a 100%
hard rule, but the default is: if the library has it, you call it.

## 1. Prerequisites — in this order, before any swap

1. **Commit your untracked figure layer.** `lib/render/`, `04_manuscript/`,
   `lib/figures/{spec_maps,spec_histograms,anatomy,interactive}.py`,
   `normalize_specs.py`, and their tests are untracked. There is no baseline
   to diff the migration against and no rollback until this is committed.
2. **Fix your B3 before touching save discipline:** your bottom colorbar is
   drawn partly OUTSIDE the figure canvas (colorbar_axes places it below
   `BOTTOM = 0.04`) and only survives because `bbox_inches="tight"` crops to
   ink. If you adopt `save_figure` (which enforces `bbox_inches=None`) before
   fixing that, the bar text vanishes. Fix the geometry, then switch saves.
3. Then adopt `idd_figures.lib.io.save_figure` everywhere `_save`/direct
   `savefig` lives today — and note three deltas: add `plt.close(fig)` in your
   render loops (save_figure doesn't close; your loops emit 8-14 figures);
   PNG dpi default becomes 360 (yours was 200) — pass `dpi=200` if you want
   parity; there is no `facecolor="white"` pin (the figure's own facecolor is
   used).

## 2. What the swap gets you (new in idd-figures, built for this)

- **`layouts.maps.map_facet`** — rows of fixed-aspect map panels with group
  colorbars as GRID CELLS (spanning the panels they serve), derived row
  heights (`layouts.geometry`), explicit title-allowance gaps (never implicit
  slack), per-row `cbar_h`/`cbar_band` knobs, auto-named axes returned via
  `fig.axes_by_name`.
- **Explicit aspect + guard** — `set_aspect("auto")` is gone; a margins/hspace
  value that breaks a map's derived box RAISES instead of silently stretching.
- **Preview** — `map_facet(preview=True)`/`map_panel(draw_data=False)` skip
  data draws and Natural Earth, bar layout is identical (mappables are built
  from declared cmap/norm, never harvested from `ax.collections[0]`), and
  `save_figure` auto-suffixes `_preview` so a draft can NEVER overwrite a
  final. Use the simplified shapefiles for iteration, always.
- **Your palette is now the library's**: `palettes.GBD_SUPER_REGION_COLORS`
  carries YOUR `SR_COLORS` hexes (as hex strings), plus `GREY`/`MED_DARK`/
  `MED_LIGHT`. Delete `palettes.py` locally and import.
- **`colors.clipped_diverging_cmap(name, lo=, hi=)`** — your continuous
  split-middle ramp, `lo`/`hi` as FRACTIONS (your `96/160` of 256 = the
  defaults `0.375/0.625`); off-centre cuts raise.
- **`numbers.compact()`** — your `_tick_label` (k-notation), plus an M tier
  and negative-value handling.
- Also relevant: `binned_colormap(remove_middle=)` is now symmetric by
  construction (odd bin counts get a white centre + one colour dropped per
  side); `bin_legend_panel` takes `cbar_label=`.

## 3. The swap table

| Yours | Becomes |
|---|---|
| geometry kit: `gap_factor`, `map_figsize`, `map_height_ratios`, `map_extent`, `map_aspect`, `colorbar_axes`, `log_colorbar`/`plain_colorbar` placement, `outline_axes`, `pin_extent` | DELETE → `idd_figures.lib.layouts.geometry` + the engine (`show_anatomy` is the richer `outline_axes`) |
| `figure_maps_indices` (4 panels / 1 bar), `figure_maps_data_to_hdi` (7 panels / 4 bars) | config over `map_facet` (rows= dicts; see section 6) |
| `anatomy_figure` (3-row mixed composite) | a `panel_grid` spec (mixed map/plot/legend cells are the engine's native mode). Rename YOUR module in the process — `transform_anatomy` or similar; `idd_figures` keeps `anatomy` for the layout debugger |
| `style.size_by_logpop`, `style.signed_diverging_cmap`, `style.clipped_diverging_cmap`, `palettes.SR_COLORS`/greys, `_tick_label` | DELETE → `lib.style`, `lib.colors`, `lib.palettes`, `lib.numbers.compact` |
| `render/spec_figures._save` + the 5 other `bbox_inches="tight"` save sites | `lib.io.save_figure` (after section 1.2-1.3) |
| `render/spec_figures._draw_map` (render-local map painter, `fraction=` colorbar) | `lib.painters.maps.map_cell_painter` + a bar cell (your own module banner already bans `fraction=` — this closes the violation) |
| KEEP local | spec system + `AROC_LIMITS`, transforms, `ARTIFACT_LOCATION_IDS`, `AnalysisData`/`INDICATORS` contracts, `interactive.py` (plotly), `reports.py`, your tuning constants |

## 4. Contract details the swap must preserve or replace

- Your render layer reaches into figures by POSITION in several places
  (`ax.collections[0]`, `fig.axes[0]`/`[1]`, `fig.legends[0]`, hard-wired
  `GridSpec(3, 4)` row logic). Library figures return `fig.axes_by_name`
  (e.g. `map:r0c1`, `cbar:r0`) — replace positional digs with names.
- `START_YEAR/END_YEAR = 2000/2023` is declared in ~9 places across your seam
  and relied on as matching library-side defaults. Pick ONE owner
  (constants.py) and pass years explicitly at call sites.
- Module-constant reach-ins that must survive the transition byte-for-byte
  until each call site migrates: `LEVEL_CMAP_NAME(_REVERSED)`,
  `ARTIFACT_LOCATION_IDS` (implicit via `mask_artifacts` default),
  `clipped_diverging_cmap` defaults, `anatomy.DIMENSIONS`,
  `HEALTH_TRANSFORMS` (a CLI-visible choice set).

## 5. Corrections to your letter (your §9 needs these edits)

- Your bug 1 (shared_legend/colorbar collision) is ALREADY FIXED in your own
  tree — `anatomy.py` passes an explicit `y` and `anatomy_bottom` reserves the
  band, with a rendering regression test. Drop it.
- Real bugs your letter missed, worth fixing or absorbing into the swap:
  (a) `map_figsize` leaks ~86% of `COLORBAR_HEIGHT` back into map rows
  (+6-8% dead band per row); your own `anatomy_layout` has the correct
  height-dependent-bottom fix. (b) `wspace` is missing from the per-row width
  math (the `(1,3)` ratios should be 3.04:1). (c) the drawn aspect is set by
  the LAST geopandas plot call (the border overlay), not the layer your
  layout measured — reorder-fragile. (d) `--health-transform log_survival`
  titles the map as U5MR on the reversed ramp (red = good survival — violates
  your own palette law); `u5m` gets decade ticks on linear limits.
  (e) viridis defaults are LIVE in production: `linked.py` calls
  `choropleth_panel` with no cmap in 3 places. (f) artifact greying is NOT on
  "every map" — none of the `linked.py` maps mask the two Algerian units.
  (g) anatomy figures are permanently `log_u5m` (`run_spec_figures` never
  passes `health_transform`) and can silently disagree with maps/histograms
  in the same output directory. (h) `aroc_limit()` silently falls back to 3.0
  on a typo'd spec — make it raise.
- Titles in your multi-panel figures currently clear the map ink only by
  consuming bug (a)'s dead band. The library reserves title clearance
  explicitly (`panel_title_h`) — do not "fix" (a) locally without adding
  clearance, and don't be surprised that library figures are slightly taller
  for the same content.

## 6. Working style + validation

- Start from `map_facet`: your `figure_maps_indices` is literally
  `rows=[{1 panel, no bar}, {3 panels, shared bar}]`; `figure_maps_data_to_hdi`
  is `rows=[{3 panels, cbar "each"}, {3 panels, no bar}, {1 panel, shared}]`.
  Keep your loaders in `render/` (data prep is the caller's job — a painter
  never loads); pass prepared GeoDataFrames in the panel dicts.
- **Acceptance fixtures are your own current outputs.** For each spec: render
  before and after, compare figure-by-figure. Bobby reviews visual diffs, not
  code diffs. Keep the CLI surface (`--spec/--group/--preview/--full`) stable.
- Migrate one render group per commit; your CLIs must render after every
  commit.

## 7. Answer these BEFORE starting (send answers to Bobby)

1. Your `anatomy.py` collides with the library's `layouts/anatomy.py`
   debugger. What will you rename yours to, and what does the split
   "painter/layout vs published-figure module" mean for where its code lands?
2. Why must your B3 (off-canvas colorbar) be fixed BEFORE adopting
   `save_figure` — what specifically breaks if the order is reversed?
3. The library will NOT port your geometry kit even though its math is
   verified correct. Why is deletion-and-reimplementation the ruling rather
   than porting, and which of your kit's lessons DID transfer (name three)?
4. "A painter never loads data." Your `load_spec_map_frames` and
   `make_figures`/`make_map_figures` live in `lib/figures/` and read
   netCDF/parquet and write files. Where does each responsibility go after
   the swap, and what does that leave inside `lib/figures/`?

Answers that show these four are understood = green light for phase 5.
