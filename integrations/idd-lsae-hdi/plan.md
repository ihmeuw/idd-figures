---
kind: plan
repo: idd-lsae-hdi
date: 2026-08-02
phase: 3 — integration plan + map_facet design
gate: Bobby approval (design picks in §1–§2; swap mapping in §4)
feeds: prep.md (Tier B unblocks on approval), handoff.md (phase 4)
---

# Integration plan: idd-lsae-hdi → idd-figures

## 1. Design pick: colorbars and legends are grid cells, not floating boxes

**The pick.** A colorbar (or legend) serving a group of panels is a **cell in
the grid**. The cell's column span is its *footprint* — the maximum area the
solver accounts for — and how much of that footprint the bar actually fills is
an **explicit fill-fraction/inset knob** in both dimensions (the mechanism
`bin_legend_panel` already uses today). Anchored on Bobby's ruling that
bars/legends are first-class grid elements.

**Within-cell margins, settled.** Bobby is right that we can draw within-grid
margins: matplotlib merely lacks a *parameter* for it on nested grids, not the
capability. A cell's drawn content can inset via a child axes (or spacer
weights), which is our own explicit code — so cells get a library-level
`inset=`/`pad=` knob, consistent with "no automatic anything."

**What this replaces.** Two rejected alternatives:
- *lsae's mechanism* — post-layout `fig.add_axes` at coordinates computed from
  a union of panel positions. Works, but geometry lives outside the grid: the
  grid solver can't see the bar, which is exactly how lsae's B1/B3/B6 family of
  bugs happened (bar space leaking into rows, bars drawn off-canvas, titles
  clearing only by accident).
- *my earlier `place_colorbar(fig, over=[axes])` proposal* — same weakness,
  library-ified. Dropped.

**Why cells win.** All geometry stays declared and solvable (house rule); the
"clamp to served union" requirement becomes trivial (the cell *is* the span);
preview/anatomy tooling sees bars for free; no second realization pass, no new
node machinery — the engine already places spanning cells.

**Consequence.** The `Colorbar` node stays for the simple one-cell case (and
finally gets tests); group bars are painted cells: a `colorbar_panel`-style
painter (continuous mappable → inset horizontal bar; extends the existing
`bin_legend_panel` inset path) painted into a spanning cell.

## 2. map_facet specification

A builder that CONSTRUCTS a `panel_grid` spec — sugar over the node engine,
not over `facet_grid` (mixed map/plot/legend composites remain the engine's
native mode; nothing here blocks them).

```python
fig, axes_by_name = map_facet(
    rows=[
        # one dict per MAP row, in top-to-bottom order
        {
            "panels": [
                {"gdf": ..., "column": "v", "title": "HDI 2000",
                 "bins"/"cmap": ..., "vmin": ..., "vmax": ..., "name": "hdi2000"},
                ...,
            ],
            "extent": (lon0, lon1, lat0, lat1),   # per row; per-panel override allowed
            "cbar": "shared" | "each" | None,     # bar row inserted BELOW this row
            "cbar_label": ...,
        },
        ...,
    ],
    fig_width=16.0,
    projection=ccrs.PlateCarree(),                # per-row override allowed
    margins=None, wspace=0.02, hspace=None,       # hspace=None → solver picks (title allowance)
    preview=False,                                 # simplified/synthetic path + _preview suffix
    show_anatomy=False,
)
```

Construction rules:
1. **Columns**: LCM of per-row panel counts; panels span equal slices; a
   "shared" bar row spans all columns of its row group; "each" gives one bar
   cell under each panel.
2. **Heights**: from `lib/layouts/geometry.py` — per-row panel width =
   `usable_width_of(k panels, wspace)` (wspace charged per matplotlib's
   average-width rule); row height = width × extent aspect **in projected
   units**; bar rows get explicit small heights; hspace charged via
   `gap_factor`; title clearance is an explicit allowance in the solve (lsae's
   B6 lesson — never implicit slack).
3. **Aspect**: explicit — cells get `set_aspect(<derived>, adjustable="box")`;
   the painter no longer calls `set_aspect("auto")`. Correct figures are
   pixel-identical; wrong geometry letterboxes visibly AND trips a tolerance
   guard (error). Bobby's 2026-08-02 ruling; forecast-mbp's six `auto` sites
   migrate later, not the reverse.
4. **Names**: every cell auto-named (`map:r{i}c{j}` or caller's `name`,
   `cbar:r{i}`...); registry attached to the returned figure (non-breaking
   registry fix).
5. **Preview**: `preview=True` uses outline-only draws on SIMPLIFIED
   geometry — or the built-in synthetic continent fixture when no gdf is
   passed — skips Natural Earth features, returns stand-in mappables so bars
   lay out identically, and save paths get a `_preview` suffix guard.

Prerequisite refactor: extract `map_panel`'s private `_draw_map` closure into a
public painter both builders share.

## 3. Library work plan

Two tiers in `prep.md`. Tier A (the eleven ruled fixes) is unblocked now and
independent of this plan. Tier B (geometry.py, colorbar-cell painter,
map_facet, fixture, palette adoption, continuous clipped ramp) unblocks when
this plan is approved. Vignettes ("plotting options", "control all the
things") are parked pending Bobby's specs; the ocean-coastline workaround slot
waits for Bobby's example.

## 4. The lsae swap (phase 5 preview — executed by their CC via handoff.md)

| Theirs | Becomes |
|---|---|
| geometry kit (`gap_factor`, `map_figsize`, `map_height_ratios`, `colorbar_axes`, `outline_axes`, preview plumbing) | deleted → `idd_figures.lib.layouts.geometry` + engine |
| `figure_maps_indices`, `figure_maps_data_to_hdi` | config over `map_facet` (4-panel/1-bar; 7-panel/4-bar) |
| `anatomy_figure` (3-row mixed composite) | spec over `panel_grid` (mixed-mode native); renamed — "anatomy" collision resolved in their repo (`transform_anatomy` or similar; our debugger keeps the general name) |
| duplicates: `size_by_logpop`, `signed_diverging_cmap`, `clipped_diverging_cmap`, `SR_COLORS`, `_save`, `_tick_label` | library calls (`style`, `colors`, `palettes`, `io.save_figure`, `numbers.compact`) |
| `render/spec_figures._draw_map` (render-local painter, `fraction=` API) | library map painter call |
| `bbox_inches="tight"` + `facecolor="white"` habit | explicit geometry via `save_figure` — **sequenced after their B3 fix** (their bottom bars render off-canvas today and tight-crop hides it) |
| KEEP local | spec system + `AROC_LIMITS`, transforms, `ARTIFACT_LOCATION_IDS`, `AnalysisData`/`INDICATORS` contracts, `interactive.py`, `reports.py` (→ idd-tools candidate), their tuning constants |

Swap prerequisites (handoff checklist, not blockers for our build): commit
their untracked layer (half of `lib/figures/`, all of `lib/render/` +
`04_manuscript/`); fix B3; then adopt `save_figure` (adding `plt.close` in
their render loops; DPI default change 200→360 png noted).

## 5. Risks / cautions carried into the build

- **B1/B6 coupling**: any correct height solve must add explicit title
  allowance — lsae's titles clear only via their dead-band bug; a faithful
  "fix" without the allowance collides.
- **Ocean coastlines**: Natural Earth ocean's coastline ≠ IHME admin
  coastline — slivers/gaps at coasts. Pattern to encode = Bobby's workaround
  (example to be collected); until then ocean stays a low-zorder backdrop.
- **Shapefile discipline**: simplified variant is the iteration default;
  full-resolution is an explicit opt-in. Preview never touches the network.
- **%autoreload ergonomics**: the new modules keep the None-sentinel /
  constants-read-in-bodies form and width-multiplier sizing (their §7.6 ask,
  Bobby-endorsed), so live-notebook tuning keeps working against the library.

## 6. What approval means

"Go" on this plan = Tier B unblocks (build order: geometry.py → colorbar-cell
painter → map_facet + fixture → palette + clipped ramp), and handoff.md gets
drafted from §4 + survey §10 with the comprehension questions. Their CC
executes phase 5; we track only completion.
