---
kind: prep
repo-motivating: idd-lsae-hdi (items are library work, not lsae-specific)
date: 2026-08-02
status: DONE 2026-08-02 — Tier A (1-10) and Tier B (11-18) all shipped; suite
  150 green; committed as eec8e03 (stack), 14889be (guides), b3e10f6
  (primitives). Gallery approved by Bobby (bar-height note fixed via per-row
  cbar_h/cbar_band). Parked section remains open.
---

# Library prep — work list

## Tier A — ruled fixes (unblocked)

1. **Aspect flip** — remove `set_aspect("auto")` from `basemap_painter`
   (`lib/painters/maps.py:51`); set explicit derived aspect
   (`adjustable="box"`, projected units) from the layout; add tolerance guard
   (box vs content aspect → error). Update `map_panel` accordingly. Tests:
   correct path pixel-stable; wrong `margins=`/`hspace` now raises instead of
   distorting. [survey §3.1 + ruling]
2. **`save_figure` scoping** — wrap the PDF save in
   `mpl.rc_context({"pdf.fonttype": 42})` (`lib/io.py:37-41`). Test: rcParams
   unchanged after call.
3. **Registry attach** — `panel_grid` keeps the name→Axes dict and attaches it
   to the returned figure (+ accessor). (`lib/layouts/grids.py:189`.) Test:
   named cell retrievable.
4. **`remove_middle` symmetry spec** — even n: sample n+2, drop the two
   straddling the seam; odd n: white/neutral center + one dropped from EACH
   side; raise on the impossible parity combos. Fix docstring. Tests assert
   per-side counts. (`lib/colors.py:71-78`.)
5. **`Colorbar` node tests + example** — pattern the example on
   forecast-mbp's live continuous-bar maps. Binned remains the house default.
6. **`Cell.projection` annotation** — widen from `str | None` to accept a
   projection object. (`lib/layouts/grids.py:75`.)
7. **Nested-margins warn** — nested `Grid` carrying `margins` warns/raises;
   teaching line: "the parent's cell IS the margin control."
   (`grids.py:134-138`.)
8. **`facet_grid(projection=)`** — thread into both cell-creation sites;
   refuse sharex/sharey under a projection. (`grids.py:243-247, 263-267`.)
9. **DECISIONS.md amendment** — append correction to the 2026-07-01 entry
   ("map_facet are shared" → was aspirational; link this integration).
10. **Split `plot_composition`** — layout half leaves `painters/`
    (`lib/painters/composition.py:49-62`).

## Tier B — builds (on plan approval; order matters)

11. **`lib/layouts/geometry.py`** — `gap_factor`; projected-extent aspect;
    wspace-aware `panel_width`; `row_height`; `solve_figsize` with explicit
    colorbar/legend band reservation AND title allowance (lsae B1+B6 lessons).
    Pure functions, exhaustive tests (these ARE the feature).
12. **Colorbar-cell painter** — continuous-mappable inset bar painter
    (extends `bin_legend_panel`'s inset path) for spanning cells; the
    plan §1 mechanism.
13. **Public map painter** — extract `map_panel._draw_map` closure; both
    `map_panel` and `map_facet` consume it.
14. **`map_facet`** — per plan §2 (LCM columns, solver heights, auto-names,
    registry return). **First deliverable is an example gallery rendered on
    the synthetic fixture** (4-panel/1-bar; 7-panel/4-bar; a mixed
    map+plot+legend composite) — Bobby judges the design from figures, not
    prose; the lsae port waits on that review.
15. **Synthetic preview fixture** — low-vertex continent-ish polygons shipped
    in-library; preview defaults: simplified shapes, no Natural Earth,
    stand-in mappables, `_preview` filename suffix guard.
16. **Palette adoption** — lsae SR hexes become `GBD_SUPER_REGION_COLORS`
    (as HEX STRINGS — current RGB-tuple type breaks plotly/HTML); add
    `GREY`/`MED_DARK`/`MED_LIGHT` companions; interim standard per Bobby.
17. **`clipped_diverging_cmap(name, lo_frac, hi_frac)`** — continuous
    split-middle ramp, fractions not 256-sample indices.
18. **`numbers.compact()`** — scalar k-notation formatter (else lsae keeps
    `_tick_label` local; decide at port time).

## Parked (waiting on Bobby input)

- Vignette: "plotting options" (incl. nested-margins alternative) — his spec.
- Vignette: facet/grid "control all the things" tour — his spec.
- Ocean-vs-admin coastline workaround — his example to collect.
- `dated_figure_dir` (root-injected) — nice-to-have, not gating.
