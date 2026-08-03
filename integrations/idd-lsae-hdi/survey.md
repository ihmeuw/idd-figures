---
kind: survey
repo: idd-lsae-hdi
date: 2026-08-02
phase: 2 — independent verification of the orientation letter
letter: inbox/orientation/idd-lsae-hdi.md (2026-07-28)
sources: 5 read-only agent surveys, this session (4 over their repo, 1 over ours)
status: complete
---

# idd-lsae-hdi — independent survey

Their paths below: `T:` = `idd-lsae-hdi/src/idd_lsae_hdi/`. Ours: `O:` = `idd-figures/src/idd_figures/`.

## 0. Bottom line

The letter is **structurally honest but systematically optimistic**. Its module
lists, mechanisms, and its characterizations of *our* code check out far more
often than not (7 of 10 equivalence rows accurate, including the unflattering
ones). Its errors all lean one way: **overstating absorbability** — of their kit
(which has 13 undisclosed defects), of our coverage (two claimed counterparts
aren't), and of their own discipline (their painter/layout contract is violated
more widely than admitted). One §9 "open bug" is stale (already fixed, with a
regression test), one citation is fabricated ("your survey" — no such document
exists), and **roughly half the figure layer the letter describes is untracked
in git** — there is no committed baseline for the code we'd be replacing.

Bobby's priors, scored: mistrust of the letter → justified, in the predicted
direction. "We already have map_facet or are close" → half right: the engine
skeleton is genuinely there (per-cell projection, spanning cells, a Colorbar
node); the geometry math that makes multi-panel maps *correct* is entirely
absent, and 4-subset colorbars are inexpressible today (§5).

## 1. Decisions needed from Bobby

1. **Super-region palette.** 7/7 name→hex mismatches between their `SR_COLORS`
   and our `GBD_SUPER_REGION_COLORS`. Theirs is hand-chosen with semantics
   (High-income = recessive grey; Sub-Saharan Africa = blue); ours is a
   positional Dark2 assignment we self-document as provisional (`O:
   lib/palettes.py:69-72`). Recommendation: adopt their hex set as the house
   palette (as hex strings — ours are RGB tuples today, a type mismatch that
   breaks plotly/HTML use). Also adopt their `GREY`/`MED_DARK`/`MED_LIGHT`
   companion constants (we have no equivalent).
2. **map_facet scope.** Approve building §5's minimal additions in idd-figures
   (geometry module + union colorbar + map_facet layout). This is the
   load-bearing prep item; everything else is small.
3. **Their uncommitted code.** `lib/render/`, `04_manuscript/`, and 4 of the 12
   figure modules (spec_maps, spec_histograms, anatomy, interactive) + their
   tests are untracked. Precondition for any swap: they commit first. Belongs
   in the handoff prompt as a hard prerequisite.
4. **bbox_inches switch ordering.** Their §7.1 offer to adopt our
   `bbox_inches=None` rule will immediately expose their B3 bug (bottom
   colorbar drawn *outside* the canvas, rescued only by tight-crop). The
   handoff must sequence: fix B3 → then switch save discipline.

## 2. Letter scorecard

| Area | Verdict |
|---|---|
| Module inventory (theirs, §3) | Accurate and complete |
| Painter/layout convention claims (§2, §5) | Convention real; violations undercounted (see §7) |
| Geometry-kit math (§5.4–5.6) | Formulas verified exact (gap_factor confirmed against matplotlib source); "no hand-picked figsizes" false — height is derived *given* ~6 hand-picked constants |
| Equivalence table (§6) | 7/10 rows accurate; 3 miss in the same direction (rows 3, 6, and the §7.5 convention claim) |
| Their open bugs (§9) | Bug 1 (legend/colorbar collision) is FIXED with a regression test (`T: lib/figures/anatomy.py:293`, `tests/.../test_anatomy.py:243-251`) — stale. Viridis-default count right, override count wrong (~5 real overrides, not 27) |
| "Your survey lists these as missing" (§8) | Fabricated citation — no survey document exists in our repo or its history. The *substance* (map_facet missing) is correct. Our own `.claude/DECISIONS.md:70` overclaims the opposite ("map_panel/map_facet are shared") |
| "Rendered once, not 5×" (natural maps) | True by design, false in practice — `render_natural_*` has **no caller** anywhere; currently rendered zero times |
| "One process per group" | Misleading — default `--group all` runs all 6 groups sequentially in one process, reloading data 6× |
| "Identical name, independently written" (size_by_logpop) | Dubious — verbatim shared docstring sentence + identical magic defaults; likely copied, direction unknown |

## 3. Our library: bugs this survey found in idd-figures

Prep items regardless of lsae:

1. **`map_panel` silently distorts** when callers pass `margins=` or
   `hspace>0` — the aspect math assumes full-bleed/hspace=0 defaults
   (`O: lib/layouts/maps.py:27,56-57,81-82,129`); cartopy's
   `set_aspect("auto")` stretches instead of letterboxing; no warning, no test.
2. **`save_figure` mutates global state** — sets
   `mpl.rcParams["pdf.fonttype"]=42` and never restores (`O: lib/io.py:38-40`);
   not scoped by `rc_context`.
3. **`panel_grid` discards the named-axes registry** — `_realize` builds it,
   `panel_grid` passes a throwaway `{}` (`O: lib/layouts/grids.py:189`), so
   callers can't retrieve the "map" cell for annotation.
4. **`binned_colormap(remove_middle=)` asymmetry** — symmetric only for even n
   without `force_white_zero`, only for odd n with it; docstring claims the
   opposite case; only test checks length (`O: lib/colors.py:71-78`,
   `tests/lib/test_colors.py:52-56`).
5. **`Colorbar` grid node has zero tests or examples** (`O: grids.py:59-62,175-176`).
6. **`Cell.projection` typed `str | None`** but receives a `ccrs.CRS`
   (`O: grids.py:75` vs `lib/layouts/maps.py:111`).
7. **Nested grids silently drop `margins`** (`O: grids.py:87,134-138`).
8. **`facet_grid` cannot produce GeoAxes** — no `projection` parameter
   (`O: grids.py:193-209,243-247,263-267`).
9. **`.claude/DECISIONS.md:70` overclaims** map_facet is "shared" — code says
   "comes next" (`O: lib/layouts/maps.py:9`).
10. **`plot_composition` is a layout squatting in `painters/`** — no `ax=`,
    creates Figure + colorbar, returns Figure (`O: lib/painters/composition.py:49-62`).
    The one genuine instance of the wart their §7.5 accuses us of broadly.
11. **`draw_data=False` is an incomplete fast path** — still draws the basemap
    (potential Natural Earth network fetch on first use); returns nothing
    usable for colorbar layout; no `_preview` filename interlock, so a draft
    save can overwrite a final.

## 4. Our library: capability gaps confirmed (build list)

- **Continuous split-middle diverging ramp** — nothing in `O: lib/colors.py`
  can express it; their `clipped_diverging_cmap(name, lo, hi)` is the real
  thing. Absorb with `lo/hi` as *fractions*, not indices into a 256 sample.
- **Multi-panel map geometry + shared colorbars** — §5.
- **Dated figure dirs** — their `dated_figure_dir(node, stamp, root=)` has no
  equivalent here; contributable in root-injected form only (their default
  reads an absolute-path constant; we're public).
- **Scalar k-notation tick formatter** — their `_tick_label` has no drop-in
  here (`map_bin_labels` is range-over-edges; `smart_ui_format` is Lancet
  style). Either add a scalar `compact()` to `numbers.py` or leave theirs local.
- **Median-marker neutrals** — their `GREY`/`MED_DARK`/`MED_LIGHT`; we have none.
- **Decline:** `reports.as_table` (markdown tables) — not a figure concern;
  route to idd-tools if it needs a home.

## 5. map_facet: what exists, what's missing, minimal additions

**Exists today (engine skeleton):** per-cell projection via
`Cell.projection` → `fig.add_subplot(sub, projection=…)` (proven by map_panel
with a live CRS); row/column spanning via slices; nested grids sharing a name
registry; a one-cell `Colorbar` node; one hand-built spanning-legend precedent
(`O: lib/examples.py:194`). A 4-panel/1-bar figure is hand-buildable now if the
caller does all geometry themselves — nothing helps, nothing warns.

**Missing (the actual feature):**
- Aspect-derived row heights beyond single-column/full-bleed/hspace=0 (the only
  aspect math is two lines inside map_panel, valid only at its own defaults).
- Gap accounting — matplotlib charges hspace/wspace against *average* axes
  size; nothing compensates (this is precisely their letter's "rows
  under-allocated 20–27%" failure, and their `gap_factor` fix is exact — the
  formula was verified against matplotlib's gridspec source).
- Colorbar over a panel *union* — no `fig.add_axes` anywhere in `src/`; the
  Colorbar node has no `over=`; `_realize` is single-pass with no post-layout
  hook. The 7-panel/4-bar figure's subset bars are **inexpressible** today.

**Proposed minimal additions** (fresh implementations, informed by their
lessons; NOT ports — their kit's code stays theirs per Bobby's ruling):
1. `lib/layouts/geometry.py`: `gap_factor(n, space)`; `map_aspect(extent, *,
   squeeze=1.0)` (squeeze=1 for cartopy; the 1/cos(lat) term is geopandas-only
   and does not transfer); `panel_width(fig_width, margins, ncols, wspace)`
   (wspace-aware — their kit omits wspace, a defect we won't copy);
   `row_height`; `solve_figsize(rows, …)` reserving colorbar/legend bands as
   height-dependent bottom margin — the *anatomy_layout* pattern, not the
   `map_figsize` additive term that leaks 6–8% dead band (their B1).
2. `place_colorbar(fig, mappable, over=[axes], where="below", …)` — standalone
   `Bbox.union` + `add_axes`, width clamped to the served union. Still explicit
   figure-coordinate geometry, so it doesn't violate our no-tight rule.
3. `map_facet(rows=[{panels, extent, cbar_group}], …)` in `lib/layouts/maps.py`,
   built on 1+2, passing `projection=` per cell; requires extracting map_panel's
   private `_draw_map` closure into a public painter.
4. `facet_grid(..., projection=None)` threaded into cell creation; refuse
   sharex/sharey under a projection.
5. Aspect guard: warn when a fixed-aspect cell's realized box aspect diverges;
   extend `show_anatomy` to draw the intended content box.
6. Fix §3 items 1–3 first — they're the same defect class the multi-panel work
   hits at scale.

**Porting trap (from their B6):** any correct reimplementation must budget
title clearance explicitly — their current figures clear only by consuming the
dead-band slack their own bug creates. Fixing the over-allocation without
raising inter-row gaps produces collisions.

## 6. Their kit: what to learn vs leave

**Absorb the lesson (engine-agnostic, verified exact):** gap_factor algebra;
explicit gridspec margins (matplotlib's defaults waste 22.5% width); derive
height from width given content aspect; union-clamped explicit-box colorbars
placed below (never `fraction=`/`shrink` — `shrink` is literally clamped to 1.0
and does nothing); preview mode returning a stand-in `ScalarMappable` so
colorbar layout is identical in fast drafts; `_preview` filename interlock;
constants-read-in-bodies (their §5.6 %autoreload rule — and note their warning:
a library that factors "self-contained on purpose" functions into helpers
breaks the live-notebook workflow that rule protects); clipping annotations on
windowed histograms; medians on unwindowed arrays; fail-loud categorical color
mapping.

**Leave (geopandas- or repo-specific):** the 1/cos(lat̄) aspect squeeze; the
2.507 constant; `ax.collections[0]` mappable harvesting (unguarded, ordering-
dependent); `RAW_PANELS` hard-coded transform metadata; `map_figsize`'s
additive colorbar term (B1); their `--health-transform` plumbing (B4).

## 7. Their kit: undisclosed defects (correct their §9 in the handoff)

The handoff prompt should replace their §9 bug list with this one — theirs is
both stale (bug 1 fixed) and incomplete:

- **B1** `map_figsize` leaks ~86% of `COLORBAR_HEIGHT` back into panel rows →
  +6.1% dead band per row (indices layout), +7.8% (data→HDI layout). Their
  sibling `anatomy_layout` already implements the correct fix; the letter never
  names it.
- **B2** `wspace` omitted from per-row width math — multi-column rows ~1.3%
  further off; correct (1,3) ratios are 3.04:1, their test asserts 3:1.
- **B3** bottom colorbar text drawn at negative figure coords; rescued only by
  `bbox_inches="tight"`. Gates the §7.1 save-discipline switch.
- **B4** `--health-transform log_survival` yields a survival map titled as U5MR
  on the reversed ramp — red = good, violating their own palette law;
  `u5m` gets decade ticks on linear clim. Histograms handle it correctly; maps
  hard-code.
- **B5** the drawn aspect is set by the *last* geopandas plot call (the border
  overlay), not the layer the layout math measured — delete/reorder the overlay
  and layout silently diverges; preview and full modes can disagree.
- **B6** no title allowance in gap math — titles clear only via B1's slack.
- **Two-constant wart re-created across modules** — `CBAR_WIDTH` vs
  `CBAR_WIDTH_SHARE`, `CBAR_HEIGHT` vs `CBAR_THICKNESS` (spec_maps vs anatomy);
  the letter's "shipped twice" history is also uncorroborated — those names
  never existed in committed history.
- **B8** tick-label algorithm duplicated verbatim (spec_maps re-implements
  spec_histograms' decade_ticks while importing from it).
- **§5.6 rule violated 12×** in their own layer (3 in the named modules), incl.
  constants bound as default args; regression tests cover only CBAR_WIDTH, and
  only 3 of the 4 "deleted names stay deleted".
- **Viridis is live in production paths** — `linked.py:70,385,388` call
  choropleth_panel with no cmap → those maps render viridis today.
- **Artifact greying is NOT "on every map"** — only the spec_maps/_draw_map
  paths mask; every linked.py map shows the two Algerian units un-greyed.
- **Anatomy figures are permanently `log_u5m`** — `run_spec_figures` doesn't
  expose `--health-transform`, so anatomy can silently disagree with maps/
  histograms in the same output dir.
- **`render/spec_figures._draw_map`** near-duplicates the library's map path
  using the `fraction=` colorbar API their own module banner rejects — 12 of
  the 29 per-spec figures are drawn by this render-local painter.
- **Contract violations beyond the letter's four:** `write_aid_explorer` writes
  files from figures/; aggregation inside figures/painters in ≥7 more places
  (map_frame, frame_from, _leaf_limits, _frame_at, aroc() inside a layout,
  _z_scores, dispersion pivot); `plt.close("all")` global side effects; hybrid
  count is 12, not 7.
- `aroc_limit()` silently falls back to 3.0 on a typo'd spec; `"current"` is an
  alias not a spec (5 specs, 6 accepted keys); figure count is 34/spec, not ~26.

## 8. Integration contract (render→figures seam)

15 symbols across 7 of their 12 figure modules; full kwargs inventory in the
render-agent report. The fragile couplings a swap must not break (or must
replace with explicit handles):

- Structural indexing into returned objects: `ax.collections[0]`,
  `fig.axes[0]`/`axes[1]`, `fig.legends[0]`, `subplots_adjust(bottom=0.30)`,
  `get_subplotspec()` row logic hard-wired to a 3×4 GridSpec.
- Module-level constant reach-ins that must survive byte-for-byte:
  `LEVEL_CMAP_NAME(_REVERSED)`, implicit `ARTIFACT_LOCATION_IDS`, implicit
  `clipped_diverging_cmap(lo=96, hi=160)` defaults, `anatomy.DIMENSIONS`,
  `HEALTH_TRANSFORMS` (a CLI-visible choice set).
- `START_YEAR/END_YEAR = 2000/2023` duplicated in ~9 places across the seam;
  render never passes years and relies on library defaults agreeing.
- Their tuning layer that survives a swap: the per-spec `AROC_LIMITS` table,
  bar/grid spacing kwargs, level limits. Everything about map-figure geometry
  and palette identity moves with the library.

## 9. Provenance warning

Untracked in their git (`??`): all of `lib/render/`, all of `04_manuscript/`,
and `lib/figures/{spec_maps,spec_histograms,anatomy,interactive}.py` + their
tests + `normalize_specs.py`. Committed baseline is `206a503`. The deepest
tests in the repo (403-line test_spec_maps, 264-line test_anatomy with real
pixel-collision assertions) are among the untracked files. **No swap starts
until this is committed** — there is no baseline to diff a migration against
and no rollback.

## 10. Handoff-prompt ingredients (phase 4 feed)

- Prerequisite: commit the untracked layer (§9).
- Correct their §9 with §7 above; retract the stale legend-collision bug.
- Sequence: fix B3 → adopt `save_figure` (+ add `plt.close` in their loops;
  note DPI default change 200→360 png and the facecolor pin they lose).
- Their §8 "what we need from you" answers: map_facet = we build fresh (§5),
  their kit stays local until deletion; palette = pending Bobby (§1.1);
  config surface = None-sentinel + width-multiplier sizing honored in the new
  geometry module; continuous split ramp = we absorb clipped_diverging_cmap
  semantics as fractions.
- Comprehension-check questions (draft in phase 4): the anatomy-name collision
  resolution; why bbox_inches switch is sequenced after B3; why their
  geometry kit is deleted rather than ported; what "painter never loads data"
  means for load_spec_map_frames/make_figures placement.
