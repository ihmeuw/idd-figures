---
kind: orientation
from_repo: idd-lsae-hdi
date: 2026-07-28
maintainer: bcreiner
status: living
---

# idd-lsae-hdi — repo orientation

**What you are reading.** A one-stop introduction to the figures this repo makes, every
appearance/layout decision behind them, and where the output lives — written so an
`idd-figures` session can decide what to absorb, what to leave local, and what we should
stop hand-rolling because this library already solves it.

**Audience.** A Claude Code session + Bobby, working *in* `idd-figures`. Sections 6–8 are
the ones that produce work items; 1–5 are the context needed to judge them.

Paths are written `<project_output_root>/…` (the real value lives in this repo's gitignored
`paths.yaml`). Nothing below contains an absolute path, by policy on both sides.

## 1. What this repo is

Global **admin-2 Human Development Index** built from three IHME LSAE inputs, on the
GBD×LSAE hierarchy blend.

| | |
|---|---|
| Hierarchy | 204 countries, 3,415 admin-1, 47,537 admin-2 rows — **47,450 leaves** (`most_detailed_lsae == 1`, *not* `level == 5`) |
| Years | 2000–2023 (24) |
| Uncertainty | 100 draws carried end-to-end; figures use posterior means unless stated |
| Inputs | health = U5MR (₅q₀ probability) · education = mean years schooling 18–45 · income = GDP per capita |
| Product | three [0,1] dimension indices → per-draw geometric mean = HDI |
| Live variants | **5 transformation specs** (`v1`/`current`, `quantile_plus`, `brass_le`, `scaled`, `gam_le`), each with its own cube and its own full figure set |

Two facts drive almost every figure decision:

1. **Choropleths are 47,450 polygons.** A full admin-2 fill is ~15–30 s/panel and a
   7-panel figure is minutes. Every layout iteration has to be possible *without* filling.
2. **Everything is rendered five times** — once per spec — so any per-figure manual
   tweak is a 5× cost and any silent default is a 5× error.

---

## 2. Architecture

Three layers, and the seam matters because it is where we break your rules (§7).

| Layer | Path | Contract |
|---|---|---|
| Draw | `lib/figures/` | painters take an `ax`, layouts own the `Figure`/`GridSpec`; "a figure never loads or aggregates its own data" |
| Orchestrate | `lib/render/` | "knows which set of things a deliverable needs, what colour limits and output paths they use, and writes them out" |
| CLI | `04_manuscript/` | thin `click` wrappers, zero drawing logic, one process per group so groups run in parallel |

The painter/layout split is stated in `lib/figures/dispersion.py` and restated in `maps.py`,
`composition.py`, `timeseries.py`. It is the same split `idd-figures` uses, arrived at
independently — which is the main reason absorption looks tractable.

---

## 3. Figure inventory

### 3.1 Modules in `lib/figures/`

| Module | Draws | Notes |
|---|---|---|
| `maps.py` | `choropleth_panel`, `plot_choropleth`, `join_shapes` | plain geopandas, no cartopy. **Defaults to `cmap="viridis"`** (see §9) |
| `style.py` | palette rules, `size_by_logpop`, `signed_diverging_cmap`, `clipped_diverging_cmap`, `mask_artifacts` | the canonical statement of the palette law |
| `palettes.py` | `SR_COLORS` (7 GBD super-regions), `GREY`, `MED_DARK/LIGHT` | start-year grey, end-year coloured |
| `dispersion.py` | AID-vs-level scatters, within-country range bars | where the painter/layout convention is formally declared |
| `scatter.py` | AROC scatters, "left behind" quadrant figure | probability→size/alpha binning |
| `composition.py` | composition triangles, Δ-ternary, Δ-composition, trajectory arrows | keeps out-of-simplex rows (§5.9) |
| `timeseries.py` | 2×2 composition time series | colour = signed standardized gap from the **population-weighted** national |
| `linked.py` | cross-vignette composites (which units lag / where / why) | fail-loud categorical colour mapping |
| `spec_maps.py` | the two multi-panel map layouts + **the whole geometry kit** | densest module; §5.4–5.6 live here |
| `spec_histograms.py` | distribution figures (pool + two year slices) | §5.7 lives here |
| `anatomy.py` | 3-row outcome→index figure per dimension | pure composition of the two above |
| `interactive.py` | plotly AID explorer (HTML) | hover-one-trace + SVG-not-WebGL |

### 3.2 Generators in `lib/render/`

`paths.py` (dated figure dirs; **figures overwrite in place, no `_v2`**), `spec_figures.py`
(groups `levels`/`aroc`/`bars`/`anatomy` + `aid`/`grids` injected from `aid_figures.py`),
`aid_figures.py` (no shapefiles needed → much lighter load), `natural_maps.py`
(spec-*independent* outcome maps, rendered **once** so five specs don't produce five
identical copies), `reports.py` (markdown validation reports, not figures).

CLIs: `run_spec_figures.py --spec --group`, `run_spec_maps.py --preview/--full`,
`run_spec_histograms.py`, `run_aid_interactive.py`.

### 3.3 Rendered output

`<project_output_root>/05-figures/` — two nodes, 309 files.

**`positioning_deck/`** — `20260727`, `_v2`, `_v3`, `_v4` (v4 is live: 37 png + 1 html +
`FIGURES.md` + `EQUATIONS.md`). Families in v4: `map_<key>_<year>.png` ×14,
`aroc_<key>.png` ×7, `aid_grid_<indicator>.png` ×4, `aid_<scenario>.png` ×5, `bars_*.png`
×4, `chad_left_behind_pair.png`, `aid_interactive.html`.

**`spec_comparison/20260727/`** — 223 files, two naming schemes side by side:

| scheme | families | rationale |
|---|---|---|
| spec in the **filename**, flat folder | `maps_indices_<spec>`, `maps_data_index_hdi_<spec>`, `hist_<spec>`, `hist_by_year_<spec>`, `hist_data_index_hdi_<spec>`, `aid_interactive_<spec>_portable.html` | meant to be flipped through side by side |
| generic names in a **per-spec subfolder** | `<spec>/` × 5, **identical 29 filenames each**: `map_<key>_<year>` ×8, `aroc_<key>` ×4, `anatomy_<dim>` ×3, `bars_*` ×4, `aid_*` ×9, `chad_left_behind_pair` | a slide swaps the folder and keeps its file references |

The inconsistency is a known defect, not a design (§9).

---

## 4. Figure families, one line each

| Family | What it shows |
|---|---|
| **Level maps** | HDI + 3 indices at 2000 and 2023, every panel pinned to [0,1] |
| **AROC maps** | annualized rate of change, %/yr, split-middle ramp, per-spec limit |
| **Natural-space maps** | the three raw outcomes; both years share one colour range |
| **Range bars** | within-country spread of admin-2 HDI, 2000 (grey) vs 2023 (coloured), four population cuts |
| **Chad pair** | left-behind scatter + map of the same units, side by side |
| **AID scatters** | Average Index Dispersion vs level, five focus scenarios |
| **AID grids** | 2×2 composites of the same painter across indicators |
| **Spec histograms** | all-years pool behind 2000/2023 slices; outcome → index → HDI |
| **Spec maps** (2 layouts) | index layout (HDI + 3 indices, one shared bar) and data→HDI layout (outcomes → indices → HDI, 4 bars) |
| **Anatomy** | per dimension: outcome map / before-after distributions / index map — one shared display window across all three |
| **Interactive** | plotly AID explorer; hover a country and its whole line lights up |

---

## 5. Conventions, and how each one was arrived at

Every rule below cost at least one round. The "went wrong first" line is the part worth
absorbing — it is what a library could make structurally impossible.

### 5.1 Palette law — red is bad, always
**Rule.** Every map needs an agreed bad colour and it is **red**. Blue is never bad. Yellow
appears mid-ramp only, never as an endpoint. Default to the `RdYlBu` family, reversed where
high = bad (U5MR). RdYlGn only as a last resort (colour-blindness).
**Went wrong.** Three separate rounds in one day: viridis on the HDI map after an
alternates pass had already chosen otherwise; then viridis/viridis_r on the natural-space
maps — *"U5M… yellow to blue? Blue = bad?"*. Verdict: *"If we can't get good color scales
that have a 'bad' color that is agreed is actually bad, then we need to be boring and stick
to red to blue."*

### 5.2 Ramp semantics — smooth for levels, split-middle for signed change
**Rule.** Level maps get a smooth continuous ramp. Signed change gets a clipped middle so
the zero crossing is a hard visual break (`clipped_diverging_cmap(lo=96, hi=160)`), and
**only on a symmetric scale** (`vmin=-x, vmax=+x`) or the jump doesn't land on zero.
**Went wrong.** The AROC split-middle ramp was applied to the [0,1] level maps: *"you've
taken the AROC color ramp and applied it to the HDI map… That makes no sense."* A hard
mid-ramp on a level map manufactures a threshold at HDI 0.5 that is not in the data.
**Also settled here:** the HDI map palette is clipped-mid `RdYlBu` pinned `[0.2, 1]` with
the seam at 0.6, and same-day fixes are edited into the render script **in place** — no new
dated version dir for an iteration fix.

### 5.3 Pin and saturate, don't use the full data range
AROC maps ±3 %/yr for goalposted specs, **±5 for `quantile_plus`** (rank indices move ~4.5×
faster in relative terms, so no single limit serves both), chosen so ~1–3% of units
saturate. Level maps pinned [0,1] so specs are comparable.

### 5.4 Every layout number is derived from the *measured drawn-box* aspect
**Rule.** No hand-picked figsizes or height ratios. `map_aspect(extent)` = raw extent ratio
÷ geopandas' `1/cos(mean latitude)` squeeze; `map_height_ratios`, `map_figsize`,
`gap_factor(n_rows, hspace)` all follow from it.
**Went wrong — four separate omissions, each of which read as "a spacing bug":**

| omission | cost |
|---|---|
| used the raw extent ratio 2.583 instead of the drawn 2.507 | ~3% slack per row → dead band |
| never set gridspec `left`/`right` (matplotlib defaults 0.125/0.9) | **22.5% of the width** spent on margin |
| left matplotlib's default 5% data margins | ~10% of every panel |
| left `hspace` out of the derived height | rows under-allocated 20–27%, so fixed-aspect maps came out **narrower than the histograms beside them** (10.11 in vs 10.78 in) |

`gap_factor` exists because matplotlib charges `hspace` against the *average* axes height,
so gaps cost `(n-1) · hspace · mean(height)` on top of the rows.
**Caveat for absorption:** the `1/cos(latitude)` correction is *geopandas* behaviour
(`set_aspect(1/cos(lat))` with `adjustable="box"`). Your `map_panel` uses cartopy and calls
`set_aspect("auto")`, so the squeeze does not apply there — the *lesson* transfers, the
*constant* does not.

### 5.5 Colorbar geometry is an explicit figure-coordinate box
**Rule.** `CBAR_WIDTH` (share of figure width, clamped to the panels served), `CBAR_HEIGHT`,
`CBAR_GAP`, `CBAR_LABEL_SIZE`, `CBAR_TICK_SIZE`. Placed with `add_axes` **below** its
panels, never carved out with `fraction` — so resizing the bar never resizes the map.
**Went wrong, twice, ~3 rounds each:**
- matplotlib's `fraction`/`aspect`/`shrink` fight each other. With `aspect` pinned,
  `fraction` drives thickness and length falls out of it; **`shrink` is clamped at 1.0** —
  measured: `shrink=1.0`, `2.0` and `10.0` draw byte-identically. So "make the bar wider"
  had no working knob.
- Then a **second constant** was added for the bars spanning a whole row
  (`CBAR_FRACTION` + `CBAR_FRACTION_SHARED`, then after that was flagged as a wart,
  `CBAR_WIDTH` + `CBAR_WIDTH_SHARED`). Editing one silently did nothing in whichever figure
  used the other. **The same wart shipped twice.** Now one constant, clamped to the served
  union, with a test asserting the deleted names stay deleted.

### 5.6 Module constants are read in function *bodies*, never as default arguments
**Rule.** `def f(..., width=None)` then `width = CBAR_WIDTH if width is None else width`.
**Went wrong — the single most expensive bug of the session.** Python binds a default once
at import; `%autoreload` swaps function *bodies* without refreshing `__defaults__`. Three
constants were edited in a live notebook (`CBAR_FRACTION`, `CBAR_SHRINK`, `CBAR_WIDTH`) and
each appeared to do nothing, because the kernel kept the import-time value. Two regression
tests now mutate the module attribute and assert the drawn figure follows.
**Corollary.** `%autoreload` also cannot add *new* module-level names to a live namespace.
The fix is `importlib.reload(module)` — **not** restructuring the module to avoid new names
(that was tried; it moved the failure and made things worse).

### 5.7 Distributions: pool behind, two years over, medians on unwindowed arrays
Every panel is a **density** (the all-years pool holds 24× the units of one year, so counts
would be incomparable). Pool in neutral fill + dark outline; the two years semi-transparent
over it; each distribution carries its own dashed median **computed on the full array, not
the plotted window**; y axes carry no ticks or numbers; **one shared legend** below the
panels; log axes get ticks at round values per decade (1/2/5 for U5MR, 1/5 for GDP) instead
of raw log10 positions.
**Windowing + the rule that makes it honest.** Raw panels are windowed to
`RAW_WINDOW_PERCENTILES = (0.2, 99.8)` — long tails otherwise squash all visible structure
(U5MR reaches 54%, GDP $380k). **matplotlib silently drops out-of-range values from a
histogram**, so every windowed panel is annotated with how much falls outside, placed in the
emptier top corner with a translucent backing. That annotation is what caught the 489
admin-2 unit-years whose schooling exceeds the 15-year education goalpost. Index panels are
never windowed — they are [0,1] by construction.

### 5.8 Type sizes, titles, legends
`PANEL_TITLE_SIZE = 18`, `SUPTITLE_SIZE = 20`, colorbar label 15 / ticks 14; one-line
suptitles (measured clearance +0.034 to the first panel title). Colorbar labels are dropped
on rows where the panel title already names the outcome — passing both printed every label
twice. Legends must be collision-checked against labels, titles **and colorbars**, and
dropped entirely when uninformative (a super-region legend on a sub-Saharan-Africa-only
figure). Every encoded mark must be decodable: `▽` = start year, `△` = end year, stated in
the legend because a reader cannot decode marker shape from the data.

### 5.9 Keep the awkward rows visible
Two instances of the same principle:
- **Δ-composition ternary.** Contribution shares go negative when a component moves against
  the total. `mpltern` silently drops those rows — 19 of 204 countries, including the exact
  Chad units that are the story. So `delta_composition_panel` uses a hand-rolled *linear*
  barycentric projection (`x = right + 0.5·top`, `y = top·√3/2`) which stays valid for
  negative shares: they land **outside** the triangle instead of vanishing.
  Trap: rows where *every* component declined have all-**positive** shares (negative over
  negative), so they are detectable only via a separate `declined` flag.
- **Artifact greying.** Two Algerian admin-2 units (`67602` Bordj Badji Mokhtar, `68860`
  Tazrouk) have upstream education artifacts. They are greyed **on maps only, via NaN**, so
  they read as "no estimate" exactly like genuinely absent geography — the underlying data
  is untouched and they still appear in bars, scatters and aggregates. No masking of any
  kind in the data. Presentation-only.

### 5.10 Iteration tooling — because a full render is minutes
`preview=True` skips the 47,450-polygon fill entirely, drawing country outlines only and
returning a stand-in `ScalarMappable` with the same colour limits, so **the layout,
colorbars included, is identical** — seconds instead of minutes. Preview output gets a
`_preview` filename suffix so a draft can never overwrite a final. `show_boxes=True`
outlines every axes' allocated box (colorbars included), which is how you tell a spacing
problem from a cropping one: maps never fill their box, and `savefig(bbox_inches="tight")`
crops to the ink, not to the boxes.

### 5.11 Shapes are pinned, and simplified
Figures read the **LBD standard admin release**, `constants.ADMIN_SHAPEFILE_DATE =
"2024_07_29"`, simplified variant, whose `loc_id` is our `location_id` (204/204 countries
and 47,450/47,450 leaves join, 0 missing). Same geometry as the LSAE parquets but 24–70×
smaller: admin-0 is 462,612 vertices vs 31,663,411, so an outline draw is **0.55 s/panel
instead of 18.7**, and all three levels load in 1.3 s. Newer releases exist; pinning keeps
every figure on one vintage, bumped deliberately with a re-render.
**Dead end worth recording:** we were mid-build on a disk-cached `geometry.simplify()` store
(≈145 s to build, needs invalidation) when the pre-simplified files turned out to already
exist. Check for a canonical asset before building machinery.

### 5.12 Interactive figures — two hard-won rules
- **One trace per country plus a single highlight trace.** Restyling ~200 traces on every
  mouse-move made the page unusable.
- **SVG, not `scattergl`.** WebGL renders nothing at all on remote desktops/VDI — a blank
  page, not a degraded one.
- Payload discipline: round coordinates, name once in the trace name and read it back with
  `%{fullData.name}`, use x/y channels rather than duplicated `customdata`, explicit format
  on every tooltip field. Embedded plotly.js is ~4.9 MB and sets the floor on file size.
- **Caution:** these files *are* self-contained. A grep for `cdn.plot.ly` hits a string
  inside plotly's own bundle and looks like a CDN dependency — it isn't.

### 5.13 Hygiene
Never write a figure into the repo — output goes to `<project_output_root>`, and a
gitignored `notebooks/` does not count as "outside the repo". No absolute paths in committed
files — our pre-commit guard blocks all five IHME mount prefixes (the two home mounts, the
J-drive and its Linux alias, the share mount, and the team mount; that last one was missing
until 2026-07-28, which is where every figure actually lands). Deliberately not spelled out
here: this file would trip that guard, and yours.
Every shipped folder gets a `FIGURES.md` with a caption per figure, and
figures get self-describing presentation titles, never notebook-cell-derived names. Save
uniformly `dpi=200, bbox_inches="tight", facecolor="white"` — **which conflicts with your
rule; see §7.**
And the one that underpins all of it: **look at every figure you produce.** A successful
`savefig` is not verification.

---

## 6. We reinvented these — they already exist in `idd-figures`

Highest-value section. Each row is code we should delete and replace with a call.

| Ours | Yours | Note |
|---|---|---|
| `style.size_by_logpop` | `lib/style.py::size_by_logpop` | **identical name**, independently written |
| `style.signed_diverging_cmap` | `lib/colors.py::signed_diverging_cmap` | **identical name** |
| `style.clipped_diverging_cmap(lo=96, hi=160)` | `lib/colors.py::binned_colormap(..., remove_middle=)` | ours is continuous-ramp surgery, yours is bin-based — needs a compatibility check for a *continuous* split ramp |
| `spec_maps.outline_axes` / `show_boxes=True` | `lib/layouts/anatomy.py::show_anatomy` | yours is richer (labels title/tick/label regions) |
| `spec_maps` `preview=True` | `map_panel(draw_data=False)` | same idea; ours additionally returns a stand-in mappable so colorbars still lay out |
| `spec_histograms._tick_label` (k-notation) | `lib/bins.py::map_bin_labels(abbreviate=)` | plus `numbers.smart_ui_format` for text |
| `palettes.SR_COLORS` | `lib/palettes.py::GBD_SUPER_REGION_COLORS` | two different hex sets for the same 7 names — must reconcile |
| `render.spec_figures._save` | `lib/io.py::save_figure` | yours does multi-format, `pdf.fonttype=42`, chmod, thumbnails |
| `render.paths.dated_figure_dir` | — | no equivalent in either; candidate contribution |
| `reports.as_table` | — | markdown tables without `tabulate` |

## 7. Conflicts to resolve before absorption

1. **`bbox_inches="tight"`.** We save everything with it; you forbid it outright ("all
   geometry explicit"). Our reason is weak — it was never a decision, just a default we
   inherited — but note that *because* we use it, our figures' final crop is set by ink, not
   by the boxes, which interacts with §5.10. Adopting your rule means our margins
   (`LEFT/RIGHT/TOP/BOTTOM`) become load-bearing rather than advisory. **We should switch.**
2. **Data loading inside the figures layer.** `spec_maps.load_spec_map_frames`,
   `spec_histograms.load_spec_distributions`, `make_map_figures`, `make_figures` open
   netCDF/parquet and save files from inside `lib/figures/`, violating both your contract
   and our own stated one. These belong in `lib/render/`. Absorbing our geometry kit does
   not require fixing this first, but exporting our *layouts* does.
3. **"Anatomy" collides.** Ours is a published 3-row outcome→index figure. Yours is a layout
   **debugger** (`show_anatomy`). Someone will conflate them. Suggest we rename ours
   (`transform_anatomy`?) since yours is the more general meaning.
4. **Aspect mechanism differs.** §5.4 — geopandas `1/cos(lat)` squeeze vs your cartopy
   `set_aspect("auto")`. The `gap_factor` and derive-don't-guess lessons are portable; the
   2.507 constant is not.
5. **Painter/layout hybrids.** Our `scatter.py` and five functions in `linked.py` take
   `ax=None` and create a Figure if absent — painter and layout in one, which your
   `plot_<thing>(df, *, ax=None)` convention actually blesses. Worth confirming which side
   the seam belongs on before we port.
6. **Config surface.** Our per-figure knobs are ~40 loose module-level constants across
   `spec_maps`/`spec_histograms`/`anatomy`. Your successor pattern is keyword-only args with
   in-signature defaults (`map_panel`) plus `rc_context` for fonts. Two things to settle:
   - **Our §5.6 rule has to survive the port.** Live-editing a module constant is how these
     figures get tuned, and a constant bound as a signature default is invisible to
     `%autoreload`. If the shared version puts defaults in signatures, it needs the
     `None`-sentinel + resolve-in-body form, or it re-breaks the workflow that rule protects.
   - **Absolute point sizes do not survive a change of figure width.** Our
     `CBAR_THICKNESS = 0.024` exists only because the 16-inch map figure's default reads as a
     hairline on the 11-inch anatomy figure, and `PANEL_TITLE_SIZE = 18` / `SUPTITLE_SIZE = 20`
     will hit the same wall on the next new width. Sizes expressed as **multipliers of figure
     width** would remove that whole class of hand-patching. Worth considering for the shared
     config surface.

## 8. What we could contribute, and what we need

**Gaps in `idd-figures` that we have already solved locally** (your survey lists these as
missing; we have working code):
- **`map_facet` / multi-panel maps** — `spec_maps.figure_maps_indices` (4 panels, one shared
  bar) and `figure_maps_data_to_hdi` (7 panels, 4 bars) are exactly the missing piece, with
  the row-height maths (`map_height_ratios`, `gap_factor`, `map_figsize`) that makes a
  mixed-panel-count grid actually fit.
- **Shared legend/colorbar across map panels** — `colorbar_axes` centres a bar under the
  union of the panels it serves and clamps its width to them.
- **Admin-2-scale performance** — the simplified-shapefile pin (§5.11) plus `preview` mode
  is the difference between a 30-minute and a 30-second iteration loop.
- **Clipping annotation** (§5.7) — generic, and it catches a class of silent lie.
- **The gridspec-margin trap** (§5.4) — 22.5% of width lost to unset `left`/`right` is worth
  a lint or a default in the library.

**What we need from you:**
- The `map_facet` decision — if you build it, we delete ours; if not, take ours.
- A reconciliation of the two GBD super-region palettes.
- A ruling on §7.6 (config surface vs live-editable constants), since it decides how much of
  our tuning layer can be shared at all.
- `map_bin_labels`/`binned_colormap` confirmation that a *continuous* split-middle ramp is
  expressible, or we keep `clipped_diverging_cmap`.

---

## 9. Outstanding issues in this repo

**Open bugs**
1. **Shared legend collides with the bottom colorbar in all 15 anatomy figures.**
   `shared_legend` anchors at `(0.5, 0.02)`; the index map's bar now lands at the same
   height, so the legend prints on top of the ramp. `LEGEND_HEIGHT` reserves space but
   nothing keeps the colorbar out of it. Present in the current rendered set.
2. **Six surviving `cmap="viridis"` defaults** (5 in `composition.py`, 1 in `maps.py`)
   against 27 call sites that override them. The palette law holds only because callers
   remember it — a new caller who forgets gets viridis, which is exactly the mistake that
   cost three rounds.
3. **Figure output naming is inconsistent** — anatomy writes generic names into `<spec>/`
   (so a re-render overwrites with no A/B), maps put the spec in the filename in the flat
   folder. One convention plus a way to keep the prior look is needed.
4. **`positioning_deck/current` → `20260727` (v1)** while v4 is the live set — three
   versions stale.
5. **`positioning_deck/20260727_v4/*` and `spec_comparison/20260727/current/*` share ~20
   filenames for the same spec but differ by md5** — separate renders from different code
   states, so two slides can silently disagree.
6. `hist_spec1_current.png` / `hist_spec2_quantile_plus.png` are byte-identical leftovers of
   an older naming scheme, and exist for only 2 of 5 specs.
7. **`current` is overloaded** — "latest" in `positioning_deck/current`, a *spec name* in
   `spec_comparison/20260727/current/`.
8. 36 hidden `.log_*` files sit among the figures with inconsistent naming;
   `spec_comparison/20260727` mixes two build days rather than one atomic render.
9. Two figures exist only in v1–v3 and were never rebuilt: `05_composition_triangle_2023`
   and `aid_c18_range_bars_admin1`.
10. Superseded generator scripts still live in the output tree (`render_deck_figures_v1-v4`,
    `render_spec_figures`, `render_transform_anatomy`, …) — the package now owns these.

**Undocumented but landed:** the `lancet_label` display-name work (publication names —
"Bolivia", not "Bolivia (Plurinational State of)") and the whole `interactive.py` surface
have no decision record.

**Deferred by design:** directional axis arrows; a general figure-standards pass; the
`Indicator` class (figures stay functions either way).

---

## 10. The repeat-offence table

The most useful thing we can hand you: mistakes that recurred, ranked. Each is a candidate
for something the library could make *impossible* rather than merely documented.

| # | Offence | Occurrences | Cost |
|---|---|---|---|
| 1 | Two-constant width (a base plus a `…_SHARED` twin) so editing one silently did nothing | shipped **twice** | 3 rounds; now guarded by a test that the deleted names stay deleted |
| 2 | Module constant bound as a **default argument** in a live-edited module | 3 constants | 3 rounds; 2 regression tests |
| 3 | Wrong palette / wrong ramp semantics | viridis on HDI; AROC ramp on level maps; viridis on natural maps | 3 rounds in one day → the palette law |
| 4 | Shipping vignette/notebook **defaults** into a deliverable | bar lw=7; default viridis cell; cell-derived titles | 3 rounds |
| 5 | Legend defects | overlapping labels; uninformative legend kept; **colorbar collision (still open)** | 3 |
| 6 | Hand-picked sizes instead of content-derived | fixed figsize regardless of country count; hand-picked `spec_maps` figsizes | 2 |
| 7 | Marks not rescaled together / invisible marks kept | bars thinned but diamonds and dots left | 2 |
| 8 | Panel spacing left at the layout default | Chad pair; the AID composites | 2 |
| 9 | Building bespoke machinery when a canonical asset exists | the simplify cache vs the existing simplified shapefiles | 2 |

Read #1, #2 and #6 together: all three are *configuration* failures, not drawing failures.
That is the strongest argument for whatever config surface §7.6 settles on.

---

## 11. Suggested absorption order

0. **Settle the size/config surface** (§7.6) — it decides what every figure signature looks
   like, so it comes before any code moves. Our position: sizes as multipliers of figure
   width, resolved by `None`-sentinel in the function body, owned by the shared library
   rather than by us.
1. **Free wins, no behaviour change:** adopt `io.save_figure`, `palettes` (after
   reconciling hex), `bins.map_bin_labels`, `numbers.*`. Delete our duplicates of
   `size_by_logpop` and `signed_diverging_cmap`.
2. **Take the geometry kit** (`gap_factor`, `map_height_ratios`, `map_figsize`,
   `pin_extent`, `colorbar_axes`, plus the preview/stand-in-mappable idea) into whatever
   `map_facet` becomes, being careful about the geopandas-vs-cartopy aspect difference.
3. **Then port a whole layout** — `figure_maps_indices` is the smallest complete example
   (4 panels, 1 shared bar) and would prove the seam.
4. Leave local: everything named in this repo's terms — spec names, `AROC_LIMITS`,
   `HEALTH_TRANSFORMS`, `DIMENSIONS`, `INDEX_PANELS`, `RAW_PANELS`, the leaf definition
   (`most_detailed_lsae == 1`), `ARTIFACT_LOCATION_IDS`, and the `AnalysisData`/`INDICATORS`
   contracts.
